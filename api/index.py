"""Vercel entry point: every /api/* request is routed here (see vercel.json)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT)]

from server.app import app  # noqa: E402,F401
