import json
from datetime import datetime, timezone

from airwindow import sources, store
import api_handler

from test_planner import HOURLY


def ev(path, method="GET", q=None, body=None):
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "queryStringParameters": q,
        "body": json.dumps(body) if body is not None else None,
    }


def fake_forecast(monkeypatch):
    # shift the fixture so it always starts at the current UTC hour
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    hourly = [
        {**h, "time": (now.replace() + (datetime.fromisoformat(h["time"]) - datetime(2026, 10, 11))).isoformat(timespec="minutes")}
        for h in HOURLY
    ]
    monkeypatch.setattr(sources, "fetch_hourly", lambda lat, lon: {"utc_offset": 0, "hourly": hourly})
    monkeypatch.setattr(
        sources, "geocode",
        lambda name: {"name": "Hyderabad", "lat": 17.38, "lon": 78.48, "country": "India",
                      "admin1": "Telangana", "slug": "hyderabad", "key": "hyderabad-in"},
    )


def test_health_and_page():
    assert api_handler.handler(ev("/api/health"))["statusCode"] == 200
    page = api_handler.handler(ev("/"))
    assert page["statusCode"] == 200 and "AirWindow" in page["body"]


def test_plan_ok(monkeypatch):
    fake_forecast(monkeypatch)
    r = api_handler.handler(ev("/api/plan", q={"city": "Hyderabad", "profile": "child", "lang": "te"}))
    assert r["statusCode"] == 200
    body = json.loads(r["body"])
    assert body["place"]["name"] == "Hyderabad"
    assert len(body["plan"]["strip"]) == 24 and body["tips"]


def test_plan_uses_station_when_cached(monkeypatch):
    fake_forecast(monkeypatch)
    import time
    store.put("gt#hyderabad-in", {"aqi": 300, "pollutant": "PM2.5", "fetched_at": time.time()})
    body = json.loads(api_handler.handler(ev("/api/plan", q={"city": "Hyderabad"}))["body"])
    assert body["plan"]["ground_truth"]["station_aqi"] == 300
    assert body["sources"]["station_check"]


def test_validation_errors(monkeypatch):
    fake_forecast(monkeypatch)
    assert api_handler.handler(ev("/api/plan", q={}))["statusCode"] == 400
    assert api_handler.handler(ev("/api/plan", q={"city": "x", "profile": "zzz"}))["statusCode"] == 400
    assert api_handler.handler(ev("/api/plan", q={"lat": "999", "lon": "0"}))["statusCode"] == 400
    assert api_handler.handler(ev("/api/plan", q={"city": "x", "lang": "xx"}))["statusCode"] == 400


def test_unknown_route():
    assert api_handler.handler(ev("/nope"))["statusCode"] == 404


def test_subscribe_needs_aws():
    r = api_handler.handler(ev("/api/subscribe", "POST", body={"email": "a@b.co", "city": "Hyderabad"}))
    assert r["statusCode"] == 501
