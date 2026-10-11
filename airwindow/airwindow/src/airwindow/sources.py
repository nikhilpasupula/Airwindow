"""Open-Meteo: free air-quality forecast + geocoding. No API key needed."""
import json
import re
import urllib.parse
import urllib.request

from . import store

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"


def _get_json(url, params, timeout=8):
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "AirWindow/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec - fixed https hosts
        return json.loads(r.read().decode("utf-8"))


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def geocode(name):
    """City name -> {name, lat, lon, country, admin1, slug, key} or None. Cached 30 days."""
    ck = f"geo#{slugify(name)}"
    hit = store.get(ck)
    if hit:
        return hit
    data = _get_json(GEO_URL, {"name": name, "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    place = {
        "name": r["name"],
        "lat": round(r["latitude"], 4),
        "lon": round(r["longitude"], 4),
        "country": r.get("country"),
        "admin1": r.get("admin1"),
        "slug": slugify(r["name"]),
        "key": f"{slugify(r['name'])}-{(r.get('country_code') or 'xx').lower()}",
    }
    store.put(ck, place, ttl_s=30 * 24 * 3600)
    return place


def fetch_hourly(lat, lon):
    """Return {utc_offset, hourly:[{time,aqi,pm25,pm10}]} for ~48h, cached 1 hour."""
    ck = f"fc#{lat:.2f},{lon:.2f}"
    hit = store.get(ck)
    if hit:
        return hit
    d = _get_json(
        AQ_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "us_aqi,pm2_5,pm10",
            "forecast_days": 2,
            "timezone": "auto",
        },
    )
    h = d["hourly"]
    hourly, last = [], None
    for t, a, p25, p10 in zip(h["time"], h["us_aqi"], h["pm2_5"], h["pm10"]):
        if a is None:
            a = last  # forward-fill small gaps
        if a is None:
            continue
        last = a
        hourly.append({"time": t, "aqi": a, "pm25": p25, "pm10": p10})
    out = {"utc_offset": d.get("utc_offset_seconds", 0), "hourly": hourly}
    store.put(ck, out, ttl_s=3600)
    return out
