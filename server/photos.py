"""Optional photo storage (setting STORE_PHOTOS). Switch it off and nothing is kept.

On Vercel: Vercel Blob (Storage -> Blob), which sets BLOB_READ_WRITE_TOKEN.
Without a token photos are not stored (local development).
"""
from __future__ import annotations

import datetime as dt
import os
import secrets
import urllib.request


def store_photo(data: bytes, media_type: str, game_id: str, index: int) -> str | None:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        return None
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(media_type, "bin")
    path = f"sheets/{dt.date.today():%Y/%m}/{game_id}-{index}.{ext}"
    req = urllib.request.Request(
        f"https://blob.vercel-storage.com/{path}", data=data, method="PUT",
        headers={"authorization": f"Bearer {token}", "x-api-version": "7",
                 "x-content-type": media_type, "x-add-random-suffix": "1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode()[:500]
    except Exception:
        return None          # storing is best effort: never fail the recognition because of it


def new_game_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
