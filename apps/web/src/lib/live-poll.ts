export type Pulse = { token: string; terminal: boolean; interval_ms: number };
export type PulseResult = { data?: Pulse; error?: string; stop?: boolean };
export type LiveKind = "execution" | "run" | "approval" | "executions" | "runs" | "approvals" | "operations";

/** Single-flight loop with injected clock/environment for deterministic checks. */
export function startPolling(options: {
  read: () => Promise<PulseResult>; refresh: () => void; status: (text: string) => void;
  available: () => boolean; schedule: (fn: () => void, ms: number) => unknown;
  cancel: (timer: unknown) => void; terminal?: boolean;
}) {
  let timer: unknown, disposed = false, pending = false, stopped = !!options.terminal, queuedForce = false;
  let token: string | undefined, failures = 0, interval = 5000;
  function schedule(ms: number) { options.cancel(timer); if (!disposed && !stopped) timer = options.schedule(() => { void tick(); }, ms); }
  async function tick(force = false) {
    if (disposed || pending || (stopped && !force)) return;
    if (force) stopped = false;
    if (!options.available()) { options.status("Updates paused while offline or in a hidden tab."); schedule(15000); return; }
    pending = true;
    try {
      const result = await options.read();
      if (disposed) return;
      if (result.error || !result.data) {
        stopped = !!result.stop; failures++;
        options.status(stopped ? "Live access changed. Reload your organization." : "Connection unavailable. Retrying with backoff; existing data is retained.");
        interval = Math.min(60000, 5000 * 2 ** Math.min(failures, 4));
      } else {
        const data = result.data;
        failures = 0; interval = Math.max(5000, Math.min(60000, data.interval_ms));
        if (token !== data.token || force) options.refresh();
        token = data.token; stopped = data.terminal;
        options.status(stopped ? "Run resolved. Live updates stopped." : `Live updates every ${interval / 1000} seconds.`);
      }
    } catch {
      if (disposed) return;
      failures++; interval = Math.min(60000, 5000 * 2 ** Math.min(failures, 4));
      options.status("Connection unavailable. Retrying with backoff; existing data is retained.");
    } finally { pending = false; if (queuedForce && !disposed) { queuedForce = false; void tick(true); } else schedule(interval); }
  }
  options.status(stopped ? "Run resolved. Live updates stopped." : "Live updates enabled.");
  schedule(interval);
  return {
    wake(force = false) { options.cancel(timer); if (pending) queuedForce ||= force; else void tick(force); },
    dispose() { disposed = true; options.cancel(timer); },
  };
}
