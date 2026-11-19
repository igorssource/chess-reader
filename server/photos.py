"""Optional photo storage (setting STORE_PHOTOS). Switch it off and nothing is kept.

On Vercel: a Blob store connected to the project (Storage -> Blob, private access).
Auth, as in the official @vercel/blob client:
  * BLOB_READ_WRITE_TOKEN (store id is part of the token), or
  * OIDC: the per-request token (header x-vercel-oidc-token / env VERCEL_OIDC_TOKEN)
    together with BLOB_STORE_ID.
Storing is best effort: recognition never fails because of it; the error is logged.
Photos older than KEEP_DAYS are deleted once a day (Vercel cron -> /api/cleanup).
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


KEEP_DAYS = 90      # photos are deleted automatically after this many days (the page says so)


def _blob_request(token: str, store_id: str, path: str, data: bytes | None = None, method: str = "GET"):
    import json
    headers = {"authorization": f"Bearer {token}", "x-api-version": API_VERSION,
               "x-vercel-blob-store-id": store_id}
    if data is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(API_URL.rstrip("/") + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"{}")


def _uploaded(blob: dict) -> dt.datetime | None:
    try:
        t = dt.datetime.fromisoformat(str(blob.get("uploadedAt", "")).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def delete_old_photos(request_headers=None, keep_days: int = KEEP_DAYS, now: dt.datetime | None = None,
                      max_pages: int = 20) -> dict:
    """Deletes stored photos older than keep_days. Returns counts (or an error)."""
    import json
    auth = _auth(request_headers)
    if not auth:
        return {"error": "no blob credentials"}
    token, store_id = auth
    limit = (now or dt.datetime.now(dt.timezone.utc)) - dt.timedelta(days=keep_days)
    checked, old, cursor = 0, [], None
    try:
        for _ in range(max_pages):
            q = {"prefix": "sheets/", "limit": "1000", **({"cursor": cursor} if cursor else {})}
            page = _blob_request(token, store_id, "/?" + urllib.parse.urlencode(q))
            for b in page.get("blobs") or []:
                checked += 1
                t = _uploaded(b)
                if t and t < limit and b.get("url"):
                    old.append(b["url"])
            cursor = page.get("cursor")
            if not page.get("hasMore") or not cursor:
                break
        for i in range(0, len(old), 100):
            _blob_request(token, store_id, "/delete", json.dumps({"urls": old[i:i + 100]}).encode(), "POST")
    except urllib.error.HTTPError as e:
        return {"error": f"blob HTTP {e.code}", "checked": checked}
    except Exception as e:  # network etc.
        return {"error": f"blob error: {type(e).__name__}", "checked": checked}
    return {"checked": checked, "deleted": len(old), "older_than": limit.date().isoformat()}


def new_game_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
