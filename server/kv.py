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

    def hincr(self, key: str, field: str, amount: float, ttl: int):
        h = self.data.setdefault(key, {})
        h[field] = float(h.get(field, 0.0)) + amount

    def hgetall_many(self, keys: list[str]) -> list[dict]:
        return [dict(self.data.get(k) or {}) for k in keys]

    def counters(self, prefix: str) -> dict:
        """All plain counters whose key starts with the prefix: {rest of key: value}."""
        return {k[len(prefix):]: float(v) for k, v in self.data.items()
                if k.startswith(prefix) and not isinstance(v, (dict, list))}


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

    def _pipe(self, commands: list[list]):
        req = urllib.request.Request(
            self.url + "/pipeline", data=json.dumps([[str(a) for a in c] for c in commands]).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return [x.get("result") for x in json.loads(r.read())]

    def hincr(self, key, field, amount, ttl):
        self._pipe([["HINCRBYFLOAT", key, field, f"{amount:.6f}"], ["EXPIRE", key, ttl]])

    def hgetall_many(self, keys):
        if not keys:
            return []
        out = []
        for flat in self._pipe([["HGETALL", k] for k in keys]):
            flat = flat or []
            out.append({flat[i]: float(flat[i + 1]) for i in range(0, len(flat) - 1, 2)})
        return out

    def counters(self, prefix):
        keys = self._cmd("KEYS", prefix + "*") or []
        if not keys:
            return {}
        values = self._cmd("MGET", *keys)
        return {k[len(prefix):]: float(v) for k, v in zip(keys, values) if v}

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
