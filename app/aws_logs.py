import boto3
from botocore.config import Config
from app.config import settings
from app.redaction import redact

def _client():
    session = boto3.session.Session(profile_name=settings.aws_profile or None, region_name=settings.aws_region)
    kwargs = {"config": Config(retries={"max_attempts": 3, "mode": "standard"})}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return session.client("logs", **kwargs)

def list_log_groups(limit=50):
    client = _client()
    paginator = client.get_paginator("describe_log_groups")
    groups = []
    for page in paginator.paginate(PaginationConfig={"MaxItems": limit, "PageSize": min(limit, 50)}):
        groups.extend(x["logGroupName"] for x in page.get("logGroups", []))
    return groups

def fetch_logs(log_group: str, hours: int = 1, limit: int = 1000) -> str:
    from datetime import datetime, timedelta, timezone
    if not log_group.startswith("/"):
        raise ValueError("Log group must be a full CloudWatch log group name.")
    if not 1 <= hours <= 168:
        raise ValueError("hours must be between 1 and 168.")
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000.")
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    client = _client()
    response = client.filter_log_events(
        logGroupName=log_group,
        startTime=int(start.timestamp() * 1000),
        endTime=int(end.timestamp() * 1000),
        limit=limit,
    )
    events = sorted(response.get("events", []), key=lambda x: x.get("timestamp", 0))
    return "\n".join(redact(e.get("message", "")) for e in events)
