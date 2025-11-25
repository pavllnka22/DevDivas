import os

import requests
from django.contrib import admin
from django.db import models
from django import forms

from trips.utils import generate_google_maps_link_city


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    flag_url = models.URLField(blank=True, null=True)
    currency = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)


    def __str__(self):
       return self.name

admin.site.register(Country)

class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    img_url = models.URLField(blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("country", "name")

    def __str__(self):
        return f"{self.name} ({self.country.name})"

    def save(self, *args, **kwargs):
        if (self.latitude is None or self.longitude is None) and self.name and self.country:
            API_KEY = os.getenv("WEATHER_API_KEY")
            url = (
                f"http://api.openweathermap.org/geo/1.0/direct"
                f"?q={self.name}&limit=1&appid={API_KEY}"
            )
            response = requests.get(url).json()

            if response: # check if it is not empty
                self.latitude = response[0]["lat"]
                self.longitude = response[0]["lon"]

        super().save(*args, **kwargs)

admin.site.register(City)

class Trip(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="trips")
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title
admin.site.register(Trip)

class Accommodation(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="accomodations")
    accommodation_title = models.CharField(max_length=200)
    accommodation_description = models.TextField()
    accommodation_price = models.DecimalField(max_digits=10, decimal_places=2)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

admin.site.register(Accommodation)

class Flight(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="flights")
    flight_title = models.CharField(max_length=200)
    flight_description = models.TextField()
    flight_price = models.DecimalField(max_digits=10, decimal_places=2)
    flight_date = models.DateField()

admin.site.register(Flight)

class FlightBookingForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=(("MALE", "Male"), ("FEMALE", "Female")))
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)
    phone_country_code = forms.CharField(max_length=5, initial="1")
    passport_number = forms.CharField(max_length=50)
    passport_expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    passport_issuance_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    passport_issuance_location = forms.CharField(max_length=100)
    birth_place = forms.CharField(max_length=100)
    nationality = forms.CharField(max_length=5, initial="UA")
    passport_country = forms.CharField(max_length=5, initial="UA")
