from amadeus import Client

from TravellinoCappuchino import settings

amadeus = Client(
    client_id=settings.AMADEUS_API_KEY,
    client_secret=settings.AMADEUS_API_SECRET
)
