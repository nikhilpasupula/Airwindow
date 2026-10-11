"""Lambda handler behind API Gateway (HTTP API, payload v2). Also serves the web page."""
import base64
import json
import os

from airwindow import advice, groundtruth, i18n, notify, planner, sources, store

WEB = os.path.join(os.path.dirname(__file__), "web", "index.html")
MAX_WATCHED_CITIES = 10


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def _resp(status, body, ctype="application/json", cache="no-store"):
    return {
        "statusCode": status,
        "headers": {"Content-Type": ctype, "Cache-Control": cache},
        "body": body if isinstance(body, str) else json.dumps(body, ensure_ascii=False),
    }


def _place(q):
    city = (q.get("city") or "").strip()
    if city:
        if len(city) > 80:
            raise HttpError(400, "City name is too long.")
        try:
            place = sources.geocode(city)
        except Exception as exc:
            print(f"geocode failed: {exc}")
            raise HttpError(502, "City lookup is unavailable right now. Try again in a minute.")
        if not place:
            raise HttpError(404, f"Could not find a city called '{city}'.")
        return place
    try:
        lat, lon = float(q["lat"]), float(q["lon"])
    except (KeyError, TypeError, ValueError):
        raise HttpError(400, "Give a city, or both lat and lon.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HttpError(400, "lat/lon out of range.")
    return {"name": f"{lat:.2f}, {lon:.2f}", "lat": lat, "lon": lon, "key": None, "slug": None}


def plan_route(q):
    profile = q.get("profile", "general")
    activity = q.get("activity", "walk")
    lang = q.get("lang", "en")
    if profile not in planner.PROFILES:
        raise HttpError(400, f"profile must be one of {sorted(planner.PROFILES)}")
    if activity not in planner.VENT:
        raise HttpError(400, f"activity must be one of {sorted(planner.VENT)}")
    if lang not in i18n.LANGUAGES:
        raise HttpError(400, f"lang must be one of {sorted(i18n.LANGUAGES)}")
    try:
        duration = int(q.get("duration", 1))
    except ValueError:
        raise HttpError(400, "duration must be a number of hours (1-3).")

    place = _place(q)
    try:
        fc = sources.fetch_hourly(place["lat"], place["lon"])
    except Exception as exc:
        print(f"forecast failed: {exc}")
        raise HttpError(502, "The air-quality forecast service is unavailable. Try again shortly.")
    station = groundtruth.fresh(place.get("key"))
    try:
        plan = planner.build_plan(
            fc["hourly"], fc["utc_offset"], profile, activity, duration, station=station
        )
    except ValueError as exc:
        raise HttpError(502, str(exc))

    return {
        "place": {k: place.get(k) for k in ("name", "admin1", "country", "lat", "lon", "key")},
        "plan": plan,
        "tips": advice.tips(plan, lang),
        "briefing": advice.briefing(plan, place["name"], lang),
        "sources": {
            "forecast": "Open-Meteo Air Quality (CAMS)",
            "station_check": "TinyFish web agent" if station else None,
        },
    }


def subscribe_route(body):
    if not notify.enabled():
        raise HttpError(501, "Alerts are only available on the AWS deployment.")
    email = (body.get("email") or "").strip()
    profile = body.get("profile", "general")
    if not notify.EMAIL_RE.match(email):
        raise HttpError(400, "Enter a valid email address.")
    if profile not in planner.PROFILES:
        raise HttpError(400, "Unknown profile.")
    place = _place({"city": body.get("city", "")})
    watched = store.scan_prefix("watch#")
    if place["key"] not in {w["key"] for w in watched} and len(watched) >= MAX_WATCHED_CITIES:
        raise HttpError(409, "Alert coverage is full for now. Try a nearby major city.")
    store.put(f"watch#{place['key']}", {k: place[k] for k in ("key", "name", "lat", "lon", "slug")})
    notify.subscribe(email, place["key"], profile in planner.SENSITIVE_PROFILES)
    return {"message": f"Check your inbox for a confirmation email to start alerts for {place['name']}."}


def handler(event, _context=None):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    q = event.get("queryStringParameters") or {}
    try:
        if method == "GET" and path == "/":
            with open(WEB, encoding="utf-8") as f:
                return _resp(200, f.read(), "text/html; charset=utf-8", "public, max-age=300")
        if method == "GET" and path == "/api/health":
            return _resp(200, {"ok": True})
        if method == "GET" and path == "/api/plan":
            return _resp(200, plan_route(q), cache="public, max-age=300")
        if method == "POST" and path == "/api/subscribe":
            raw = event.get("body") or "{}"
            if event.get("isBase64Encoded"):
                raw = base64.b64decode(raw).decode("utf-8")
            try:
                body = json.loads(raw)
            except ValueError:
                raise HttpError(400, "Body must be JSON.")
            return _resp(200, subscribe_route(body))
        return _resp(404, {"error": "Not found"})
    except HttpError as e:
        return _resp(e.status, {"error": e.message})
    except Exception as exc:  # last-resort guard; details stay in CloudWatch
        print(f"unhandled error: {exc!r}")
        return _resp(500, {"error": "Something went wrong on our side."})
