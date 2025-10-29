from rest_framework import serializers
from .models import Country, City, Trip, Accommodation, Flight


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'description', 'flag_url', 'currency']


class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "country"]


class TripSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ["id", "title", "description", "price", "duration_days", "city"]
