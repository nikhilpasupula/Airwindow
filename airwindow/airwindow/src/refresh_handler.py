"""Scheduled Lambda (EventBridge, every few hours).

For each watched city: 1) read the real station with TinyFish, 2) re-run the forecast,
3) email subscribers through SNS if air is about to turn bad (with de-duplication).
"""
from concurrent.futures import ThreadPoolExecutor

from airwindow import groundtruth, notify, planner, sources, store

SENSITIVE_AT = 101   # "unhealthy for sensitive groups"
EVERYONE_AT = 151    # "unhealthy"
ALERT_TTL_S = 12 * 3600
RANK = {"sensitive": 1, "all": 2}


def _process(city):
    name, key = city["name"], city["key"]
    try:
        groundtruth.refresh(city)
    except Exception as exc:  # station check is a bonus; carry on with the model
        print(f"[{key}] ground truth skipped: {exc}")
    try:
        sources_fc = sources.fetch_hourly(city["lat"], city["lon"])
        plan = planner.build_plan(
            sources_fc["hourly"], sources_fc["utc_offset"], "general", "rest",
            station=groundtruth.fresh(key),
        )
    except Exception as exc:
        print(f"[{key}] forecast failed: {exc}")
        return {"city": key, "status": "forecast_failed"}

    peak = planner.peak_aqi(plan, 6)
    audience = "all" if peak >= EVERYONE_AT else "sensitive" if peak >= SENSITIVE_AT else None
    if not audience:
        return {"city": key, "status": "ok", "peak": peak}

    last = store.get(f"alert#{key}")
    if last and RANK[last["audience"]] >= RANK[audience]:
        return {"city": key, "status": "already_alerted", "peak": peak}

    text = (
        f"AirWindow alert for {name}\n\n"
        f"Air quality is expected to reach AQI {peak} in the next 6 hours "
        f"({'unhealthy for everyone' if audience == 'all' else 'unhealthy for sensitive groups'}).\n"
        "Keep windows closed, avoid hard exercise outdoors, and wear an N95 mask if you must go out.\n"
        "Open AirWindow for the hour-by-hour plan."
    )
    notify.publish(key, name, audience, text)
    store.put(f"alert#{key}", {"audience": audience, "peak": peak}, ttl_s=ALERT_TTL_S)
    return {"city": key, "status": "alert_sent", "peak": peak, "audience": audience}


def handler(event=None, _context=None):
    cities = store.scan_prefix("watch#")
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(_process, cities))
    print(results)
    return {"processed": len(results), "results": results}
