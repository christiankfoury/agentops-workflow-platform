import "server-only";

import { cookies } from "next/headers";
import { apiUrl } from "./api-url";

export const sessionCookie = "agentops-session";
export const organizationCookie = "agentops-organization";
export const cookieOptions = {
  httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax" as const,
  path: "/",
};

export interface Identity {
  id: string;
  display_name: string;
  kind: "user" | "service";
  organizations: Array<{ id: string; name: string; role: string }>;
}

export async function identityHeaders(): Promise<Headers> {
  const jar = await cookies();
  const headers = new Headers();
  const session = jar.get(sessionCookie)?.value;
  const organization = jar.get(organizationCookie)?.value;
  if (session) headers.set("authorization", `Session ${session}`);
  if (organization) headers.set("x-organization-id", organization);
  return headers;
}

export async function getIdentity(): Promise<Identity | null> {
  if (process.env.IDENTITY_ENABLED !== "true") return null;
  const response = await fetch(apiUrl("/identity/me"), {
    headers: await identityHeaders(), cache: "no-store", signal: AbortSignal.timeout(10000),
  });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error("Sign-in service is unavailable");
  return response.json() as Promise<Identity>;
}

export function oidcConfig() {
  if (process.env.IDENTITY_ENABLED !== "true") throw new Error("Sign-in is disabled");
  const origin = process.env.APP_ORIGIN;
  const authorizeUrl = process.env.OIDC_AUTHORIZE_URL;
  const tokenUrl = process.env.OIDC_TOKEN_URL;
  const clientId = process.env.OIDC_CLIENT_ID;
  if (!origin || !authorizeUrl || !tokenUrl || !clientId) {
    throw new Error("Sign-in is not configured");
  }
  for (const value of [origin, authorizeUrl, tokenUrl]) {
    const url = new URL(value);
    if (url.protocol !== "https:" && !(process.env.NODE_ENV !== "production"
        && url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) {
      throw new Error("Sign-in endpoints require HTTPS");
    }
  }
  return { origin: new URL(origin).origin, authorizeUrl, tokenUrl, clientId,
    callback: `${new URL(origin).origin}/auth/callback` };
}
