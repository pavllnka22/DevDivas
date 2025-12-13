import requests
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from TravellinoCappuchino import settings
from .models import Country, City, Trip
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