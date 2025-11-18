from rest_framework import serializers
from .models import Country, City, Trip, Accommodation, Flight
from .utils import generate_google_maps_link_city, generate_google_maps_link_country


class CitySerializer(serializers.ModelSerializer):
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ["id", "name", 'description', 'img_url', 'map_url']

    def get_map_url(self, city):
        return generate_google_maps_link_city(city.name, city.country)

class CountrySerializer(serializers.ModelSerializer):
    cities = CitySerializer(many=True, read_only=True)
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ['id', 'name', 'description', 'flag_url', 'currency', 'cities', 'map_url']

    def get_map_url(self, country):
        return generate_google_maps_link_country(country.name)


class TripSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ["id", "title", "description", "price", "duration_days", "city"]
