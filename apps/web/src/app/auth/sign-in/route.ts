import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { cookieOptions, oidcConfig } from "@/lib/identity";

export async function GET() {
  try {
    const config = oidcConfig();
    const state = randomBytes(32).toString("base64url");
    const nonce = randomBytes(32).toString("base64url");
    const verifier = randomBytes(32).toString("base64url");
    const url = new URL(config.authorizeUrl);
    url.search = new URLSearchParams({
      response_type: "code", client_id: config.clientId, redirect_uri: config.callback,
      scope: "openid profile", state, nonce,
      code_challenge: createHash("sha256").update(verifier).digest("base64url"),
      code_challenge_method: "S256",
    }).toString();
    const response = NextResponse.redirect(url);
    response.cookies.set("agentops-oidc", JSON.stringify({ state, nonce, verifier }), {
      ...cookieOptions, maxAge: 600,
    });
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return NextResponse.json({ error: "Sign-in is not configured" }, { status: 503 });
  }
}
