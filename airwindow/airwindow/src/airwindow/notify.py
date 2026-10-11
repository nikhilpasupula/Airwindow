"""Amazon SNS: email alert subscriptions with per-city / per-audience filter policies."""
import json
import os
import re

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")


def _sns():
    import boto3

    return boto3.client("sns")


def enabled():
    return bool(os.environ.get("TOPIC_ARN"))


def subscribe(email, city_key, sensitive):
    audience = ["sensitive", "all"] if sensitive else ["all"]
    _sns().subscribe(
        TopicArn=os.environ["TOPIC_ARN"],
        Protocol="email",
        Endpoint=email,
        Attributes={"FilterPolicy": json.dumps({"city": [city_key], "audience": audience})},
        ReturnSubscriptionArn=True,
    )


def publish(city_key, city_name, audience, text):
    _sns().publish(
        TopicArn=os.environ["TOPIC_ARN"],
        Subject=f"AirWindow: poor air expected in {city_name}"[:99],
        Message=text,
        MessageAttributes={
            "city": {"DataType": "String", "StringValue": city_key},
            "audience": {"DataType": "String", "StringValue": audience},
        },
    )
