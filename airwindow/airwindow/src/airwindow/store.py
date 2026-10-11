"""Tiny key-value store on DynamoDB (single table, TTL). Falls back to memory for local runs."""
import json
import os
import time

_mem = {}
_table = None


def _tbl():
    global _table
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def _local():
    return not os.environ.get("TABLE_NAME")


def get(pk):
    if _local():
        item = _mem.get(pk)
    else:
        item = _tbl().get_item(Key={"pk": pk}).get("Item")
    if not item:
        return None
    if item.get("ttl") and int(item["ttl"]) < time.time():
        return None
    return json.loads(item["data"])


def put(pk, data, ttl_s=None):
    item = {"pk": pk, "data": json.dumps(data)}
    if ttl_s:
        item["ttl"] = int(time.time()) + int(ttl_s)
    if _local():
        _mem[pk] = item
    else:
        _tbl().put_item(Item=item)


def scan_prefix(prefix):
    """Return all live items whose key starts with prefix (fine for the small watch-list)."""
    if _local():
        return [json.loads(v["data"]) for k, v in _mem.items() if k.startswith(prefix)]
    from boto3.dynamodb.conditions import Attr

    out, kwargs = [], {"FilterExpression": Attr("pk").begins_with(prefix)}
    while True:
        resp = _tbl().scan(**kwargs)
        out += [json.loads(i["data"]) for i in resp.get("Items", []) if not i.get("ttl") or int(i["ttl"]) >= time.time()]
        if "LastEvaluatedKey" not in resp:
            return out
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
