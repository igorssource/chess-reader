"""HTTP API used by the web page.

POST /api/process   photo(s) of one game -> moves with marks + PGN
POST /api/pgn       header + moves -> PGN (after the user edits; no model call)
POST /api/redecode  a person fixed one move -> rest of the game decoded again (no model call)
GET  /api/result/<job>  the answer of /api/process again (phone slept or lost the connection)
GET  /api/cleanup   deletes photos older than 90 days (daily Vercel cron)
GET  /api/health    settings visible to the page (no secrets)
GET  /api/stats     usage statistics (needs ADMIN_TOKEN)
"""
from __future__ import annotations

import hmac
import json
import os
import time
from dataclasses import replace

import chess
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chessreader.combine import detect_language
from chessreader.config import MODEL_PRICES_USD, Settings
from chessreader.decoder import DecodedPly, DecodeResult
from chessreader.model import get_provider
from chessreader.model.anthropic_provider import ModelError
from chessreader.imaging import prepare
from chessreader.model.base import Image
from chessreader.notation import LANGUAGES
from chessreader.openings import detect as detect_opening
from chessreader.pgn_export import build_pgn
from chessreader.pipeline import BudgetExhausted, process_cascade, process_game
from chessreader.review import (ReviewError, cell_from_dict, cells_from_plies, cells_to_dicts, move_from_text,
                                redecode)
from chessreader.sheet import Header

from .kv import get_kv
from .limits import Budget, DayStats, IpAttempts, IpLimit, client_ip, day_history, ip_tag, log_game, stats
from . import results
from .photos import delete_old_photos, new_game_id, store_photo
from .references import REFERENCES, compare

MAX_IMAGES = 2              # the sheet + a continuation page or the opponent's sheet
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PLIES = 1000            # no real game is longer; keeps the model-free routes cheap
MAX_CELLS = 2500


def _is_admin(value: str | None) -> bool:
    """True only for the exact ADMIN_TOKEN (compared in constant time)."""
    admin = os.environ.get("ADMIN_TOKEN") or ""
    return bool(admin) and bool(value) and hmac.compare_digest(value.encode(), admin.encode())


def _image_type(data: bytes) -> str | None:
    """The real type from the first bytes of the file (the browser's claim is not trusted)."""
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None

app = FastAPI(title="Chess Reader API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods=["GET", "POST"], allow_headers=["*"],
)


@app.middleware("http")
async def restore_original_path(request: Request, call_next):
    """On Vercel every /api/* request is rewritten to /api/index (see vercel.json),
    which passes the original path as ?__path=. Put it back so the routes match."""
    orig = request.query_params.get("__path")
    if orig is not None and not request.url.path.startswith("/api/") or (
            orig is not None and request.url.path in ("/api/index", "/api/index.py", "/api")):
        path = "/api/" + orig.lstrip("/")
        request.scope["path"] = path
        request.scope["raw_path"] = path.encode()
    return await call_next(request)


def _err(status: int, code: str, message: str):
    return JSONResponse({"error": code, "message": message}, status_code=status)


@app.get("/api/health")
def health():
    s = Settings()
    b = Budget(get_kv(), s)
    return {"ok": True, "notation": s.notation_language, "model": s.model_name,
            "cascade": s.cascade_models,
            "max_calls_per_game": s.max_calls_per_game, "budget_left_today": b.remaining() > 0,
            "stores_photos": s.store_photos}


@app.post("/api/process")
async def process(request: Request, files: list[UploadFile] = File(...), language: str = Form(None),
                  admin: str = Form(None), model: str = Form(None), ref: str = Form(None),
                  job: str = Form(None)):
    # With a job id the answer is also kept for a day (GET /api/result/<job>): a phone that
    # fell asleep or lost the connection meanwhile still gets the game it already paid for.
    job = results.valid_job(job)
    if not job:
        return await _process(request, files, language, admin, model, ref)
    kv = get_kv()
    results.mark_running(kv, job)
    try:
        out = await _process(request, files, language, admin, model, ref)
    except Exception:
        results.save(kv, job, 500, {"error": "server_error", "message": "internal error"})
        raise
    if isinstance(out, JSONResponse):
        results.save(kv, job, out.status_code, json.loads(out.body))
    else:
        results.save(kv, job, 200, out)
    return out


@app.get("/api/result/{job}")
def get_result(job: str):
    if not results.valid_job(job):
        return _err(400, "bad_request", "bad job id")
    r = results.load(get_kv(), job)
    if r is None:
        return _err(404, "unknown_job", "no such reading (never arrived or older than a day)")
    return r


@app.get("/api/cleanup")
def cleanup(request: Request):
    """Deletes photos older than 90 days. Called once a day by the Vercel cron (vercel.json).
    Harmless to call by hand: it runs at most every 6 hours unless the admin asks."""
    secret = os.environ.get("CRON_SECRET")
    auth = request.headers.get("authorization") or ""
    by_cron = bool(secret) and hmac.compare_digest(auth.encode(), f"Bearer {secret}".encode())
    if not (by_cron or _is_admin(request.headers.get("x-admin-token"))):
        if secret:
            return _err(403, "forbidden", "cron secret required")
        if not get_kv().set_once("cleanup:recent", 6 * 3600):
            return {"skipped": "ran less than 6 hours ago"}
    return delete_old_photos(request.headers)


async def _process(request: Request, files, language, admin, model, ref):
    s = Settings()
    if language in LANGUAGES:      # anything else: the default stays
        s.notation_language = language
    # Admin test mode (hidden in the page): choose the model per upload and compare
    # the result with a reference game. Needs ADMIN_TOKEN, so normal users can't use it.
    is_admin = _is_admin(admin)
    if (model or ref) and not is_admin:
        return _err(403, "forbidden", "admin token required")
    if model:
        if model not in MODEL_PRICES_USD:
            return _err(400, "bad_request", f"unknown model {model}")
        s.model_name = model
    if ref and ref not in REFERENCES:
        return _err(400, "bad_request", f"unknown reference {ref}")
    if not 1 <= len(files) <= MAX_IMAGES:
        return _err(400, "bad_request", f"send 1 to {MAX_IMAGES} photos")
    images = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_IMAGE_BYTES:
            return _err(413, "too_large", "photo is too large")
        mt = _image_type(data)
        if mt is None:             # not a photo: never stored, never sent to the model
            return _err(400, "not_image", "this file is not a photo (JPEG, PNG or WebP)")
        images.append(prepare(Image(data, mt)))   # smaller copy for reading, full size kept for zoomed crops

    kv = get_kv()
    budget = Budget(kv, s)
    # games per IP address per day (admin test mode is not counted)
    ip = client_ip(request.headers, request.client and request.client.host)
    ip_limit = None if is_admin else IpLimit(kv, ip)
    attempts = None if is_admin else IpAttempts(kv, ip)
    day = DayStats(kv, is_admin, ip)        # history per day for the admin's statistics

    def on_call(call):
        budget.add(call)
        day.cost(call)

    def ip_refused():
        day.event("ip_limit_hits")
        return JSONResponse({"error": "ip_limit", "message": "daily limit per user reached",
                             "limit": ip_limit.limit}, status_code=429)

    if ip_limit and not ip_limit.ok():
        return ip_refused()
    if not budget.ok():             # checked before anything is stored or sent to the model
        day.event("budget_hits")
        return _err(429, "daily_limit", "daily limit reached")
    # The place is taken BEFORE the reading starts, so many uploads sent at the same moment
    # cannot all slip under the limit; it is given back if the game could not be read.
    # Uploads that fail are counted too (separately), so they cannot be repeated without end.
    if attempts and not attempts.take():
        return ip_refused()
    if ip_limit and not ip_limit.take():
        return ip_refused()
    game_id = new_game_id()
    photo_refs, photo_errors = [], []
    if s.store_photos:
        for i, img in enumerate(images):
            pref, err = store_photo(img.hires or img.data, img.media_type, game_id, i, request.headers)
            photo_refs.append(pref)
            if err:
                photo_errors.append(err)

    t0 = time.time()
    try:
        if not model and len(s.cascade_models) > 1:
            # cheap model first, strong model only if the result looks unsure
            outcome = process_cascade(images, lambda m: get_provider(replace(s, model_name=m)), s,
                                      budget_ok=budget.ok, on_call=on_call)
        else:
            outcome = process_game(images, get_provider(s), s, budget_ok=budget.ok, on_call=on_call)
    except BudgetExhausted:
        if ip_limit:
            ip_limit.give_back()
        day.event("budget_hits")
        return _err(429, "daily_limit", "daily limit reached")
    except ModelError as e:
        if ip_limit:
            ip_limit.give_back()
        day.event("errors")
        return _err(502, "model_error", str(e))
    except Exception:
        if ip_limit:
            ip_limit.give_back()   # only a game that was actually read counts
        raise

    day.game()
    r = outcome.result
    accuracy = compare(ref, [p.san for p in r.plies]) if ref else None
    cost_by_model: dict = {}
    for c in outcome.calls:
        cost_by_model[c.model] = round(cost_by_model.get(c.model, 0.0) + c.cost_eur, 5)
    models_used = list(cost_by_model)
    route = "+".join(models_used) or s.model_name
    log_game(kv, {
        "id": game_id, "ts": int(t0), "seconds": round(time.time() - t0, 1),
        "model": route, "calls": len(outcome.calls), "escalated": outcome.escalated,
        "cost_by_model": cost_by_model,
        "cost_eur": round(outcome.cost_eur, 5), "stopped": outcome.stopped_because,
        "plies": len(r.plies), "doubtful": sum(p.status == "doubtful" for p in r.plies),
        "fixed": sum(p.status == "fixed" for p in r.plies), "photos": [p for p in photo_refs if p],
        **({"photo_error": photo_errors[0]} if photo_errors else {}),
        **(accuracy or {}), **({"admin": True} if is_admin else {"ip": ip_tag(ip)}),
    })
    return {
        "game_id": game_id,
        "header": outcome.reading.header.__dict__,
        "plies": [p.__dict__ for p in r.plies],
        "skipped_cells": [outcome_cell(outcome, i) for i in r.skipped_tokens],
        "pgn": outcome.pgn,
        "opening": _opening([p.san for p in r.plies]),
        # kept by the page with the game, so a fixed move can be decoded again without the model
        "cells": cells_to_dicts(outcome.tokens),
        "layout": outcome.reading.sheets[0].layout if outcome.reading.sheets else [],
        # which photo is what (shown on the page with two photos)
        "sheets": [{"image": sh.image, "role": sh.role, "cells": len(sh.plies),
                    "language": detect_language(sh, sh.language if sh.language in ("de", "en") else s.notation_language)}
                   for sh in outcome.reading.sheets],
        "model_calls": len(outcome.calls),
        "stopped_because": outcome.stopped_because,
        "language": s.notation_language,
        **({"admin": {"model": route, "cost_eur": round(outcome.cost_eur, 4),
                      "models_used": models_used, "escalated": outcome.escalated,
                      "accuracy": accuracy}} if is_admin else {}),
    }


def outcome_cell(outcome, i):
    toks = outcome.tokens
    t = toks[i] if i < len(toks) else None
    return {"index": i, "text": t.text if t else "", "number": t.number if t else None,
            "color": t.color if t else None}


class PgnRequest(BaseModel):
    header: dict
    moves: list[dict]          # [{san, status, reason, written, local, alternatives}]


@app.post("/api/pgn")
def pgn(req: PgnRequest):
    s = Settings()
    if len(req.moves) > MAX_PLIES:
        raise HTTPException(400, "too many moves")
    board = chess.Board()
    plies = []
    for k, m in enumerate(req.moves):
        try:
            mv = board.parse_san(m["san"])
        except (ValueError, KeyError):
            raise HTTPException(400, f"illegal move at ply {k + 1}")
        plies.append(DecodedPly(ply=k, san=board.san(mv), written=m.get("written", ""),
                                local=m.get("local", ""), status=m.get("status", "ok"),
                                reason=m.get("reason", "exact"),
                                alternatives=m.get("alternatives", [])))
        board.push(mv)
    header = Header(**{k: v for k, v in req.header.items() if k in Header.__dataclass_fields__})
    return {"pgn": build_pgn(header, DecodeResult(plies, [], 0, board.fen()), s.pgn_comments_language),
            "opening": _opening([p.san for p in plies])}


class RedecodeRequest(BaseModel):
    header: dict
    plies: list[dict]          # current moves as the page has them
    cells: list[dict] | None = None   # cells read from the photo (None for older saved games)
    ply: int                   # half-move index the person fixed (0 = White's 1st move)
    san: str | None = None     # the chosen move (English SAN) ...
    text: str | None = None    # ... or as typed/shown in the sheet's notation ("Thd1")
    language: str = "de"


@app.post("/api/redecode")
def redecode_route(req: RedecodeRequest):
    s = Settings()
    if len(req.plies) > MAX_PLIES or len(req.cells or []) > MAX_CELLS:
        raise HTTPException(400, "too many moves")
    if req.cells is None:
        cells, plies = cells_from_plies(req.plies)
    else:
        cells, plies = [cell_from_dict(c) for c in req.cells], req.plies
    lang = req.language or s.notation_language
    try:
        san = req.san or move_from_text(plies, req.ply, req.text or "", lang)
        new_plies, new_cells, skipped = redecode(cells, plies, req.ply, san, lang)
    except ReviewError as e:
        return JSONResponse({"error": "no_match", "message": str(e), "options": getattr(e, "options", [])},
                            status_code=400)
    board = chess.Board()
    decoded = []
    for k, m in enumerate(new_plies):
        mv = board.parse_san(m["san"])
        decoded.append(DecodedPly(ply=k, san=m["san"], written=m.get("written", ""), local=m.get("local", ""),
                                  status=m.get("status", "ok"), reason=m.get("reason", "exact"),
                                  alternatives=m.get("alternatives", [])))
        board.push(mv)
    header = Header(**{k: v for k, v in req.header.items() if k in Header.__dataclass_fields__})
    return {"plies": new_plies, "cells": cells_to_dicts(new_cells),
            "skipped_cells": [{"index": i, "text": new_cells[i].text, "number": new_cells[i].number,
                               "color": new_cells[i].color} for i in skipped],
            "pgn": build_pgn(header, DecodeResult(decoded, skipped, 0, board.fen()), s.pgn_comments_language),
            "opening": _opening([m["san"] for m in new_plies])}


def _opening(sans):
    o = detect_opening(sans)
    return o.to_dict() if o else None


@app.get("/api/stats")
def get_stats(request: Request, token: str = ""):
    # the page sends the token in a header (kept out of addresses and logs); ?token= still works
    if not _is_admin(request.headers.get("x-admin-token") or token):
        return _err(403, "forbidden", "admin token required")
    kv = get_kv()
    s = Settings()
    out = stats(kv, today_prefix=_today_start())
    b = Budget(kv, s)
    out["spent_today_eur"] = round(b.spent(), 4)
    out["daily_budget_eur"] = b.limit
    out["max_calls_per_game"] = s.max_calls_per_game
    out["games_per_ip_today"] = IpLimit(kv, "-").limit
    out["days"] = day_history(kv)
    return out


def _today_start() -> int:
    import datetime as dt
    from .limits import TZ
    now = dt.datetime.now(TZ)
    return int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


@app.api_route("/{rest:path}", methods=["GET", "POST"], include_in_schema=False)
def not_found(rest: str, request: Request):
    # Shows which path the server actually received (helps to debug routing on the host).
    return _err(404, "not_found", f"no route for /{rest}")
