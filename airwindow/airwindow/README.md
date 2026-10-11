# AirWindow

**Track: Air.** A free, multilingual web app that tells ordinary people *when to open their windows, when to walk, run or commute, and when to keep the air out* — hour by hour, for the person they pick (child, older adult, pregnant, asthma, outdoor worker).

## Why it is different

Most air apps show one number: "AQI 168". People then have to guess what to do. AirWindow turns the forecast into **actions**:

| Idea | What it does |
|---|---|
| **Window planner** | Shows which hours the window can be open (blue strip) and which hours it should stay shut. If the whole day is bad, it finds the single least-bad hour for a 10-minute air change. Indoor air gets stale too, so "keep it shut all day" is not enough advice. |
| **Breathing-aware activity picker** | You breathe about 2.5x more air walking and 5x more running than at rest. Run limits are therefore stricter than walk limits, and it picks the best non-overlapping 1-3 hour slots, never at night. |
| **Personal thresholds** | Same AQI, different risk: the bar height is scaled for child / elderly / pregnant / asthma. |
| **Ground-truth correction** | Models drift. A scheduled job uses **TinyFish** to read the live number from a real monitoring-station page, and the plan is nudged toward it (fading over 6 hours, and never trusting a "cleaner" reading by more than half). |
| **Own language** | Reliable tips in English, Hindi, Telugu; Amazon Bedrock writes a short briefing in 11 Indian languages. |
| **Alerts** | Email when the next 6 hours cross a risk threshold, via SNS filter policies per city and audience. |

Useful for: parents, older people, people with asthma, joggers, delivery riders and office commuters, anyone choosing whether to open a window.

## Architecture

```
Browser ──► API Gateway (HTTP API, throttled)
              └─► Lambda "ApiFunction" ──► Open-Meteo (forecast, geocoding)
                     │   │                 DynamoDB (cache, watch-list, TTL)
                     │   └──────────────► Bedrock (briefing in your language)
                     └──────────────────► SNS (subscribe by email)

EventBridge schedule (every 3 h)
   └─► Lambda "RefreshFunction" ──► TinyFish Web Agent (live station AQI)
              │                     SSM Parameter Store (TinyFish key, encrypted)
              ├──► DynamoDB (store station reading)
              └──► SNS topic ──► subscribers' email (filtered by city + audience)
```

The API never waits for TinyFish. A browser request only reads cached values, so pages stay fast; the slow web-agent work happens in the background.

### AWS services used

Lambda, API Gateway (HTTP API), DynamoDB (+TTL), EventBridge schedule, SNS, Bedrock, Systems Manager Parameter Store, CloudWatch Logs, deployed with AWS SAM (infrastructure as code).

## Run locally (no AWS needed)

```bash
pip install -r requirements-dev.txt
python -m pytest            # 24 tests
python local_server.py      # http://localhost:8000
```

Locally the store is in memory, Bedrock and alerts are off. Set `TINYFISH_API_KEY` to try the station check.

## Deploy to AWS

1. Install the AWS CLI and AWS SAM CLI, then run `aws configure`.
2. In the Bedrock console, enable a model in your region and put its ID (or inference-profile ID) into `BedrockModelId` in `template.yaml`. Or set `UseBedrock` to `false`; everything else still works.
3. Get a TinyFish API key from agent.tinyfish.ai.
4. Run `./deploy.sh`. It stores the key in SSM, runs the tests, builds and deploys.
5. Open the `AppUrl` printed at the end.

Seed the city list for the TinyFish job by subscribing to alerts for a city from the page (only watched cities are checked, capped at 10 to control cost).

## Project layout

```
template.yaml            AWS SAM stack (all AWS resources)
src/api_handler.py       HTTP API Lambda (page, /api/plan, /api/subscribe)
src/refresh_handler.py   Scheduled Lambda (TinyFish + alerts)
src/airwindow/planner.py Pure logic: windows, activity slots, mask, trend, correction
src/airwindow/...        sources, tinyfish, groundtruth, advice, i18n, notify, store
src/web/index.html       The UI
tests/                   pytest (planner + API)
docs/PITCH.md            Idea-submission content
```

## Honest limits

- Forecast is a regional model (Open-Meteo / CAMS), not your street. The TinyFish station check reduces this gap but a station can still be kilometres away.
- Station pages use the US AQI scale; India's official CPCB AQI is on a different scale, so numbers can differ.
- The TinyFish goal asks for a headline AQI from a public page. If a page layout changes or the city slug does not exist, the check is skipped and the model is used alone.
- One email can hold one alert subscription per topic (SNS ignores re-subscribing with a new filter).
- General guidance, not medical advice.
- I could not call the live Open-Meteo, TinyFish or AWS services from my build environment, so the logic is unit-tested with fake data, but you should do a first live test after deploying.
