"use client";

import { useActionState } from "react";
import { createEvaluationComparisonAction } from "./actions";

const initialState = { error: null };

export function CreateEvaluationComparisonForm({
  compact = false,
  runId,
}: {
  compact?: boolean;
  runId: string;
}) {
  const [state, formAction, pending] = useActionState(
    createEvaluationComparisonAction,
    initialState,
  );

  return (
    <form action={formAction} className={compact ? "" : "mt-4"}>
      <input type="hidden" name="run_id" value={runId} />
      <button
        type="submit"
        disabled={pending}
        className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Creating comparison..." : "Compare This Run"}
      </button>
      {!compact && (
        <p className="mt-2 text-xs text-muted-foreground">
          Reuses this completed run. If the counterpart does not exist yet, only
          the missing baseline or multi-agent side is created.
        </p>
      )}
      {state.error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
    </form>
  );
}
