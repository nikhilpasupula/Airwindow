"""Turn a plan into plain-language tips (templates) and an optional Bedrock briefing."""
import hashlib
import json
import os
from datetime import datetime

from . import i18n, store


def _fmt_range(start, end, lang, first_day):
    t = i18n.T[lang]
    s, e = datetime.fromisoformat(start), datetime.fromisoformat(end)
    day = f"{t['tomorrow']} " if s.date() != first_day else ""
    return f"{day}{s:%H:%M}–{e:%H:%M}"


def tips(plan, lang="en"):
    """Deterministic, safe tips. Falls back to English for languages without templates."""
    lang = lang if lang in i18n.T else "en"
    t = i18n.T[lang]
    first_day = datetime.fromisoformat(plan["strip"][0]["time"]).date()
    out = []

    vent = plan["ventilation"]
    if vent["open_ranges"]:
        rngs = ", ".join(_fmt_range(r["start"], r["end"], lang, first_day) for r in vent["open_ranges"][:2])
        out.append(t["open"].format(range=rngs))
    elif vent["purge"]:
        when = _fmt_range(vent["purge"]["time"], vent["purge"]["time"], lang, first_day).split("–")[0]
        out.append(t["no_open_purge"].format(time=when))
    else:
        out.append(t["no_open"])

    act = plan["activity"]
    if act:
        name = t["activity"][act["type"]]
        if act["verdict"] == "avoid" or not act["best"]:
            out.append(t["activity_avoid"].format(activity=name))
        else:
            b = act["best"][0]
            key = "activity_go" if act["verdict"] == "go" else "activity_limit"
            out.append(t[key].format(activity=name, range=_fmt_range(b["start"], b["end"], lang, first_day)))

    if plan["mask"] != "none":
        out.append(t["mask_" + plan["mask"]])
    if plan["trend"] != "steady":
        out.append(t["trend_" + plan["trend"]])
    return out


SYSTEM = (
    "You are a careful air-quality assistant for the general public in India. "
    "Write ONLY from the facts provided. Never add numbers, times or medical claims that are not in the facts. "
    "Use 2 or 3 short, friendly sentences in plain words. No markdown, no emojis."
)


def briefing(plan, place_name, lang):
    """Optional Amazon Bedrock rewrite of the facts in any supported language. Returns None on any failure."""
    if os.environ.get("USE_BEDROCK", "false").lower() != "true" or lang not in i18n.LANGUAGES:
        return None
    facts = tips(plan, "en")
    cache_key = "br#" + hashlib.sha1(json.dumps([facts, lang, place_name]).encode()).hexdigest()
    hit = store.get(cache_key)
    if hit:
        return hit["text"]
    try:
        import boto3

        client = boto3.client("bedrock-runtime")
        prompt = (
            f"City: {place_name}\nCurrent AQI: {plan['now']['aqi']} ({plan['now']['level']})\n"
            "Facts:\n- " + "\n- ".join(facts) + f"\n\nWrite the daily air briefing in {i18n.LANGUAGES[lang]}."
        )
        resp = client.converse(
            modelId=os.environ["BEDROCK_MODEL_ID"],
            system=[{"text": SYSTEM}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 220, "temperature": 0.3},
        )
        text = resp["output"]["message"]["content"][0]["text"].strip()
    except Exception as exc:  # never break the page because the AI step failed
        print(f"bedrock briefing skipped: {exc}")
        return None
    store.put(cache_key, {"text": text}, ttl_s=3600)
    return text
