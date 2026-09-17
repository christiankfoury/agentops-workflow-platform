"use client";

import { useEffect, useState, startTransition } from "react";
import { useRouter } from "next/navigation";
import { startPolling, type LiveKind } from "@/lib/live-poll";
import { readPulse } from "@/app/operations/live-actions";

export function LiveRefresh({ scope, kind, id, terminal = false }: {
  scope: string | null; kind: LiveKind; id?: string; terminal?: boolean;
}) {
  const router = useRouter(), [status, setStatus] = useState("Live updates enabled.");
  useEffect(() => {
    let active = true;
    const loop = startPolling({
      read: () => readPulse(scope, kind, id),
      refresh: () => startTransition(() => router.refresh()), status: text => queueMicrotask(() => { if (active) setStatus(text); }),
      available: () => navigator.onLine !== false && document.visibilityState !== "hidden",
      schedule: (fn, ms) => window.setTimeout(fn, ms), cancel: timer => window.clearTimeout(timer as number), terminal,
    });
    const wake = () => loop.wake(), mutation = () => loop.wake(true);
    window.addEventListener("online", wake); window.addEventListener("offline", wake);
    document.addEventListener("visibilitychange", wake); window.addEventListener("workflow:mutated", mutation);
    return () => { active = false; loop.dispose(); window.removeEventListener("online", wake); window.removeEventListener("offline", wake);
      document.removeEventListener("visibilitychange", wake); window.removeEventListener("workflow:mutated", mutation); };
  }, [scope, kind, id, terminal, router]);
  return <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground"><span role="status">{status}</span>
    <button className="rounded border px-2 py-1" onClick={() => window.dispatchEvent(new window.Event("workflow:mutated"))}>Refresh now</button></div>;
}
