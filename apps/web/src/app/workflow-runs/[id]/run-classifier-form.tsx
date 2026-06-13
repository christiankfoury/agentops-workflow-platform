"use client";

import { useActionState } from "react";
import { runClassifierAction } from "./actions";

const initialState = { error: null };

export function RunClassifierForm({ runId }: { runId: string }) {
  const [state, formAction, pending] = useActionState(
    runClassifierAction,
    initialState,
  );

  return (
    <form action={formAction} className="mt-4">
      <input type="hidden" name="run_id" value={runId} />
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Running..." : "Run Classifier"}
      </button>
      {state.error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
    </form>
  );
}
