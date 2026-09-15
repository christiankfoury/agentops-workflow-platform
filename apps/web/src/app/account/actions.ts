"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { apiUrl } from "@/lib/api-url";
import {
  cookieOptions, getIdentity, identityHeaders, organizationCookie, sessionCookie,
} from "@/lib/identity";

export async function selectOrganization(form: FormData) {
  const identity = await getIdentity();
  const selected = form.get("organization_id");
  if (typeof selected !== "string" || !identity?.organizations.some(org => org.id === selected)) {
    throw new Error("Select an organization with an active membership");
  }
  (await cookies()).set(organizationCookie, selected, cookieOptions);
  redirect("/");
}

export async function signOut() {
  const response = await fetch(apiUrl("/identity/sessions/current"), {
    method: "DELETE", headers: await identityHeaders(), cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok && response.status !== 401) throw new Error("Could not end your session");
  const jar = await cookies();
  jar.delete(sessionCookie);
  jar.delete(organizationCookie);
  redirect("/account");
}
