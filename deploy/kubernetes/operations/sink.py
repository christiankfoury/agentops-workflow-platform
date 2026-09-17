"""Local operations fixture: durable idempotent receipts, never a hosted service."""

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Ledger:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS effects
                    (key TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS calls
                    (id INTEGER PRIMARY KEY, key TEXT, path TEXT, fresh INTEGER, created REAL);
                CREATE TABLE IF NOT EXISTS releases (key TEXT PRIMARY KEY);
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def accept(self, key, payload, path):
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT payload FROM effects WHERE key=?", (key,)).fetchone()
            if previous and previous[0] != encoded:
                raise ValueError("Idempotency key payload conflict")
            fresh = previous is None
            if fresh:
                db.execute("INSERT INTO effects VALUES (?,?,?)", (key, encoded, time.time()))
            db.execute(
                "INSERT INTO calls(key,path,fresh,created) VALUES (?,?,?,?)",
                (key, path, int(fresh), time.time()),
            )
        # Commit the receipt before delaying/losing the response.
        return fresh

    def release(self, key):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO releases VALUES (?)", (key,))

    def released(self, key):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM releases WHERE key=?", (key,)).fetchone() is not None

    def snapshot(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return {
                "effects": [dict(row) for row in db.execute("SELECT * FROM effects ORDER BY key")],
                "calls": [dict(row) for row in db.execute("SELECT * FROM calls ORDER BY id")],
            }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, body):
        payload = json.dumps(body).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected after a controlled worker failure.

    def do_GET(self):
        if self.path == "/health":
            return self.respond(200, {"status": "ready"})
        if self.path == "/snapshot":
            return self.respond(200, self.server.ledger.snapshot())
        self.respond(404, {})

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384:
                return self.respond(413, {})
            body = json.loads(self.rfile.read(size))
            if self.path == "/release":
                key = body["key"]
                if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,100}", key):
                    return self.respond(400, {})
                self.server.ledger.release(key)
                return self.respond(200, {"released": key})
            key = self.headers.get("Idempotency-Key", "")
            if self.path not in {"/write", "/slow", "/hold"} or not re.fullmatch(
                r"[a-zA-Z0-9:_-]{1,100}", key
            ):
                return self.respond(400, {})
            fresh = self.server.ledger.accept(key, body, self.path)
            if self.path == "/slow":
                time.sleep(3)
            if self.path == "/hold" and fresh:
                deadline = time.monotonic() + 150
                while not self.server.ledger.released(key) and time.monotonic() < deadline:
                    time.sleep(0.1)
            self.respond(200, body)
        except (ValueError, KeyError, TypeError):
            self.respond(409, {"error": "invalid or conflicting request"})


def server(path, address=("0.0.0.0", 8080)):
    result = ThreadingHTTPServer(address, Handler)
    result.daemon_threads = True
    result.ledger = Ledger(path)
    return result


if __name__ == "__main__":
    path = Path(os.environ.get("SINK_DATABASE", "/data/effects.sqlite"))
    server(path).serve_forever()
