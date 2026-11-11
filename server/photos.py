"""Optional photo storage (setting STORE_PHOTOS). Switch it off and nothing is kept.

On Vercel: a Blob store connected to the project (Storage -> Blob, private access).
Auth, as in the official @vercel/blob client:
  * BLOB_READ_WRITE_TOKEN (store id is part of the token), or
  * OIDC: the per-request token (header x-vercel-oidc-token / env VERCEL_OIDC_TOKEN)
    together with BLOB_STORE_ID.
Storing is best effort: recognition never fails because of it; the error is logged.
"""
from __future__ import annotations

import datetime as dt
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://vercel.com/api/blob/"
API_VERSION = "13"


def _auth(request_headers) -> tuple[str, str] | None:
    rw = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if rw:
        parts = rw.split("_")
        return rw, (parts[3] if len(parts) > 3 else "")
    oidc = (request_headers.get("x-vercel-oidc-token") if request_headers else None) \
        or os.environ.get("VERCEL_OIDC_TOKEN")
    store = os.environ.get("BLOB_STORE_ID", "")
    if oidc and store:
        return oidc, store.removeprefix("store_")
    return None


def store_photo(data: bytes, media_type: str, game_id: str, index: int,
                request_headers=None, access: str | None = None) -> tuple[str | None, str | None]:
    """Returns (pathname or url, error)."""
    auth = _auth(request_headers)
    if not auth:
        return None, "no blob credentials (BLOB_READ_WRITE_TOKEN or BLOB_STORE_ID+OIDC)"
    token, store_id = auth
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(media_type, "bin")
    pathname = f"sheets/{dt.date.today():%Y/%m}/{game_id}-{index}.{ext}"
    req = urllib.request.Request(
        API_URL + "?" + urllib.parse.urlencode({"pathname": pathname}), data=data, method="PUT",
        headers={"authorization": f"Bearer {token}", "x-api-version": API_VERSION,
                 "x-vercel-blob-store-id": store_id,
                 "x-vercel-blob-access": access or os.environ.get("BLOB_ACCESS", "private"),
                 "x-content-type": media_type, "x-add-random-suffix": "1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            import json
            body = json.loads(r.read() or b"{}")
            return body.get("pathname") or body.get("url") or pathname, None
    except urllib.error.HTTPError as e:
        return None, f"blob HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"
    except Exception as e:  # network etc.
        return None, f"blob error: {type(e).__name__}"


def new_game_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
