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
        r = client.post("/api/process", files={"files": ("a.jpg", b"\xff\xd8x", "image/jpeg")})
        assert r.status_code == 429 and r.json()["error"] == "daily_limit"
    finally:
        del os.environ["DAILY_BUDGET_EUR"]


def test_pgn_after_edit():
    r = client.post("/api/pgn", json={"header": {"white": "X", "result": "*"},
                                      "moves": [{"san": "e4"}, {"san": "e5", "status": "doubtful",
                                                                "written": "e6", "local": "e5"}]})
    assert r.status_code == 200 and "1. e4 e5" in r.json()["pgn"]
    assert r.json()["opening"]["family"] == "King's Pawn Game" and '[ECO "C20"]' in r.json()["pgn"]


def test_admin_model_and_reference():
    from server.references import check_references
    check_references()
    f = {"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")}
    # model / reference choice needs the admin token
    assert client.post("/api/process", files=f, data={"model": "claude-haiku-5-5"}).status_code == 403
    assert client.post("/api/process", files=f, data={"admin": "t", "model": "gpt"}).status_code == 400
    r = client.post("/api/process", files=f, data={"admin": "t", "model": "claude-haiku-5-5", "ref": "02"})
    assert r.status_code == 200, r.text
    a = r.json()["admin"]
    assert a["model"] == "claude-haiku-5-5" and a["accuracy"]["ref_plies"] == 30
    s = client.get("/api/stats?token=t").json()
    assert "claude-haiku-5-5" in s["by_model"] and s["today"]["games"] >= 1
    assert s["ref_runs"][0]["ref"] == "02" and s["ref_runs"][0]["model"] == "claude-haiku-5-5"


def test_games_per_ip_limit():
    from server import limits
    f = {"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")}
    h = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
    os.environ["GAMES_PER_IP_PER_DAY"] = "2"
    try:
        assert client.post("/api/process", files=f, headers=h).status_code == 200
        # a manual fix needs no model and is not counted
        assert client.post("/api/pgn", headers=h, json={"header": {}, "moves": [{"san": "e4"}]}).status_code == 200
        assert client.post("/api/process", files=f, headers=h).status_code == 200
        r = client.post("/api/process", files=f, headers=h)
        assert r.status_code == 429 and r.json()["error"] == "ip_limit" and r.json()["limit"] == 2
        # another address is not affected, the admin test mode is not limited
        assert client.post("/api/process", files=f, headers={"x-real-ip": "198.51.100.1"}).status_code == 200
        assert client.post("/api/process", files=f, headers=h, data={"admin": "t"}).status_code == 200
    finally:
        del os.environ["GAMES_PER_IP_PER_DAY"]
    # dated values: 10 on 2026-11-15, 5 afterwards
    assert limits.GAMES_PER_IP_DAYS["2026-11-15"] == 10 and limits.GAMES_PER_IP_DEFAULT == 5
    orig = limits.today
    try:
        limits.today = lambda: "2026-11-15"
        assert limits.IpLimit(limits_kv(), "x").limit == 10
        limits.today = lambda: "2026-11-16"
        assert limits.IpLimit(limits_kv(), "x").limit == 5
    finally:
        limits.today = orig


def limits_kv():
    from server.kv import MemoryKV
    return MemoryKV()


def test_day_history_splits_users_and_admin():
    from server.kv import get_kv
    from server.limits import LOG_KEY, today
    kv = get_kv()
    kv.data.clear()
    f = {"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")}
    os.environ["GAMES_PER_IP_PER_DAY"] = "2"
    try:
        for ip, n in (("1.1.1.1", 2), ("2.2.2.2", 1)):
            for _ in range(n):
                assert client.post("/api/process", files=f, headers={"x-real-ip": ip}).status_code == 200
        assert client.post("/api/process", files=f, headers={"x-real-ip": "1.1.1.1"}).status_code == 429
        assert client.post("/api/process", files=f, data={"admin": "t"},
                           headers={"x-real-ip": "1.1.1.1"}).status_code == 200
    finally:
        del os.environ["GAMES_PER_IP_PER_DAY"]
    row = client.get("/api/stats?token=t").json()["days"][0]
    assert row["date"] == today()
    assert (row["games_user"], row["games_admin"], row["ips"], row["max_per_ip"]) == (3, 1, 2, 2)
    assert row["ip_histogram"] == {"1": 1, "2": 1} and row["ip_limit_hits"] == 1
    assert "1.1.1.1" not in str(kv.data)                     # no plain address is stored
    # a day recorded before this history existed: rebuilt from the log and the limit counters
    del kv.data[f"day:{today()}"], kv.data[f"dayip:{today()}"]
    row = client.get("/api/stats?token=t").json()["days"][0]
    assert (row["games_user"], row["games_admin"], row["ips"], row["max_per_ip"]) == (3, 1, 2, 2)
    assert len(kv.read_log(LOG_KEY, 10)) == 4


def test_security_guards():
    from concurrent.futures import ThreadPoolExecutor
    from server.kv import get_kv
    kv = get_kv()
    photos_before = len(kv.read_log("games", 5000))
    # a file that is not a photo is refused before anything is stored or read
    r = client.post("/api/process", files={"files": ("a.jpg", b"<html>not a photo", "image/jpeg")})
    assert r.status_code == 400 and r.json()["error"] == "not_image"
    assert len(kv.read_log("games", 5000)) == photos_before
    # an unknown notation language does not break the upload
    f = {"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")}
    assert client.post("/api/process", files=f, data={"language": "xx"},
                       headers={"x-real-ip": "192.0.2.50"}).status_code == 200
    # uploads sent at the same moment cannot all slip under the per-IP limit
    os.environ["GAMES_PER_IP_PER_DAY"] = "2"
    try:
        h = {"x-real-ip": "192.0.2.77"}
        with ThreadPoolExecutor(8) as ex:
            codes = list(ex.map(lambda _: client.post("/api/process", files=f, headers=h).status_code, range(8)))
        assert codes.count(200) == 2 and codes.count(429) == 6
    finally:
        del os.environ["GAMES_PER_IP_PER_DAY"]
    # the admin token is accepted in a header; a wrong or empty one is refused
    assert client.get("/api/stats", headers={"x-admin-token": "t"}).status_code == 200
    assert client.get("/api/stats", headers={"x-admin-token": "tt"}).status_code == 403
    assert client.get("/api/stats").status_code == 403
    # absurdly long games are refused by the model-free routes
    assert client.post("/api/pgn", json={"header": {}, "moves": [{"san": "e4"}] * 1001}).status_code == 400
