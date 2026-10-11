"""Pure planning logic: no network, no AWS. This is the heart of AirWindow.

Given an hourly AQI forecast it answers three questions for one person:
  1. When should I open my windows (and when keep them shut)?
  2. When is the best hour(s) for my walk / run / commute?
  3. Do I need a mask, and is the air getting better or worse?
"""
from datetime import datetime, timedelta, timezone

from .aqi import category

# How much more strongly the same AQI affects each group (applied to the AQI number).
PROFILES = {
    "general": 1.0,
    "outdoor_worker": 1.15,
    "child": 1.25,
    "elderly": 1.25,
    "pregnant": 1.3,
    "respiratory": 1.5,
}
SENSITIVE_PROFILES = {"child", "elderly", "pregnant", "respiratory"}

# Relative breathing rate: you inhale several times more air while running than at rest.
VENT = {"rest": 1.0, "commute": 2.0, "walk": 2.5, "run": 5.0}
# Highest "effective AQI" (AQI x profile factor) at which we call an activity fine.
LIMIT = {"walk": 100, "commute": 150, "run": 75}
# Allowed local hours (first hour start inclusive, last hour end exclusive).
ALLOWED_HOURS = {"walk": (5, 22), "run": (5, 22), "commute": (6, 23)}
# Windows are "open" when the effective AQI outdoors is at or below this.
VENT_LIMIT = 100


def _parse(t: str) -> datetime:
    return datetime.fromisoformat(t)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


def _correct_with_station(series, station):
    """Nowcast bias correction: nudge the model toward a real station reading,
    fading the correction out over 6 hours. We never lower risk by more than half
    the gap, because under-warning is worse than over-warning."""
    if not station or station.get("aqi") is None:
        for p in series:
            p["aqi"] = p["raw"]
        return None
    bias = float(station["aqi"]) - series[0]["raw"]
    bias = max(-60.0, min(100.0, bias))
    if bias < 0:
        bias *= 0.5
    for i, p in enumerate(series):
        p["aqi"] = max(0.0, p["raw"] + bias * max(0.0, 1 - i / 6))
    return {
        "station_aqi": round(float(station["aqi"])),
        "model_aqi": round(series[0]["raw"]),
        "bias_applied": round(bias),
        "pollutant": station.get("pollutant"),
    }


def _ranges(series, pred):
    """Contiguous runs of hours where pred(point) is true -> [{start,end}]."""
    out, run = [], []
    for p in series:
        if pred(p) and (not run or p["t"] - run[-1]["t"] == timedelta(hours=1)):
            run.append(p)
            continue
        if run:
            out.append(run)
        run = [p] if pred(p) else []
    if run:
        out.append(run)
    return [{"start": _iso(r[0]["t"]), "end": _iso(r[-1]["t"] + timedelta(hours=1))} for r in out]


def _activity_plan(series, activity, duration_h):
    lo, hi = ALLOWED_HOURS[activity]
    limit = LIMIT[activity]
    cands = []
    for i in range(len(series) - duration_h + 1):
        chunk = series[i : i + duration_h]
        if any(not (lo <= p["t"].hour < hi) for p in chunk):
            continue
        if any(chunk[j + 1]["t"] - chunk[j]["t"] != timedelta(hours=1) for j in range(len(chunk) - 1)):
            continue
        mean_eff = sum(p["eff"] for p in chunk) / duration_h
        cands.append(
            {
                "i": i,
                "start": _iso(chunk[0]["t"]),
                "end": _iso(chunk[-1]["t"] + timedelta(hours=1)),
                "mean_aqi": round(sum(p["aqi"] for p in chunk) / duration_h),
                "mean_effective_aqi": round(mean_eff),
                "ok": max(p["eff"] for p in chunk) <= limit,
            }
        )
    cands.sort(key=lambda c: (c["mean_effective_aqi"], c["i"]))
    best, used = [], set()
    for c in cands:  # greedy, non-overlapping
        span = set(range(c["i"], c["i"] + duration_h))
        if span & used:
            continue
        used |= span
        best.append({k: v for k, v in c.items() if k != "i"})
        if len(best) == 3:
            break
    if not best:
        verdict = "avoid"
    elif any(b["ok"] for b in best):
        verdict = "go"
    elif best[0]["mean_effective_aqi"] <= limit * 1.5:
        verdict = "limit"
    else:
        verdict = "avoid"
    return {"type": activity, "duration_h": duration_h, "verdict": verdict, "best": best}


def build_plan(
    hourly,
    utc_offset,
    profile="general",
    activity="walk",
    duration_h=1,
    station=None,
    now_utc=None,
    horizon=24,
):
    """Build the full personalised plan. `hourly` items: {time, aqi, pm25, pm10}."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    if activity not in VENT:
        raise ValueError(f"unknown activity: {activity}")
    duration_h = max(1, min(3, int(duration_h)))
    now_utc = now_utc or datetime.now(timezone.utc)
    local_now = (now_utc + timedelta(seconds=utc_offset)).replace(
        tzinfo=None, minute=0, second=0, microsecond=0
    )

    series = []
    for h in hourly:
        if h.get("aqi") is None:
            continue
        t = _parse(h["time"])
        if t >= local_now:
            series.append({"t": t, "raw": float(h["aqi"]), "pm25": h.get("pm25"), "pm10": h.get("pm10")})
        if len(series) >= horizon:
            break
    if not series:
        raise ValueError("no forecast data for the requested window")

    ground_truth = _correct_with_station(series, station)
    sens = PROFILES[profile]
    for p in series:
        p["eff"] = p["aqi"] * sens

    strip = [
        {
            "time": _iso(p["t"]),
            "hour": p["t"].hour,
            "aqi": round(p["aqi"]),
            "effective_aqi": round(p["eff"]),
            "level": category(p["eff"]),
            "window": "open" if p["eff"] <= VENT_LIMIT else "closed",
            "pm25": p["pm25"],
        }
        for p in series
    ]

    open_ranges = _ranges(series, lambda p: p["eff"] <= VENT_LIMIT)
    purge = None
    if not open_ranges:
        daytime = [p for p in series if 6 <= p["t"].hour < 22]
        if daytime:
            low = min(daytime, key=lambda p: p["eff"])
            if low["eff"] <= 150:
                purge = {"time": _iso(low["t"]), "minutes": 10}

    near = max(p["eff"] for p in series[:3])
    mask = "n95" if near > 150 else "consider" if near > 100 else "none"

    trend = "steady"
    if len(series) >= 6:
        now_avg = sum(p["eff"] for p in series[:2]) / 2
        later_avg = sum(p["eff"] for p in series[3:6]) / 3
        if later_avg - now_avg >= 15:
            trend = "worsening"
        elif now_avg - later_avg >= 15:
            trend = "improving"

    act = None if activity == "rest" else _activity_plan(series, activity, duration_h)

    return {
        "profile": profile,
        "now": {
            "time": strip[0]["time"],
            "aqi": strip[0]["aqi"],
            "effective_aqi": strip[0]["effective_aqi"],
            "level": strip[0]["level"],
        },
        "strip": strip,
        "ventilation": {"open_ranges": open_ranges, "purge": purge},
        "activity": act,
        "mask": mask,
        "trend": trend,
        "ground_truth": ground_truth,
    }


def peak_aqi(plan, hours=6):
    """Highest (profile-independent) AQI in the next `hours` hours. Used for alerts."""
    return max(p["aqi"] for p in plan["strip"][:hours])
