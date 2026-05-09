"""Google Places API (v1 / New API) integration for shop enrichment."""

import os
import urllib.parse
from typing import Any, Optional

import requests

_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.rating,"
    "places.googleMapsUri,"
    "places.editorialSummary"
)


def search_google_places(
    shop_name: str,
    location: str = "",
) -> Optional[dict[str, Any]]:
    """Query Google Places and return enriched info, or None if unavailable."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        return None

    query = f"{shop_name} {location}".strip()

    try:
        resp = requests.post(
            _PLACES_URL,
            json={"textQuery": query, "languageCode": "zh-CN"},
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": _FIELD_MASK,
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    places = resp.json().get("places") or []
    if not places:
        return None

    place = places[0]
    editorial = place.get("editorialSummary") or {}

    return {
        "place_id":       place.get("id"),
        "address":        place.get("formattedAddress"),
        "rating":         place.get("rating"),
        "google_maps_url": place.get("googleMapsUri"),
        "description":    editorial.get("text"),
    }


def fallback_maps_search_url(shop_name: str, location: str = "") -> str:
    """Return a Google Maps search URL (no API key needed, best-effort)."""
    query = f"{shop_name} {location}".strip()
    return "https://www.google.com/maps/search/" + urllib.parse.quote(query)
