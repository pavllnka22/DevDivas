import requests
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response

from TravellinoCappuchino import settings
from .models import Country, City, Trip
from .serializers import CitySerializer, TripSerializer, CountrySerializer


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

