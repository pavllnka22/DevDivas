from django.urls import path
from .views import country_list, country_detail, CityListView, TripListView, city_detail, get_weather

urlpatterns = [
    path('countries/', country_list),
    path('countries/<int:country_id>/', country_detail),
    path("cities/", CityListView.as_view(), name="city-list"),
    path("cities/<int:city_id>/", city_detail),
    path("trips/", TripListView.as_view(), name="trip-list"),
    path("weather/<int:city_id>/", get_weather),

]

