"use client";

import { useActionState } from "react";
import { createEvaluationComparisonAction } from "./actions";

const initialState = { error: null };

export function CreateEvaluationComparisonForm({ runId }: { runId: string }) {
  const [state, formAction, pending] = useActionState(
    createEvaluationComparisonAction,
    initialState,
  );

  return (
    <form action={formAction} className="mt-4">
      <input type="hidden" name="run_id" value={runId} />
      <button
        type="submit"
        disabled={pending}
        className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Creating comparison..." : "Create Evaluation Comparison"}
      </button>
      {state.error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
    </form>
  );
}
