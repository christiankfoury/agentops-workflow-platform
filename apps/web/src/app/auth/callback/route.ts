import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { apiUrl } from "@/lib/api-url";
import { cookieOptions, oidcConfig, organizationCookie, sessionCookie } from "@/lib/identity";

export async function GET(request: NextRequest) {
  try {
    const config = oidcConfig();
    const stored = JSON.parse(request.cookies.get("agentops-oidc")?.value ?? "null");
    const state = request.nextUrl.searchParams.get("state");
    const code = request.nextUrl.searchParams.get("code");
    if (!stored || !state || !code || state.length !== stored.state.length
        || !timingSafeEqual(Buffer.from(state), Buffer.from(stored.state))) {
      throw new Error("Invalid sign-in state");
    }
    const tokens = await fetch(config.tokenUrl, {
      method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "authorization_code", code,
        client_id: config.clientId, redirect_uri: config.callback, code_verifier: stored.verifier,
        ...(process.env.OIDC_CLIENT_SECRET ? { client_secret: process.env.OIDC_CLIENT_SECRET } : {}),
      }), cache: "no-store", signal: AbortSignal.timeout(10000), redirect: "error",
    });
    if (!tokens.ok) throw new Error("Token exchange failed");
    const payload = await tokens.json();
    const accepted = await fetch(apiUrl("/identity/sessions"), {
      method: "POST", headers: {
        "Content-Type": "application/json", authorization: `Bearer ${payload.id_token}`,
      },
      body: JSON.stringify({ nonce: stored.nonce }),
      cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    if (!accepted.ok) throw new Error("Identity verification failed");
    const session = await accepted.json();
    const response = NextResponse.redirect(`${config.origin}/account`);
    response.cookies.set(sessionCookie, session.session_token, {
      ...cookieOptions, expires: new Date(session.expires_at),
    });
    response.cookies.delete("agentops-oidc");
    response.cookies.delete(organizationCookie);
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    const response = NextResponse.json({ error: "Sign-in failed. Please start again." }, { status: 401 });
    response.cookies.delete("agentops-oidc");
    return response;
  }
}
