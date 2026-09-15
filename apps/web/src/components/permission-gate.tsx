import { cache, type ReactNode } from "react";
import { getAccessPermissions } from "@/lib/api";

export const allowedActions = cache(async (): Promise<string[]> => {
  try { return await getAccessPermissions(); } catch { return []; }
});

export async function PermissionGate({ action, children, fallback = null }: {
  action: string; children: ReactNode; fallback?: ReactNode;
}) {
  return (await allowedActions()).includes(action) ? children : fallback;
}
