from django.urls import path
from .views import country_list, country_detail, CityListView, TripListView

urlpatterns = [
    path('countries/', country_list),
    path('countries/<int:country_id>/', country_detail),    path("cities/", CityListView.as_view(), name="city-list"),
    path("trips/", TripListView.as_view(), name="trip-list"),
]
