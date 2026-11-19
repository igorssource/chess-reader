import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "core"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_memory_store():
    """Every test starts with an empty in-memory store (no per-IP counts left from other tests)."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from server import kv
    kv._memory.data.clear()
    yield
