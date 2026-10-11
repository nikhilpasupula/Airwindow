"""TinyFish Web Agent client (plain urllib, no extra dependency).

TinyFish turns a public web page + a plain-English goal into structured JSON. We use it
to read the live reading of a real monitoring station, which has no free public API.
Docs: https://docs.tinyfish.ai  (POST /v1/automation/run, header X-API-Key)
"""
import json
import os
import urllib.request

AGENT_URL = os.environ.get("TINYFISH_AGENT_URL", "https://agent.tinyfish.ai/v1/automation/run")
_cached_key = None

GOAL = (
    "Find the current Air Quality Index (AQI) number for this city and its main pollutant. "
    'Return JSON only, like {"aqi": 123, "pollutant": "PM2.5", "updated": "10:00"}. '
    "If a list of stations is shown, use the city's headline or average reading. "
    'If no AQI is visible, return {"aqi": null}.'
)


def get_api_key():
    """Env var for local dev; SSM SecureString parameter on AWS."""
    global _cached_key
    if _cached_key:
        return _cached_key
    key = os.environ.get("TINYFISH_API_KEY")
    if not key and os.environ.get("TINYFISH_KEY_PARAM"):
        import boto3

        key = boto3.client("ssm").get_parameter(
            Name=os.environ["TINYFISH_KEY_PARAM"], WithDecryption=True
        )["Parameter"]["Value"]
    _cached_key = key
    return key


def run_agent(url, goal, api_key, timeout=120):
    body = json.dumps({"url": url, "goal": goal}).encode()
    req = urllib.request.Request(
        AGENT_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec - fixed https host
        return json.loads(r.read().decode("utf-8"))


def extract_aqi(url, api_key):
    """Return {aqi, pollutant, updated} or None if the agent could not find a reading."""
    run = run_agent(url, GOAL, api_key)
    if run.get("status") not in (None, "COMPLETED"):
        return None
    result = run.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return None
    if not isinstance(result, dict):
        return None
    try:
        aqi = int(result.get("aqi"))
    except (TypeError, ValueError):
        return None
    if not 0 <= aqi <= 1000:
        return None
    return {"aqi": aqi, "pollutant": result.get("pollutant"), "updated": result.get("updated")}
