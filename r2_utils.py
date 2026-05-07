"""
r2_utils.py — Cloudflare R2 helpers (boto3 S3-compatible)

Required env vars:
  R2_ACCESS_KEY_ID
  R2_SECRET_ACCESS_KEY
  R2_ACCOUNT_ID
  R2_BUCKET_NAME
"""

import os
import boto3
from botocore.config import Config

R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID", "")
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME", "inventoryestimates")

ENABLED = bool(R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_ACCOUNT_ID)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_file(file_obj, key: str, content_type: str) -> None:
    """Upload file_obj to R2 at the given key."""
    _client().upload_fileobj(
        file_obj, R2_BUCKET_NAME, key,
        ExtraArgs={"ContentType": content_type},
    )


def delete_file(key: str) -> None:
    """Delete an object from R2 by key. Silently ignores missing keys."""
    try:
        _client().delete_object(Bucket=R2_BUCKET_NAME, Key=key)
    except Exception:
        pass


def presigned_url(key: str, expires: int = 3600) -> str:
    """Return a presigned GET URL valid for `expires` seconds."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )
