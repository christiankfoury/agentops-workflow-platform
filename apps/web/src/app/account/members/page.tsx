import Link from "next/link";
import { allowedActions } from "@/components/permission-gate";
import { listAuditEvents, listMembers } from "@/lib/api";
import { MemberForm } from "./member-form";

export default async function MembersPage() {
  if (!(await allowedActions()).includes("membership.manage")) {
    return <p>Organization administrator access is required to manage members.</p>;
  }
  const [members, audit] = await Promise.all([listMembers(), listAuditEvents()]);
  return <div className="mx-auto max-w-4xl space-y-6">
    <Link href="/account" className="text-sm underline">Back to account</Link>
    <h1 className="text-2xl font-semibold">Members and audit history</h1>
    <p className="text-muted-foreground">Changes apply to the selected organization. Users must already be provisioned by an identity administrator.</p>
    {members.map(member => <MemberForm key={member.user_id} member={member} />)}
    <MemberForm />
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Recent audit events</h2>
      <p className="text-sm text-muted-foreground">Latest 100 accepted actions. Times are UTC.</p>
      {audit.length === 0 ? <p>No audit events yet.</p> : audit.map(entry => <article key={entry.id} className="rounded border p-3 text-sm break-words">
        <strong>{entry.action}</strong> · <time>{entry.created_at}</time>
        <p>Actor: {entry.actor_user_id ?? entry.actor_kind}</p>
        <p>{entry.target_type}: {entry.target_id}</p>
      </article>)}
    </section>
  </div>;
}
