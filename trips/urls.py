from django.urls import path
from .views import CountryListView, CityListView, TripListView

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("cities/", CityListView.as_view(), name="city-list"),
    path("trips/", TripListView.as_view(), name="trip-list"),
]
