"""HTTP API used by the web page.

POST /api/process   photo(s) of one game -> moves with marks + PGN
POST /api/pgn       header + moves -> PGN (after the user edits; no model call)
POST /api/redecode  a person fixed one move -> rest of the game decoded again (no model call)
GET  /api/health    settings visible to the page (no secrets)
GET  /api/stats     usage statistics (needs ADMIN_TOKEN)
"""
from __future__ import annotations

import os
import time
from dataclasses import replace

import chess
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chessreader.config import MODEL_PRICES_USD, Settings
from chessreader.decoder import DecodedPly, DecodeResult
from chessreader.model import get_provider
from chessreader.model.anthropic_provider import ModelError
from chessreader.model.base import Image
from chessreader.openings import detect as detect_opening
from chessreader.pgn_export import build_pgn
from chessreader.pipeline import BudgetExhausted, process_cascade, process_game
from chessreader.review import ReviewError, cell_from_dict, cells_from_plies, cells_to_dicts, redecode
from chessreader.sheet import Header

from .kv import get_kv
from .limits import Budget, log_game, stats
from .photos import new_game_id, store_photo
from .references import REFERENCES, compare

MAX_IMAGES = 2              # stage 1 uses one; room for a continuation sheet
MAX_IMAGE_BYTES = 4 * 1024 * 1024

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
                  admin: str = Form(None), model: str = Form(None), ref: str = Form(None)):
    s = Settings()
    if language:
        s.notation_language = language
    # Admin test mode (hidden in the page): choose the model per upload and compare
    # the result with a reference game. Needs ADMIN_TOKEN, so normal users can't use it.
    is_admin = bool(admin) and admin == os.environ.get("ADMIN_TOKEN")
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
        mt = f.content_type if f.content_type in ("image/jpeg", "image/png", "image/webp") else "image/jpeg"
        images.append(Image(data, mt))

    kv = get_kv()
    budget = Budget(kv, s)
    game_id = new_game_id()
    photo_refs, photo_errors = [], []
    if s.store_photos:
        for i, img in enumerate(images):
            pref, err = store_photo(img.data, img.media_type, game_id, i, request.headers)
            photo_refs.append(pref)
            if err:
                photo_errors.append(err)

    t0 = time.time()
    try:
        if not model and len(s.cascade_models) > 1:
            # cheap model first, strong model only if the result looks unsure
            outcome = process_cascade(images, lambda m: get_provider(replace(s, model_name=m)), s,
                                      budget_ok=budget.ok, on_call=budget.add)
        else:
            outcome = process_game(images, get_provider(s), s, budget_ok=budget.ok, on_call=budget.add)
    except BudgetExhausted:
        return _err(429, "daily_limit", "daily limit reached")
    except ModelError as e:
        return _err(502, "model_error", str(e))

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
        **(accuracy or {}), **({"admin": True} if is_admin else {}),
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
        "model_calls": len(outcome.calls),
        "stopped_because": outcome.stopped_because,
        "language": s.notation_language,
        **({"admin": {"model": route, "cost_eur": round(outcome.cost_eur, 4),
                      "models_used": models_used, "escalated": outcome.escalated,
                      "accuracy": accuracy}} if is_admin else {}),
    }


def outcome_cell(outcome, i):
    from chessreader.sheet import flatten
    toks = flatten(outcome.reading)
    t = toks[i] if i < len(toks) else None
    return {"index": i, "text": t.text if t else "", "number": t.number if t else None,
            "color": t.color if t else None}


class PgnRequest(BaseModel):
    header: dict
    moves: list[dict]          # [{san, status, reason, written, local, alternatives}]


@app.post("/api/pgn")
def pgn(req: PgnRequest):
    s = Settings()
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
    san: str                   # the chosen move (English SAN)
    language: str = "de"


@app.post("/api/redecode")
def redecode_route(req: RedecodeRequest):
    s = Settings()
    if req.cells is None:
        cells, plies = cells_from_plies(req.plies)
    else:
        cells, plies = [cell_from_dict(c) for c in req.cells], req.plies
    try:
        new_plies, new_cells, skipped = redecode(cells, plies, req.ply, req.san, req.language or s.notation_language)
    except ReviewError as e:
        return _err(400, "bad_request", str(e))
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
    admin = os.environ.get("ADMIN_TOKEN")
    if not admin or token != admin:
        return _err(403, "forbidden", "admin token required")
    kv = get_kv()
    s = Settings()
    out = stats(kv, today_prefix=_today_start())
    out["spent_today_eur"] = round(Budget(kv, s).spent(), 4)
    out["daily_budget_eur"] = s.daily_budget_eur
    out["max_calls_per_game"] = s.max_calls_per_game
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
