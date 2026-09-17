import { builderRequest } from "@/lib/api";
import type { LiveKind } from "@/lib/live-poll";
import { LiveRefresh } from "./live-refresh";

export async function LivePage({ kind, id, terminal }: { kind: LiveKind; id?: string; terminal?: boolean }) {
  let access: { organization_id: string | null };
  try {
    access = await builderRequest<{ organization_id: string | null }>("/access/permissions");
  } catch { return <p className="text-xs">Live access unavailable. Reload to reconnect.</p>; }
  return <LiveRefresh key={`${access.organization_id}:${kind}:${id}`} scope={access.organization_id} kind={kind} id={id} terminal={terminal} />;
}
