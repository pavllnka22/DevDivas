from django.http import JsonResponse
from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.response import Response

from .models import Country, City, Trip
from .serializers import CountrySerializer, CitySerializer, TripSerializer


def country_list(request):
    countries = Country.objects.all().values('id', 'name', 'description', 'flag_url', 'currency')
    return JsonResponse(list(countries), safe=False)

def country_detail(request, country_id):
    try:
        country = Country.objects.values('id', 'name', 'description', 'flag_url', 'currency').get(id=country_id)
        return JsonResponse(country, safe=False)
    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)
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
