import boto3
from app.config import settings

def session() -> boto3.session.Session:
    return boto3.session.Session(profile_name=settings.aws_profile or None, region_name=settings.aws_region)
