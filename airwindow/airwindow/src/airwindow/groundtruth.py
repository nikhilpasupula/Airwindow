"""Ground-truth station readings fetched with TinyFish and cached in DynamoDB."""
import os
import time

from . import store, tinyfish

URL_TEMPLATE = os.environ.get("GROUND_TRUTH_URL", "https://aqicn.org/city/{slug}/")
MAX_AGE_S = 4 * 3600


def fresh(key):
    """Latest cached station reading if it is younger than 4 hours, else None."""
    if not key:
        return None
    rec = store.get(f"gt#{key}")
    if rec and time.time() - rec.get("fetched_at", 0) <= MAX_AGE_S:
        return rec
    return None


def refresh(place):
    """Ask TinyFish for the live reading and cache it. Returns the record or None."""
    api_key = tinyfish.get_api_key()
    if not api_key or not place.get("key"):
        return None
    url = URL_TEMPLATE.format(slug=place["slug"])
    result = tinyfish.extract_aqi(url, api_key)
    if not result:
        return None
    rec = {**result, "fetched_at": time.time(), "source_url": url}
    store.put(f"gt#{place['key']}", rec, ttl_s=6 * 3600)
    return rec
