import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const config = {
  origin: "https://app.example.test", authorizeUrl: "https://id.example.test/authorize",
  tokenUrl: "https://id.example.test/token", clientId: "agentops",
  callback: "https://app.example.test/auth/callback",
};
function response(body, status = 200) {
  return { body, status, headers: new Headers(), cookies: new Map() };
}
const NextResponse = {
  redirect: url => response({ redirect: String(url) }, 307),
  json: (body, options) => response(body, options?.status),
};
function loadRoute(path, fetchMock = () => { throw new Error("Unexpected request"); }) {
  const source = readFileSync(new URL(`../src/app/${path}/route.ts`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const exports = {};
  const modules = {
    "next/server": { NextResponse },
    "@/lib/identity": { oidcConfig: () => config, cookieOptions: { httpOnly: true },
      sessionCookie: "agentops-session", organizationCookie: "agentops-organization" },
    "@/lib/api-url": { apiUrl: path => `https://api.example.test${path}` },
  };
  new Function("require", "exports", "fetch", compiled)(
    name => modules[name] ?? require(name), exports, fetchMock,
  );
  return exports;
}

test("sign-in binds state and nonce to an S256 PKCE challenge", async () => {
  const result = await loadRoute("auth/sign-in").GET();
  const url = new URL(result.body.redirect);
  const stored = JSON.parse(result.cookies.get("agentops-oidc"));
  assert.equal(url.searchParams.get("state"), stored.state);
  assert.equal(url.searchParams.get("nonce"), stored.nonce);
  assert.equal(url.searchParams.get("redirect_uri"), config.callback);
  assert.equal(url.searchParams.get("code_challenge_method"), "S256");
  assert.equal(url.searchParams.get("code_challenge"),
    createHash("sha256").update(stored.verifier).digest("base64url"));
  assert.ok(stored.state.length >= 32);
  assert.equal(result.headers.get("cache-control"), "no-store");
});

function callbackRequest(state = "correct-state") {
  return { nextUrl: new URL(`https://app.example.test/auth/callback?state=${state}&code=code`),
    cookies: { get: () => ({ value: JSON.stringify({ state: "correct-state", nonce: "expected-nonce",
      verifier: "expected-verifier" }) }) } };
}

test("callback rejects a forged state before requesting tokens", async () => {
  const result = await loadRoute("auth/callback").GET(callbackRequest("forged-state"));
  assert.equal(result.status, 401);
});

test("callback verifies nonce at API and stores only the opaque session", async () => {
  const calls = [];
  const fetchMock = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, json: async () => calls.length === 1 ? { id_token: "provider-secret-token" }
      : { session_token: "opaque-browser-session", expires_at: "2099-01-01T00:00:00Z" } };
  };
  const result = await loadRoute("auth/callback", fetchMock).GET(callbackRequest());
  assert.equal(calls[0].init.body.get("code_verifier"), "expected-verifier");
  assert.equal(calls[0].init.redirect, "error");
  assert.equal(calls[1].init.headers.authorization, "Bearer provider-secret-token");
  assert.equal(JSON.parse(calls[1].init.body).nonce, "expected-nonce");
  assert.equal(result.cookies.get("agentops-session"), "opaque-browser-session");
  assert.equal(result.body.redirect, "https://app.example.test/account");
  assert.ok(!JSON.stringify(result.body).includes("provider-secret-token"));
});

test("provider failure never creates a browser session or exposes the token", async () => {
  const route = loadRoute("auth/callback", async () => ({ ok: false }));
  const result = await route.GET(callbackRequest());
  assert.equal(result.status, 401);
  assert.equal(result.cookies.has("agentops-session"), false);
  assert.equal(result.body.error, "Sign-in failed. Please start again.");
});

test("organization UI validates selection against current memberships", () => {
  const read = path => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  assert.match(read("app/account/actions.ts"), /organizations\.some\(org => org\.id === selected\)/);
  assert.match(read("app/account/page.tsx"), /No active memberships/);
  assert.match(read("lib/identity.ts"), /httpOnly: true/);
  assert.match(read("lib/api.ts"), /await identityHeaders\(\)/);
});
