"""The operations evidence sink must deduplicate durably before acknowledging."""

import importlib.util
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread

import httpx
import pytest

path = Path(__file__).resolve().parents[3] / "deploy/kubernetes/operations/sink.py"
spec = importlib.util.spec_from_file_location("operations_sink", path)
sink = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sink)


def test_concurrent_receipts_commit_once_and_conflicts_preserve_history(tmp_path):
    ledger = sink.Ledger(tmp_path / "effects.sqlite")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda _: ledger.accept("same", {"value": "one"}, "/write"), range(24))
        )
    assert sum(results) == 1
    before = ledger.snapshot()
    assert len(before["effects"]) == 1 and len(before["calls"]) == 24
    with pytest.raises(ValueError, match="conflict"):
        ledger.accept("same", {"value": "changed"}, "/write")
    assert sink.Ledger(tmp_path / "effects.sqlite").snapshot() == before


def test_effect_survives_unacknowledged_response_and_server_restart(tmp_path):
    database = tmp_path / "effects.sqlite"
    server = sink.server(database, ("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    headers = {"Idempotency-Key": "held"}
    payload = {"value": "persisted"}
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(
                httpx.post, origin + "/hold", json=payload, headers=headers, timeout=10
            )
            deadline = time.monotonic() + 5
            while not server.ledger.snapshot()["effects"] and time.monotonic() < deadline:
                time.sleep(0.01)
            assert len(server.ledger.snapshot()["effects"]) == 1
            assert not first.done()
            repeated = httpx.post(origin + "/hold", json=payload, headers=headers)
            assert repeated.status_code == 200 and repeated.json() == payload
            server.ledger.release("held")
            assert first.result(timeout=5).json() == payload
        assert httpx.post(origin + "/write", json=payload).status_code == 400
        assert (
            httpx.post(origin + "/write", json={"value": "changed"}, headers=headers).status_code
            == 409
        )
    finally:
        server.ledger.release("held")
        server.shutdown()
        server.server_close()
        thread.join(5)
    restarted = sink.server(database, ("127.0.0.1", 0))
    thread = Thread(target=restarted.serve_forever, daemon=True)
    thread.start()
    try:
        response = httpx.post(
            f"http://127.0.0.1:{restarted.server_port}/write", json=payload, headers=headers
        )
        assert response.json() == payload
        snapshot = restarted.ledger.snapshot()
        assert len(snapshot["effects"]) == 1 and len(snapshot["calls"]) == 3
    finally:
        restarted.shutdown()
        restarted.server_close()
        thread.join(5)
