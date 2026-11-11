"""HTTP API used by the web page.

POST /api/process   photo(s) of one game -> moves with marks + PGN
POST /api/pgn       header + moves -> PGN (after the user edits; no model call)
GET  /api/health    settings visible to the page (no secrets)
GET  /api/stats     usage statistics (needs ADMIN_TOKEN)
"""
from __future__ import annotations

import os
import time

import chess
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chessreader.config import Settings
from chessreader.decoder import DecodedPly, DecodeResult
from chessreader.model import get_provider
from chessreader.model.anthropic_provider import ModelError
from chessreader.model.base import Image
from chessreader.pgn_export import build_pgn
from chessreader.pipeline import BudgetExhausted, process_game
from chessreader.sheet import Header

from .kv import get_kv
from .limits import Budget, log_game, stats
from .photos import new_game_id, store_photo

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
            "max_calls_per_game": s.max_calls_per_game, "budget_left_today": b.remaining() > 0,
            "stores_photos": s.store_photos}


@app.post("/api/process")
async def process(request: Request, files: list[UploadFile] = File(...), language: str = Form(None)):
    s = Settings()
    if language:
        s.notation_language = language
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
            ref, err = store_photo(img.data, img.media_type, game_id, i, request.headers)
            photo_refs.append(ref)
            if err:
                photo_errors.append(err)

    t0 = time.time()
    try:
        outcome = process_game(images, get_provider(s), s, budget_ok=budget.ok, on_call=budget.add)
    except BudgetExhausted:
        return _err(429, "daily_limit", "daily limit reached")
    except ModelError as e:
        return _err(502, "model_error", str(e))

    r = outcome.result
    log_game(kv, {
        "id": game_id, "ts": int(t0), "seconds": round(time.time() - t0, 1),
        "model": s.model_name, "calls": len(outcome.calls),
        "cost_eur": round(outcome.cost_eur, 5), "stopped": outcome.stopped_because,
        "plies": len(r.plies), "doubtful": sum(p.status == "doubtful" for p in r.plies),
        "fixed": sum(p.status == "fixed" for p in r.plies), "photos": [p for p in photo_refs if p],
        **({"photo_error": photo_errors[0]} if photo_errors else {}),
    })
    return {
        "game_id": game_id,
        "header": outcome.reading.header.__dict__,
        "plies": [p.__dict__ for p in r.plies],
        "skipped_cells": [outcome_cell(outcome, i) for i in r.skipped_tokens],
        "pgn": outcome.pgn,
        "model_calls": len(outcome.calls),
        "stopped_because": outcome.stopped_because,
        "language": s.notation_language,
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
    return {"pgn": build_pgn(header, DecodeResult(plies, [], 0, board.fen()), s.pgn_comments_language)}


@app.get("/api/stats")
def get_stats(request: Request, token: str = ""):
    admin = os.environ.get("ADMIN_TOKEN")
    if not admin or token != admin:
        return _err(403, "forbidden", "admin token required")
    kv = get_kv()
    s = Settings()
    out = stats(kv)
    out["spent_today_eur"] = round(Budget(kv, s).spent(), 4)
    out["daily_budget_eur"] = s.daily_budget_eur
    out["max_calls_per_game"] = s.max_calls_per_game
    return out


@app.api_route("/{rest:path}", methods=["GET", "POST"], include_in_schema=False)
def not_found(rest: str, request: Request):
    # Shows which path the server actually received (helps to debug routing on the host).
    return _err(404, "not_found", f"no route for /{rest}")
