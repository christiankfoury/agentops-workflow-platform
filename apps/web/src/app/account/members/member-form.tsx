"use client";

import { useActionState } from "react";
import { saveMember } from "./actions";

export function MemberForm({ member }: { member?: {
  user_id: string; display_name: string; role: string; active: boolean;
} }) {
  const [state, action, pending] = useActionState(saveMember, {});
  return <form action={action} className="space-y-3 rounded-lg border p-4">
    <h2 className="font-semibold">{member?.display_name ?? "Add a provisioned user"}</h2>
    {member ? <input type="hidden" name="user_id" value={member.user_id} /> :
      <input name="user_id" aria-label="Provisioned user ID" placeholder="User ID" required className="w-full rounded border bg-background p-2" />}
    <div className="flex flex-wrap items-center gap-3">
      <select name="role" aria-label={`Role for ${member?.display_name ?? "new member"}`} defaultValue={member?.role ?? "viewer"} className="rounded border bg-background p-2">
        {["viewer", "operator", "reviewer", "admin"].map(role => <option key={role}>{role}</option>)}
      </select>
      <label><input type="checkbox" name="active" defaultChecked={member?.active ?? true} /> Active</label>
      <button disabled={pending} className="rounded border px-3 py-2 disabled:opacity-50">{pending ? "Saving…" : "Save membership"}</button>
    </div>
    {state.error && <p role="alert" className="text-sm text-red-700">{state.error}</p>}
    {state.success && <p role="status" className="text-sm text-green-700">{state.success}</p>}
  </form>;
}
