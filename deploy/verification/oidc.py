"""Private-network synthetic OIDC provider, only for explicit local verification."""

import base64
import hashlib
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key

ORIGIN = os.environ["FIXTURE_ORIGIN"]
CLIENT = "agentops-verification"
KEY = load_pem_private_key(Path("/run/secrets/fixture_signing_key").read_bytes(), password=None)
JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key())) | {
    "kid": "fixture",
    "use": "sig",
}
CODES = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Authorization codes and tokens must never appear in request logs.

    def result(self, status, body, **headers):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/oidc/jwks":
            return self.result(200, {"keys": [JWK]})
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if (
            parsed.path != "/oidc/authorize"
            or query.get("client_id") != CLIENT
            or query.get("redirect_uri") != ORIGIN + "/auth/callback"
            or query.get("response_type") != "code"
            or query.get("code_challenge_method") != "S256"
            or not all(query.get(k) for k in ["state", "nonce", "code_challenge"])
        ):
            return self.result(400, {"error": "invalid_request"})
        for code in list(CODES):
            if CODES[code]["expires"] < time.time():
                del CODES[code]
        if len(CODES) >= 100:
            return self.result(429, {"error": "fixture_capacity"})
        code = secrets.token_urlsafe(32)
        CODES[code] = query | {"expires": time.time() + 60}
        return self.result(
            302,
            {},
            Location=query["redirect_uri"]
            + "?"
            + urlencode(
                {
                    "code": code,
                    "state": query["state"],
                }
            ),
        )

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if self.path != "/oidc/token" or not 0 < length < 8192:
            return self.result(400, {"error": "invalid_request"})
        data = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        grant = CODES.pop(data.get("code", ""), None)
        challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(data.get("code_verifier", "").encode()).digest()
            )
            .decode()
            .rstrip("=")
        )
        if (
            not grant
            or grant["expires"] < time.time()
            or data.get("client_id") != CLIENT
            or data.get("grant_type") != "authorization_code"
            or data.get("redirect_uri") != grant["redirect_uri"]
            or not secrets.compare_digest(challenge, grant["code_challenge"])
        ):
            return self.result(400, {"error": "invalid_grant"})
        token = jwt.encode(
            {
                "iss": ORIGIN + "/oidc",
                "aud": CLIENT,
                "sub": "local-verifier",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
                "nonce": grant["nonce"],
            },
            KEY,
            algorithm="RS256",
            headers={"kid": "fixture"},
        )
        return self.result(200, {"id_token": token, "token_type": "Bearer"})


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
