"use client";

import { XCircle } from "lucide-react";
import { useActionState } from "react";
import { cancelWorkflowAction } from "./actions";

const initialState = { error: null };

export function CancelWorkflowForm({ runId }: { runId: string }) {
  const [state, formAction, pending] = useActionState(
    cancelWorkflowAction,
    initialState,
  );

  return (
    <form action={formAction} className="mt-4">
      <input type="hidden" name="run_id" value={runId} />
      {state.error && (
        <p className="mb-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="inline-flex items-center gap-2 rounded-md border border-destructive/30 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <XCircle className="h-4 w-4" aria-hidden="true" />
        {pending ? "Cancelling..." : "Cancel Workflow"}
      </button>
    </form>
  );
}
