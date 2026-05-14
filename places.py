"""Google Places API (v1 / New API) integration for shop enrichment."""

import os
import re
import urllib.parse
from typing import Any, Optional

import requests

_PLACES_URL  = "https://places.googleapis.com/v1/places:searchText"
_PLACE_URL   = "https://places.googleapis.com/v1/places/{place_id}"
_FIELD_MASK  = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.addressComponents,"
    "places.rating,"
    "places.googleMapsUri,"
    "places.editorialSummary,"
    "places.types"
)
_DETAIL_MASK = (
    "id,displayName,formattedAddress,addressComponents,"
    "rating,googleMapsUri,editorialSummary,types"
)

# Patterns that can carry a Place ID inside a Google Maps URL
_PLACE_ID_RE  = re.compile(r"[?&]place_id=([^&]+)")
_CID_RE       = re.compile(r"[?&]cid=(\d+)")
_DATA_FID_RE  = re.compile(r"0x[0-9a-f]+:0x([0-9a-f]+)", re.I)   # hex CID in /data=


def _api_key() -> Optional[str]:
    return os.environ.get("GOOGLE_PLACES_API_KEY")


def _headers(mask: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": mask,
    }


def _place_to_dict(place: dict) -> dict[str, Any]:
    editorial   = place.get("editorialSummary") or {}
    types       = place.get("types") or []
    components  = place.get("addressComponents") or []
    return {
        "place_id":        place.get("id"),
        "shop_name":       (place.get("displayName") or {}).get("text"),
        "address":         place.get("formattedAddress"),
        "location":        _extract_locality(components),
        "rating":          place.get("rating"),
        "google_maps_url": place.get("googleMapsUri"),
        "description":     editorial.get("text"),
        "food_types":      _types_to_zh(types),
    }


def _extract_locality(components: list[dict]) -> Optional[str]:
    """Return the city/town name from addressComponents (locality → level_2 → level_1)."""
    priority = ("locality", "administrative_area_level_2", "administrative_area_level_1")
    bucket: dict[str, str] = {}
    for comp in components:
        for t in comp.get("types") or []:
            if t in priority and t not in bucket:
                bucket[t] = comp.get("longText") or comp.get("shortText") or ""
    for key in priority:
        if bucket.get(key):
            return bucket[key]
    return None


# Rough mapping of Google place types to Chinese food categories
_TYPE_ZH: dict[str, str] = {
    "restaurant":      "餐厅",
    "cafe":            "咖啡馆",
    "bakery":          "面包店",
    "bar":             "酒吧",
    "meal_takeaway":   "外卖",
    "meal_delivery":   "送餐",
    "food":            "美食",
    "chinese_restaurant": "中餐厅",
    "japanese_restaurant": "日式餐厅",
    "korean_restaurant": "韩式餐厅",
    "ramen_restaurant": "拉面",
    "sushi_restaurant": "寿司",
    "seafood_restaurant": "海鲜",
    "fast_food_restaurant": "快餐",
    "indian_restaurant": "印度餐厅",
    "thai_restaurant": "泰式餐厅",
}


def _types_to_zh(types: list[str]) -> list[str]:
    seen, result = set(), []
    for t in types:
        zh = _TYPE_ZH.get(t)
        if zh and zh not in seen:
            seen.add(zh)
            result.append(zh)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_google_places(
    shop_name: str,
    location: str = "",
) -> Optional[dict[str, Any]]:
    """Text-search Google Places by name + location. Returns enriched dict or None."""
    if not _api_key():
        return None

    query = f"{shop_name} {location}".strip()
    try:
        resp = requests.post(
            _PLACES_URL,
            json={"textQuery": query, "languageCode": "zh-CN"},
            headers=_headers(_FIELD_MASK),
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    places = resp.json().get("places") or []
    return _place_to_dict(places[0]) if places else None


def lookup_by_url(url: str) -> Optional[dict[str, Any]]:
    """Extract a Place ID from a Google Maps URL and fetch full details.

    Supports:
    - https://maps.google.com/?cid=...
    - https://www.google.com/maps/place/...?place_id=...
    - https://www.google.com/maps/place/Name/@lat,lng/data=...0x...:0x<cid_hex>...
    - Falls back to text search using the place name in the URL path.
    """
    if not _api_key():
        return None

    place_id = _extract_place_id(url)
    if place_id:
        return _fetch_place_details(place_id)

    # Fall back: try to parse a shop name from the URL path and text-search it
    shop_name = _name_from_url(url)
    if shop_name:
        return search_google_places(shop_name)

    return None


def _extract_place_id(url: str) -> Optional[str]:
    """Pull a Places API place_id string out of a Maps URL if present."""
    # Explicit place_id= param
    m = _PLACE_ID_RE.search(url)
    if m:
        return urllib.parse.unquote(m.group(1))

    # Numeric CID → convert to ChIJ... format via text search (no direct API)
    # Just return None so caller falls back to text search
    return None


def _fetch_place_details(place_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single place by ID from the Places API."""
    try:
        resp = requests.get(
            _PLACE_URL.format(place_id=place_id),
            headers=_headers(_DETAIL_MASK),
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    return _place_to_dict(resp.json())


def _name_from_url(url: str) -> Optional[str]:
    """Best-effort: extract a shop name from the path of a Maps URL."""
    try:
        path = urllib.parse.urlparse(url).path  # e.g. /maps/place/Shop+Name/@...
        parts = [p for p in path.split("/") if p and p not in ("maps", "place", "search")]
        if parts:
            raw = parts[0].split("@")[0]   # drop coordinates
            return urllib.parse.unquote_plus(raw)
    except Exception:
        pass
    return None


def fallback_maps_search_url(shop_name: str, location: str = "") -> str:
    """Return a Google Maps search URL (no API key needed, best-effort)."""
    query = f"{shop_name} {location}".strip()
    return "https://www.google.com/maps/search/" + urllib.parse.quote(query)
