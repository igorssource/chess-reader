"""Tiny key-value store for the daily budget counter and the game log.

On Vercel: Upstash Redis from the Vercel Marketplace (free tier). It sets
KV_REST_API_URL / KV_REST_API_TOKEN (or UPSTASH_REDIS_REST_URL / _TOKEN).
Without them (local development) an in-memory store is used.
"""
from __future__ import annotations

import json
import os
import urllib.request


class MemoryKV:
    def __init__(self):
        self.data: dict = {}

    def incr_float(self, key: str, amount: float, ttl: int) -> float:
        self.data[key] = float(self.data.get(key, 0.0)) + amount
        return self.data[key]

    def get_float(self, key: str) -> float:
        return float(self.data.get(key, 0.0))

    def push_log(self, key: str, item: dict, keep: int):
        lst = self.data.setdefault(key, [])
        lst.insert(0, json.dumps(item))
        del lst[keep:]

    def read_log(self, key: str, n: int) -> list[dict]:
        return [json.loads(x) for x in self.data.get(key, [])[:n]]


class UpstashKV:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = token

    def _cmd(self, *args):
        req = urllib.request.Request(
            self.url, data=json.dumps([str(a) for a in args]).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())["result"]

    def incr_float(self, key, amount, ttl):
        value = float(self._cmd("INCRBYFLOAT", key, f"{amount:.6f}"))
        self._cmd("EXPIRE", key, ttl)
        return value

    def get_float(self, key):
        v = self._cmd("GET", key)
        return float(v) if v else 0.0

    def push_log(self, key, item, keep):
        self._cmd("LPUSH", key, json.dumps(item, ensure_ascii=False))
        self._cmd("LTRIM", key, 0, keep - 1)

    def read_log(self, key, n):
        return [json.loads(x) for x in self._cmd("LRANGE", key, 0, n - 1)]


_memory = MemoryKV()


def get_kv():
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        return UpstashKV(url, token)
    return _memory
