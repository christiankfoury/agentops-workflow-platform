import Link from "next/link";
import { PermissionGate } from "@/components/permission-gate";
import { getIdentity } from "@/lib/identity";
import { selectOrganization, signOut } from "./actions";

export const dynamic = "force-dynamic";

export default async function AccountPage() {
  const enabled = process.env.IDENTITY_ENABLED === "true";
  const identity = await getIdentity();
  return <section className="mx-auto max-w-2xl space-y-6 rounded-xl border bg-card p-6">
    <h1 className="text-2xl font-semibold">Account and organization</h1>
    <PermissionGate action="membership.manage"><Link href="/account/members" className="underline">Manage members and view audit history</Link></PermissionGate>
    {!enabled ? <p>Sign-in is not configured for this local workspace.</p> : !identity ? <>
      <p>Sign in with your organization’s identity provider to access your workflows.</p>
      <a href="/auth/sign-in" className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-white">
        Sign in
      </a>
    </> : <>
      <p>Signed in as <strong>{identity.display_name}</strong></p>
      <form action={selectOrganization} className="space-y-4">
        <label htmlFor="organization" className="block font-medium">Organization</label>
        <select id="organization" name="organization_id" required className="w-full rounded border p-3">
          {identity.organizations.map(org => <option key={org.id} value={org.id}>
            {org.name} · {org.role}
          </option>)}
        </select>
        {identity.organizations.length ? <button className="rounded-lg bg-blue-600 px-4 py-2 text-white">
          Continue to organization
        </button> : <p>No active memberships. Contact your organization administrator.</p>}
      </form>
      <form action={signOut}><button className="text-sm underline">Sign out</button></form>
    </>}
  </section>;
}
