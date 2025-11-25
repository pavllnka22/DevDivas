import json

import requests
from amadeus import Client, ResponseError, Location
from amadeus.namespaces._airport import Airport
from amadeus.namespaces._booking import Booking
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

import users
from TravellinoCappuchino import settings
from .flight import Flight
from .metrics import Metrics
from .booking_flight import Booking
from .models import Country, City, Trip, FlightBookingForm
from .serializers import CitySerializer, TripSerializer, CountrySerializer

from django.contrib.auth.models import User
from users.models import CustomUser


def country_list(request):
    countries = Country.objects.all().values('id', 'name', 'description', 'flag_url', 'currency').order_by('name')
    return JsonResponse(list(countries), safe=False)


def country_detail(request, country_id):
    try:
        country = Country.objects.prefetch_related('cities').get(id=country_id)
        serializer = CountrySerializer(country)
        return JsonResponse(serializer.data, safe=False)
    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)


def city_detail(request, city_id):
    try:
        city = City.objects.get(id=city_id)
        serializer = CitySerializer(city)
        return JsonResponse(serializer.data, safe=False)
    except City.DoesNotExist:
        return JsonResponse({'error': 'City not found'}, status=404)


def get_weather(request, city_id):
    try:
        city = City.objects.get(id=city_id)
    except City.DoesNotExist:
        return JsonResponse({'error': 'City not found'}, status=404)
    lat = city.latitude
    lon = city.longitude

    api_key = settings.WEATHER_API_KEY
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={city.latitude}&lon={city.longitude}&units=metric&appid={api_key}"
    )

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        return JsonResponse({"error": "Failed to fetch weather", "details": str(e)}, status=500)

    return JsonResponse({
        "city": city.name,
        "temperature": round(data["main"]["temp"]),
        "feels_like": round(data["main"]["feels_like"]),
        "description": data["weather"][0]["description"],
        "icon": data["weather"][0]["icon"],
    })


class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer


def get_queryset(self):
    cities = City.objects.all()
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)


def post(self, request):
    serializer = CitySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TripListView(generics.ListAPIView):
    serializer_class = TripSerializer

    def get_queryset(self):
        trips = Trip.objects.all()
        country_id = self.request.query_params.get("country")
        city_id = self.request.query_params.get("city")

        if country_id:
            trips = trips.filter(city__country_id=country_id)

        if city_id:
            trips = trips.filter(city_id=city_id)

        ordering = self.request.query_params.get("ordering")
        if ordering == "price":
            trips = trips.order_by("price")
        elif ordering == "-price":
            trips = trips.order_by("-price")

        return trips


amadeus = Client()


@csrf_exempt
def flight_offers(request):
    if request.method == "POST":
        data = json.loads(request.body)
        origin = data.get('Origin')
        destination = data.get('Destination')
        departure_date = data.get('Departuredate')
        return_date = data.get('Returndate')

        kwargs = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': 1
        }

        if return_date:
            kwargs['returnDate'] = return_date

        try:
            flight_offers = get_flight_offers(**kwargs)
            cheapest_flight = get_cheapest_flight_price(flight_offers)
            response = {
                'flight_offers': flight_offers,
                'cheapest_flight': cheapest_flight
            }
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'POST method required'}, status=405)


def get_flight_offers(**kwargs):
    search_flights = amadeus.shopping.flight_offers_search.get(**kwargs)
    flight_offers = []
    for flight in search_flights.data:
        offer = Flight(flight).construct_flights()
        flight_offers.append(offer)
    return flight_offers


def get_flight_price_metrics(**kwargs_metrics):
    kwargs_metrics['currencyCode'] = 'USD'
    metrics = amadeus.analytics.itinerary_price_metrics.get(**kwargs_metrics)
    return Metrics(metrics.data).construct_metrics()


def get_trip_purpose(**kwargs_trip_purpose):
    trip_purpose = amadeus.travel.predictions.trip_purpose.get(**kwargs_trip_purpose).data
    return trip_purpose['result']


def get_cheapest_flight_price(flight_offers):
    return flight_offers[0]['price']


def rank_cheapest_flight(cheapest_flight_price, first_price, third_price):
    cheapest_flight_price_to_number = float(cheapest_flight_price)
    first_price_to_number = float(first_price)
    third_price_to_number = float(third_price)
    if cheapest_flight_price_to_number < first_price_to_number:
        return 'A GOOD DEAL'
    elif cheapest_flight_price_to_number > third_price_to_number:
        return 'HIGH'
    else:
        return 'TYPICAL'


def is_cheapest_flight_out_of_range(cheapest_flight_price, metrics):
    min_price = float(metrics['min'])
    max_price = float(metrics['max'])
    cheapest_flight_price_to_number = float(cheapest_flight_price)
    if cheapest_flight_price_to_number < min_price:
        metrics['min'] = cheapest_flight_price
    elif cheapest_flight_price_to_number > max_price:
        metrics['max'] = cheapest_flight_price


@csrf_exempt
def origin_airport_search(request):
    term = request.GET.get('term', '')
    if not term:
        return JsonResponse([], safe=False)
    try:
        amadeus_response = amadeus.reference_data.locations.get(
            keyword=term,
            subType=Location.ANY
        ).data
        result = get_city_airport_list(amadeus_response)
        return JsonResponse(result, safe=False)
    except ResponseError as e:
        return JsonResponse([], safe=False)


@csrf_exempt
def destination_airport_search(request):
    term = request.GET.get('term', '')
    if not term:
        return JsonResponse([], safe=False)
    try:
        amadeus_response = amadeus.reference_data.locations.get(
            keyword=term,
            subType=Location.ANY
        ).data
        result = get_city_airport_list(amadeus_response)
        return JsonResponse(result, safe=False)
    except ResponseError as e:
        return JsonResponse([], safe=False)

@csrf_exempt
def get_city_airport_list(amadeus_data):
    result = []
    for item in amadeus_data:
        city = item['name']
        code = item['iataCode']
        result.append(f"{city} ({code})")
    return result


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_flights(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "You need to log in to book a flight."}, status=403)

    try:
        data = request.data
        flight = data.get("flight")
        if not flight:
            return JsonResponse({"error": "Flight data missing"}, status=400)
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)

    traveler = {
            "id": "1",
            "dateOfBirth": data.get('date_of_birth'),
            "name": {
                "firstName": data.get('first_name'),
                "lastName": data.get('last_name')
            },
            "gender": data.get('gender'),
            "contact": {
                "emailAddress": data.get('email'),
                "phones": [{
                    "deviceType": "MOBILE",
                    "countryCallingCode": data.get('phone_country_code'),
                    "number": data.get('phone_number')
                }]
            },
            "documents": [{
                "documentType": "PASSPORT",
                "birthPlace": data.get('birth_place'),
                "issuanceLocation": data.get('passport_issuance_location'),
                "issuanceDate": data.get('passport_issuance_date'),
                "number": data.get('passport_number'),
                "expiryDate": data.get('passport_expiry_date'),
                "issuanceCountry": data.get('passport_country'),
                "validityCountry": data.get('passport_country'),
                "nationality": data.get('nationality'),
                "holder": True
            }]
        }

    try:
        flight_price_confirmed = amadeus.shopping.flight_offers.pricing.post(flight).data["flightOffers"]
    except (ResponseError, KeyError, AttributeError) as error:
        return JsonResponse({"error": getattr(error.response, "body", str(error))}, status=400)

    try:
        order = amadeus.booking.flight_orders.post(flight_price_confirmed, traveler).data
    except (ResponseError, KeyError, AttributeError) as error:
        detail = getattr(error.response.result["errors"][0], "detail", str(error)) if hasattr(error,
                                                                                              "response") else str(
            error)
        return JsonResponse({"error": detail}, status=400)

    booking = Booking(order).construct_booking()

    return JsonResponse({"booking": booking}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def city_to_iata(request):
    city_name = request.GET.get("city")
    if not city_name:
        return Response({"error": "City is required"}, status=400)

    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType='CITY'
        )
        data = response.data
        if not data:
            return Response({"error": "No IATA code found"}, status=404)

        iata_code = data[0]['iataCode']
        return Response({"iata": iata_code})
    except ResponseError as e:
        return Response({"error": str(e)}, status=500)