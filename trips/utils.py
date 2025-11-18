from urllib.parse import quote, quote_plus


def generate_google_maps_link_city(city_name, country_name):

    location = f"{city_name}, {country_name}".strip()

    encoded_location = quote(location)  # правильно кодує пробіли, апострофи, букви
    return f"https://www.google.com/maps/search/?api=1&query={encoded_location}"

def generate_google_maps_link_country(country_name):
    encoded_name = quote_plus(country_name)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_name}"