import fs from "node:fs";
for (const name of ["OIDC_CLIENT_SECRET"]) {
  const file = process.env[`${name}_FILE`];
  if (file) {
    if (process.env[name]) throw new Error(`Configure either ${name} or ${name}_FILE`);
    process.env[name] = fs.readFileSync(file, "utf8").trim();
  }
}
if (process.env.IDENTITY_ENABLED !== "true") throw new Error("Production requires verified identity");
for (const name of ["APP_ORIGIN", "OIDC_AUTHORIZE_URL", "OIDC_TOKEN_URL"]) {
  if (new URL(process.env[name]).protocol !== "https:") throw new Error(`${name} requires HTTPS`);
}
if (!process.env.OIDC_CLIENT_ID) throw new Error("OIDC_CLIENT_ID is required");
await import("./apps/web/server.js");
