# AirWindow - idea submission content (Track: Air)

## Problem statement
Millions of people in Indian cities see an AQI number every day but do not know what to *do* with it: Should I open the window? Is a morning walk safe for my child or my father with asthma? Apps give a number; people need a decision.

## Proposed solution
AirWindow converts the air-quality forecast into an hour-by-hour action plan for a chosen person: when windows can be open, the best 1-3 hour slot for a walk, run or commute, whether to wear an N95, and whether air is getting better or worse. Tips arrive in the user's language, and email alerts fire only when conditions turn bad.

## Target users
Parents, older adults, pregnant women, people with asthma, joggers, outdoor workers, delivery riders, commuters, schools and residents' associations in Indian cities.

## Technical architecture and stack
Python 3.12, vanilla JS front end. AWS: API Gateway HTTP API, Lambda, DynamoDB with TTL, EventBridge Scheduler, SNS, Bedrock, SSM Parameter Store, CloudWatch; AWS SAM for infrastructure as code. Data: Open-Meteo air-quality forecast + TinyFish web agent for live station readings.

## How do you plan to integrate the TinyFish API?
Air forecasts are models; real stations are the truth, but stations publish on web pages with no free API. A scheduled Lambda calls the TinyFish Web Agent (`POST /v1/automation/run`) with the station page URL and a plain-English goal ("return the current AQI and main pollutant as JSON"). The structured result is cached in DynamoDB. The planner uses it as a nowcast correction that fades over 6 hours and never lowers the risk by more than half the gap. Disagreement between model and station is shown to the user. Because TinyFish reads pages by goal and not by CSS selectors, adding a new city or data source needs no new scraper code.

## Scalability, feasibility and use case
- Serverless and pay-per-request, so cost is close to zero when idle and scales automatically.
- Forecasts are cached per 0.01-degree grid cell for one hour, so cost grows with number of cities, not number of users.
- TinyFish runs only for watched cities (capped), in the background.
- Feasible today: all data sources are available now; core planner is pure logic with automated tests.
- Next steps: school / RWA dashboards, WhatsApp alerts, indoor-sensor input, CPCB-scale conversion.
