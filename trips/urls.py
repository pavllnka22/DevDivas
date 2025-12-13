from django.urls import path

from . import views
from .views import country_list, country_detail, CityListView, TripListView, city_detail, get_weather, \
    generate_city_trip_view, SaveTripView

urlpatterns = [

    path('countries/', country_list),
    path('countries/<int:country_id>/', country_detail),
    path("cities/", CityListView.as_view(), name="city-list"),
    path("cities/<int:city_id>/", city_detail),
    path('trips/city-to-iata/', views.city_to_iata, name='city-to-iata'),
    path("trips/", TripListView.as_view(), name="trip-list"),
    path("weather/<int:city_id>/", get_weather),
    path("trips/generate_city/", generate_city_trip_view, name="generate-city-trip"),

    path('trips/hotels/', views.hotel_search, name='hotels_search'),

    path('trips/save-trip/', SaveTripView.as_view(), name='save_trip'),

    path('trips/flights/', views.flight_offers, name='flight_offers'),
    path('trips/origin_airport_search/', views.origin_airport_search, name='origin_airport_search'),
    path('trips/destination_airport_search/', views.destination_airport_search, name='destination_airport_search')
]
