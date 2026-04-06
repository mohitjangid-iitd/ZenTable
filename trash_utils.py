"""
trash_utils.py — Trash file management helpers

move_to_trash, restore_from_trash, delete_from_trash, purge_expired_trash
R2 aur local dono modes support karta hai.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone

from r2 import USE_R2, _r2_client, R2_BUCKET, r2_copy, r2_delete, r2_presign
from database import trash_add, trash_get_one, trash_remove, trash_remove_expired

IST               = timezone(timedelta(hours=5, minutes=30))
TRASH_DIR         = "private/trash"
TRASH_EXPIRY_DAYS = 30


def move_to_trash(client_id: str, save_path: str, file_type: str):
    """
    Existing file ko trash mein move karo before overwrite.

    save_path  — local path (e.g. static/assets/clint_one/logo.png)
                 ya R2 key  (e.g. clint_one/logo.png) — USE_R2 ke hisaab se
    file_type  — "image" | "model" | "mind"
    Meta PostgreSQL mein jaata hai (Render-safe).
    """
    now        = datetime.now(IST)
    ts         = int(now.timestamp())
    orig_name  = os.path.basename(save_path)
    trash_name = f"{ts}_{client_id}_{orig_name}"
    deleted_at     = now.strftime("%Y-%m-%d %H:%M:%S")
    auto_delete_at = (now + timedelta(days=TRASH_EXPIRY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    if USE_R2:
        # R2 key derive karo save_path se
        src_key = save_path
        for prefix in ("static/assets/", "private/assets/"):
            if save_path.startswith(prefix):
                src_key = save_path[len(prefix):]
                break

        trash_key = f"trash/{client_id}/{trash_name}"
        copied    = r2_copy(src_key, trash_key)
        if not copied:
            return  # file R2 pe thi hi nahi — silently skip

        r2_delete(src_key)

        # Size fetch karo (head_object — cheap request)
        size_kb = 0
        try:
            head    = _r2_client.head_object(Bucket=R2_BUCKET, Key=trash_key)
            size_kb = round(head["ContentLength"] / 1024, 1)
        except Exception:
            pass

    else:
        if not os.path.exists(save_path):
            return

        trash_client_dir = os.path.join(TRASH_DIR, client_id)
        os.makedirs(trash_client_dir, exist_ok=True)
        dest    = os.path.join(trash_client_dir, trash_name)
        shutil.copy2(save_path, dest)          # pehle copy karo
        size_kb = round(os.path.getsize(dest) / 1024, 1)
        try:
            os.remove(save_path)               # phir original hatao
        except PermissionError:
            pass                               # Windows lock — copy trash mein hai, chalta hai

    trash_add({
        "client_id":      client_id,
        "original_name":  orig_name,
        "original_path":  save_path,
        "trash_name":     trash_name,
        "file_type":      file_type,
        "size_kb":        size_kb,
        "deleted_at":     deleted_at,
        "auto_delete_at": auto_delete_at,
        "storage":        "r2" if USE_R2 else "local",
    })


def restore_from_trash(trash_name: str) -> bool:
    """
    Trash file ko uski original location pe wapas rakho.
    Return True on success, False if not found.
    """
    entry = trash_get_one(trash_name)
    if not entry:
        return False

    original_path = entry["original_path"]

    if entry.get("storage") == "r2" or USE_R2:
        trash_key = f"trash/{entry['client_id']}/{trash_name}"

        orig_key = original_path
        for prefix in ("static/assets/", "private/assets/"):
            if original_path.startswith(prefix):
                orig_key = original_path[len(prefix):]
                break

        copied = r2_copy(trash_key, orig_key)
        if not copied:
            return False
        r2_delete(trash_key)

    else:
        trash_path = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
        if not os.path.exists(trash_path):
            return False
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.move(trash_path, original_path)

    trash_remove(trash_name)
    return True


def delete_from_trash(trash_name: str) -> bool:
    """Trash se permanently delete karo (file + DB entry)."""
    entry = trash_get_one(trash_name)
    if not entry:
        return False

    try:
        if entry.get("storage") == "r2" or USE_R2:
            r2_delete(f"trash/{entry['client_id']}/{trash_name}")
        else:
            trash_path = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
            if os.path.exists(trash_path):
                os.remove(trash_path)
    except Exception:
        pass

    trash_remove(trash_name)
    return True


def purge_expired_trash():
    """
    30 din se purani trash files delete karo.
    Lifespan mein call hota hai server start pe.
    """
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    expired = trash_remove_expired(now_str)
    deleted = 0

    for entry in expired:
        try:
            if entry.get("storage") == "r2" or USE_R2:
                r2_delete(f"trash/{entry['client_id']}/{entry['trash_name']}")
            else:
                trash_path = os.path.join(TRASH_DIR, entry["client_id"], entry["trash_name"])
                if os.path.exists(trash_path):
                    os.remove(trash_path)
            deleted += 1
        except Exception:
            pass

    if deleted:
        print(f"🗑️  Trash purge: {deleted} expired file(s) deleted")
