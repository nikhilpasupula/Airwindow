from datetime import datetime, timezone

import pytest

from airwindow import advice, planner
from airwindow.aqi import category

NOW = datetime(2026, 10, 11, 0, 30, tzinfo=timezone.utc)  # offset 0 -> local 00:30


def make_hourly(values, start="2026-10-11T00:00"):
    base = datetime.fromisoformat(start)
    out = []
    for i, v in enumerate(values):
        t = base.replace(hour=0) + (datetime(2026, 1, 1, i % 24) - datetime(2026, 1, 1))
        day = base.day + i // 24
        out.append({"time": t.replace(day=day).isoformat(timespec="minutes"), "aqi": v, "pm25": v / 2, "pm10": v})
    return out


# 48h: smoggy night (170), clean morning 06-09 (40), moderate afternoon (90), dirty evening (160)
DAY = [170] * 6 + [40] * 4 + [70] * 4 + [90] * 4 + [160] * 6
HOURLY = make_hourly(DAY * 2)


def plan(**kw):
    kw.setdefault("now_utc", NOW)
    return planner.build_plan(HOURLY, 0, **kw)


def test_categories():
    assert category(50) == "good" and category(51) == "moderate"
    assert category(150) == "sensitive" and category(151) == "unhealthy"
    assert category(301) == "hazardous"


def test_strip_has_24_hours_from_now():
    p = plan()
    assert len(p["strip"]) == 24
    assert p["strip"][0]["time"] == "2026-10-11T00:00"


def test_windows_open_in_clean_hours_only():
    p = plan()
    first = p["ventilation"]["open_ranges"][0]
    assert first["start"] == "2026-10-11T06:00"
    assert first["end"] == "2026-10-11T14:00" or first["end"] <= "2026-10-11T18:00"
    assert all(h["window"] == "closed" for h in p["strip"][:6])


def test_respiratory_profile_is_stricter():
    general = plan(profile="general")["ventilation"]["open_ranges"]
    resp = plan(profile="respiratory")["ventilation"]["open_ranges"]
    g_hours = sum(1 for h in plan(profile="general")["strip"] if h["window"] == "open")
    r_hours = sum(1 for h in plan(profile="respiratory")["strip"] if h["window"] == "open")
    assert r_hours < g_hours and general and resp


def test_best_run_is_in_the_clean_morning():
    p = plan(activity="run", duration_h=2)
    best = p["activity"]["best"][0]
    assert best["start"] >= "2026-10-11T06:00" and best["end"] <= "2026-10-11T10:00"
    assert p["activity"]["verdict"] == "go"
    starts = [b["start"] for b in p["activity"]["best"]]
    assert len(starts) == len(set(starts))


def test_activity_never_scheduled_at_night():
    p = plan(activity="walk", duration_h=1)
    for b in p["activity"]["best"]:
        assert 5 <= int(b["start"][11:13]) < 22


def test_all_day_bad_air_advises_purge_or_indoors():
    bad = make_hourly([210] * 48)
    p = planner.build_plan(bad, 0, activity="run", now_utc=NOW)
    assert p["ventilation"]["open_ranges"] == []
    assert p["ventilation"]["purge"] is None  # too dirty even for a quick air change
    assert p["activity"]["verdict"] == "avoid"
    assert p["mask"] == "n95"


def test_purge_when_least_bad_hour_is_tolerable():
    mid = make_hourly([130] * 12 + [110] * 4 + [130] * 32)
    p = planner.build_plan(mid, 0, now_utc=NOW)
    assert p["ventilation"]["open_ranges"] == []
    assert p["ventilation"]["purge"]["time"] == "2026-10-11T12:00"


def test_station_correction_raises_risk_and_fades():
    base = plan()
    corrected = plan(station={"aqi": 260, "pollutant": "PM2.5"})
    assert corrected["now"]["aqi"] > base["now"]["aqi"]
    assert corrected["strip"][6]["aqi"] == base["strip"][6]["aqi"]  # faded out after 6h
    assert corrected["ground_truth"]["station_aqi"] == 260


def test_station_cannot_fully_lower_risk():
    p = plan(station={"aqi": 10})
    assert p["now"]["aqi"] > 10  # only half the gap is trusted


def test_trend_detection():
    rising = make_hourly([40, 40, 40, 100, 120, 140] + [150] * 42)
    p = planner.build_plan(rising, 0, now_utc=NOW)
    assert p["trend"] == "worsening"


def test_rest_activity_has_no_activity_block():
    assert plan(activity="rest")["activity"] is None


def test_invalid_inputs():
    with pytest.raises(ValueError):
        plan(profile="alien")
    with pytest.raises(ValueError):
        plan(activity="fly")


@pytest.mark.parametrize("lang", ["en", "hi", "te", "ta"])
def test_tips_exist_in_every_language(lang):
    tips = advice.tips(plan(activity="walk"), lang)
    assert len(tips) >= 2 and all(isinstance(t, str) and t for t in tips)


def test_peak_aqi():
    assert planner.peak_aqi(plan(), hours=6) == 170
