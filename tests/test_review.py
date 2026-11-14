"""Stage 2: a person fixes a move, the rest of the game is decoded again."""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ["MODEL_PROVIDER"] = "fake"

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402

client = TestClient(app)


def _process():
    r = client.post("/api/process", files={"files": ("a.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()


def test_process_returns_cells():
    d = _process()
    assert d["cells"] and d["cells"][0]["text"] == "e4"
    assert "layout" in d


def test_fix_move_redecodes_rest():
    d = _process()
    plies = d["plies"]
    # a wrong choice for Black's 1st move: the rest must still be decoded from the new position
    r = client.post("/api/redecode", json={"header": d["header"], "plies": plies, "cells": d["cells"],
                                           "ply": 1, "san": "e6"})
    assert r.status_code == 200, r.text
    n = r.json()
    assert [p["san"] for p in n["plies"][:2]] == ["e4", "e6"]
    assert n["plies"][1]["status"] == "ok" and n["plies"][1]["reason"] == "user"
    assert n["plies"][1]["written"] == "e5"
    assert n["cells"][1]["pinned"] is True
    # fixing it back gives the original game again; the pin survives the next fix
    r = client.post("/api/redecode", json={"header": d["header"], "plies": n["plies"], "cells": n["cells"],
                                           "ply": 1, "san": "e5"})
    m = r.json()
    assert [p["san"] for p in m["plies"]] == [p["san"] for p in plies]
    assert m["plies"][-1]["san"] == "Rd8#" and "1. e4 e5" in m["pgn"]


def test_confirm_inserted_move():
    d = _process()
    k = next(p["ply"] for p in d["plies"] if p["reason"] == "missing")
    san = d["plies"][k]["san"]
    r = client.post("/api/redecode", json={"header": d["header"], "plies": d["plies"], "cells": d["cells"],
                                           "ply": k, "san": san})
    n = r.json()
    assert [p["san"] for p in n["plies"]] == [p["san"] for p in d["plies"]]
    assert n["plies"][k]["status"] == "ok" and n["plies"][-1]["san"] == "Rd8#"


def test_old_game_without_cells():
    d = _process()
    plies = [{k: v for k, v in p.items() if k != "token"} for p in d["plies"]]
    r = client.post("/api/redecode", json={"header": d["header"], "plies": plies, "ply": 0, "san": "e4"})
    assert r.status_code == 200, r.text
    assert r.json()["plies"][-1]["san"] == "Rd8#"


def test_illegal_choice():
    d = _process()
    r = client.post("/api/redecode", json={"header": d["header"], "plies": d["plies"], "cells": d["cells"],
                                           "ply": 0, "san": "e5"})
    assert r.status_code == 400


def test_fix_by_text_and_suggestions():
    d = _process()
    r = client.post("/api/redecode", json={"header": d["header"], "plies": d["plies"], "cells": d["cells"],
                                           "ply": 1, "text": "e6"})
    assert r.status_code == 200 and r.json()["plies"][1]["san"] == "e6"
    r = client.post("/api/redecode", json={"header": d["header"], "plies": d["plies"], "cells": d["cells"],
                                           "ply": 2, "text": "Sf4"})
    assert r.status_code == 400 and "Sf3" in r.json()["options"]
