import json

import requests
from amadeus import Client, ResponseError, Location
from amadeus.namespaces._booking import Booking
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from TravellinoCappuchino import settings
from .booking_flight import Booking
from .flight import Flight
from .metrics import Metrics
from .models import Country, City, Trip, Hotel, Room
from .serializers import CitySerializer, TripSerializer, CountrySerializer


from google import genai
from google.genai.errors import APIError
from django.shortcuts import get_object_or_404


try:
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini: {e}")
    client = None


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
            metrics = build_price_metrics(flight_offers)
            response = {
                'flight_offers': flight_offers,
                'metrics': metrics
            }

            return JsonResponse(response)
        except ResponseError as e:  # Catch specifically ResponseError
            print(f"Amadeus API detailed error: {e.response.body}")
            return JsonResponse({'error': e.response.body}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'POST method required'}, status=405)


def generate_booking_link(airline, origin, destination, date):
    AIRLINE_LINKS = {
        "IB": "https://www.iberia.com/flights/?origin={o}&destination={d}&departureDate={date}",
        "LH": "https://www.lufthansa.com/fl/en/flight-search?origin={o}&destination={d}&departureDate={date}",
        "KL": "https://www.klm.com/travel/ua_en/plan_and_book/book_a_flight/index.htm?origin={o}&destination={d}&departureDate={date}",
        "AF": "https://wwws.airfrance.com.ua/search?origin={o}&destination={d}&outboundDate={date}",
    }
    if airline in AIRLINE_LINKS:
        return AIRLINE_LINKS[airline].format(
            o=origin,
            d=destination,
            date=date
        )
    return f"https://www.kayak.com/flights/{origin}-{destination}/{date}?sort=bestflight_a"


def get_flight_offers(**kwargs):
    search_flights = amadeus.shopping.flight_offers_search.get(**kwargs)
    flight_offers = []
    for flight in search_flights.data:
        offer = Flight(flight).construct_flights()
        try:
            first_segment = flight["itineraries"][0]["segments"][0]
            last_segment = flight["itineraries"][0]["segments"][-1]

            airline = first_segment["carrierCode"]
            origin = first_segment["departure"]["iataCode"]
            final_destination = last_segment["arrival"]["iataCode"]

            date = first_segment["departure"]["at"].split("T")[0]

            offer["bookingLink"] = generate_booking_link(
                airline,
                origin,
                final_destination,
                date
            )

        except Exception as e:
            print("Could not generate booking link:", e)
            offer["bookingLink"] = None

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
    return min(float(flight['price']) for flight in flight_offers)


def build_price_metrics(flight_offers):
    prices = [float(f["price"]) for f in flight_offers]
    prices.sort()

    min_price = prices[0]
    max_price = prices[-1]

    n = len(prices)

    cheapest = prices[0]



    return {
        "min": min_price,
        "max": max_price,
        "cheapest_flight": cheapest,
    }


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


def generate_city_trip_plan(city_id):
    if not client:
        raise Exception("Gemini Client wasn't initialized.")

    city = get_object_or_404(City.objects.select_related('country'), pk=city_id)

    context = (
        f"City: {city.name}, Country: {city.country.name}. "
        f"Description: {city.description}. "
        f"Currency: {city.country.currency}."
    )

    model_name = "gemini-2.5-flash"
    prompt = f"""Create a plan for a trip in the specified city {context}
    plan must contain:
            1. Main sightseeing
            2. Information about local currency ({city.country.currency}).
            3. Recommendations of local cuisine (at least 3-4 meals).
            4. All answers in English.

            Plan must be in a way of structured text with headers etc..
            """

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text

    except APIError as e:
        print(f"Error Gemini API: {e}")
        raise APIError(f"{e}")
    except Exception as e:
        print(f"Unknown error: {e}")
        raise


@api_view(['POST'])
def generate_city_trip_view(request):
    if request.method == 'POST':
        city_id = request.data.get('city_id')

        if not city_id:
            return Response({"error": "You need to specify the city's id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip_plan = generate_city_trip_plan(city_id)

            return Response({"trip": trip_plan}, status=status.HTTP_200_OK)

        except City.DoesNotExist:
            return Response({"error": "No city with such id."}, status=status.HTTP_404_NOT_FOUND)
        except APIError as e:
            return Response(
                {"error": f"Couldn't generate: {e}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response(
                {"error": f"Unknown error with server: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
def hotel_search(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)

    city_code = data.get("cityCode")
    checkin = data.get("checkInDate")
    checkout = data.get("checkOutDate")

    if not city_code or not checkin or not checkout:
        return JsonResponse({"error": "Missing params"}, status=400)

    try:
        hotels = amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code
        ).data

        hotel_ids = [h["hotelId"] for h in hotels[:25]]

        offers = amadeus.shopping.hotel_offers_search.get(
            hotelIds=hotel_ids,
            checkInDate=checkin,
            checkOutDate=checkout
        ).data

        results = []
        prices = []

        for h in offers:
            hotel = h["hotel"]
            for offer in h["offers"]:
                price = float(offer["price"]["total"])
                prices.append(price)

                results.append({
                    "hotelId": hotel["hotelId"],
                    "name": hotel["name"],
                    "city": hotel["cityCode"],
                    "price": price,
                    "currency": offer["price"]["currency"],
                    "offerId": offer["id"],
                    "bookingLink": f"https://www.booking.com/searchresults.html?ss={hotel['name']}"
                })

        prices.sort()

        metrics = {
            "min": min(prices),
            "max": max(prices),
            "first": prices[len(prices)//4],
            "third": prices[len(prices)*3//4],
            "cheapest": prices[0]
        }

        return JsonResponse({
            "hotels": results,
            "metrics": metrics
        })

    except ResponseError as e:
        return JsonResponse({"error": e.response.body}, status=400)


def rooms_per_hotel(request, hotel, departureDate, returnDate):
    try:
        # Search for rooms in a given hotel
        rooms = amadeus.shopping.hotel_offers_search.get(hotelIds=hotel,
                                                         checkInDate=departureDate,
                                                         checkOutDate=returnDate).data
        hotel_rooms = Room(rooms).construct_room()
        return render(request, 'demo/rooms_per_hotel.html', {'response': hotel_rooms,
                                                             'name': rooms[0]['hotel']['name'],
                                                             })
    except (TypeError, AttributeError, ResponseError, KeyError) as error:
        messages.add_message(request, messages.ERROR, error)
        return render(request, 'demo/rooms_per_hotel.html', {})


def book_hotel(request, offer_id):
    try:
        # Confirm availability of a given offer
        offer_availability = amadeus.shopping.hotel_offer_search(offer_id).get()
        if offer_availability.status_code == 200:
            guests = [
                {
                    "tid": 1,
                    "title": "MR",
                    "firstName": "BOB",
                    "lastName": "SMITH",
                    "phone": "+33679278416",
                    "email": "bob.smith@email.com"
                }
            ]
            travel_agent = {
                "contact": {
                    "email": "test@test.com"
                }
            }

            room_associations = [
                {
                    "guestReferences": [
                        {
                            "guestReference": "1"
                        }
                    ],
                    "hotelOfferId": offer_id
                }
            ]

            payment = {
                "method": "CREDIT_CARD",
                "paymentCard": {
                    "paymentCardInfo": {
                        "vendorCode": "VI",
                        "cardNumber": "4151289722471370",
                        "expiryDate": "2030-08",
                        "holderName": "BOB SMITH"
                    }
                }
            }
            booking = amadeus.booking.hotel_orders.post(
                guests=guests,
                travel_agent=travel_agent,
                room_associations=room_associations,
                payment=payment).data
        else:
            return render(request, 'demo/booking.html', {'response': 'The room is not available'})
    except ResponseError as error:
        messages.add_message(request, messages.ERROR, error.response.body)
        return render(request, 'demo/booking.html', {})
    return render(request, 'demo/booking.html', {'pnr': booking['associatedRecords'][0]['reference'],
                                                 'status': booking['hotelBookings'][0]['bookingStatus'],
                                                 'providerConfirmationId':
                                                     booking['hotelBookings'][0]['hotelProviderInformation'][0][
                                                         'confirmationNumber']
                                                 })

