"""
r2.py — Cloudflare R2 client setup + helper functions

USE_R2=true hone pe hi active hota hai.
Agar USE_R2=false hai toh _r2_client = None, baaki functions call mat karna.
"""

import os

# ── R2 toggle ──
USE_R2  = os.environ.get("USE_R2", "false").lower() == "true"
IS_PROD = os.environ.get("RENDER", False)

if USE_R2:
    import boto3
    from botocore.config import Config as BotocoreConfig

    _r2_client = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        config=BotocoreConfig(signature_version="s3v4"),
        region_name="auto",
    )
    R2_BUCKET     = os.environ["R2_BUCKET"]
    R2_PUBLIC_URL = os.environ["R2_PUBLIC_URL"].rstrip("/")
else:
    _r2_client    = None
    R2_BUCKET     = None
    R2_PUBLIC_URL = None


def _content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
        ".glb":  "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".mind": "application/octet-stream",
    }.get(ext, "application/octet-stream")


def r2_upload(contents: bytes, key: str, filename: str):
    """R2 pe file upload karo"""
    _r2_client.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=contents,
        ContentType=_content_type(filename),
    )


def r2_delete(key: str):
    """R2 se file delete karo — silently fails if not found"""
    try:
        _r2_client.delete_object(Bucket=R2_BUCKET, Key=key)
    except Exception:
        pass


def r2_copy(src_key: str, dst_key: str) -> bool:
    """R2 mein file copy karo (trash ke liye) — False on failure"""
    try:
        _r2_client.copy_object(
            Bucket=R2_BUCKET,
            CopySource={"Bucket": R2_BUCKET, "Key": src_key},
            Key=dst_key,
        )
        return True
    except Exception:
        return False


def r2_presign(key: str, expires: int = 600) -> str:
    """GLB ke liye presigned GET URL — default 10 min expiry"""
    return _r2_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET, "Key": key},
        ExpiresIn=expires,
    )


def r2_public_url(key: str) -> str:
    """Images / mind files ke liye public URL"""
    return f"{R2_PUBLIC_URL}/{key}"
