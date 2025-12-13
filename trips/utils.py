from urllib.parse import quote, quote_plus


def generate_google_maps_link_city(city_name, country_name):

    location = f"{city_name}, {country_name}".strip()

    encoded_location = quote(location)  # правильно кодує пробіли, апострофи, букви
    return f"https://www.google.com/maps/search/?api=1&query={encoded_location}"


def generate_google_maps_embed_city(city_name, country_name, api_key):
    location = f"{city_name}, {country_name}".strip()
    encoded = quote(location)
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded}"


def generate_google_maps_link_country(country_name):
    encoded_name = quote_plus(country_name)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_name}"

def generate_google_maps_embed_country(country_name, api_key):
    encoded_name = quote_plus(country_name)
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded_name}"


