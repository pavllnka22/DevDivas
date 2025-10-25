from django.contrib import admin
from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

admin.site.register(Country)

class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("country", "name")

    def __str__(self):
        return f"{self.name} ({self.country.name})"

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

admin.site.register(Accommodation)

class Flight(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="flights")
    flight_title = models.CharField(max_length=200)
    flight_description = models.TextField()
    flight_price = models.DecimalField(max_digits=10, decimal_places=2)
    flight_date = models.DateField()

admin.site.register(Flight)