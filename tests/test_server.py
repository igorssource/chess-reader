import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ["MODEL_PROVIDER"] = "fake"
os.environ["ADMIN_TOKEN"] = "t"

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402

client = TestClient(app)


def test_process_and_stats():
    r = client.post("/api/process", files={"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["plies"][-1]["san"] == "Rd8#"
    assert any(p["reason"] == "missing" for p in d["plies"])
    assert '[White "Morphy"]' in d["pgn"]
    s = client.get("/api/stats?token=t").json()
    assert s["games"] >= 1 and s["avg_calls_per_game"] >= 1
    assert client.get("/api/stats?token=wrong").status_code == 403


def test_daily_limit():
    os.environ["DAILY_BUDGET_EUR"] = "0"
    try:
        r = client.post("/api/process", files={"files": ("a.jpg", b"x", "image/jpeg")})
        assert r.status_code == 429 and r.json()["error"] == "daily_limit"
    finally:
        del os.environ["DAILY_BUDGET_EUR"]


def test_pgn_after_edit():
    r = client.post("/api/pgn", json={"header": {"white": "X", "result": "*"},
                                      "moves": [{"san": "e4"}, {"san": "e5", "status": "doubtful",
                                                                "written": "e6", "local": "e5"}]})
    assert r.status_code == 200 and "1. e4 e5" in r.json()["pgn"]
