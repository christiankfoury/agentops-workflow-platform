import Link from "next/link";
import { getEvaluationComparisons } from "@/lib/api";
import type { EvaluationComparison } from "@/lib/types";
import { WorkflowComparisonExplorer } from "./workflow-comparison-explorer";

function ActionLinks() {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      <Link
        href="/demo"
        className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
      >
        Open Demo Mode
      </Link>
      <Link
        href="/evaluation"
        className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
      >
        Evaluation Dashboard
      </Link>
    </div>
  );
}

export default async function WorkflowComparisonPage({
  searchParams,
}: {
  searchParams?: Promise<{ search?: string | string[] }>;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const initialSearch =
    typeof resolvedSearchParams.search === "string"
      ? resolvedSearchParams.search
      : "";
  let comparisons: EvaluationComparison[] = [];
  let apiError = false;

  try {
    comparisons = await getEvaluationComparisons();
  } catch {
    apiError = true;
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Workflow Comparison
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Compact baseline vs multi-agent comparisons for matched evaluation inputs.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/demo"
            className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
          >
            Demo Mode
          </Link>
          <Link
            href="/evaluation"
            className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
          >
            Evaluation Dashboard
          </Link>
        </div>
      </div>

      {apiError && (
        <section className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          <h2 className="font-semibold">Workflow comparison data is unavailable.</h2>
          <p className="mt-1">
            The API did not respond, so paired baseline and multi-agent runs could
            not be loaded.
          </p>
          <ActionLinks />
        </section>
      )}

      {!apiError && comparisons.length === 0 ? (
        <section className="mt-6 rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          <h2 className="font-semibold text-foreground">
            No paired comparison runs yet.
          </h2>
          <p className="mt-1">
            Seed demo workflows or run evaluations to populate baseline and
            multi-agent comparisons.
          </p>
          <ActionLinks />
        </section>
      ) : (
        comparisons.length > 0 && (
          <WorkflowComparisonExplorer
            comparisons={comparisons}
            initialSearch={initialSearch}
          />
        )
      )}
    </div>
  );
}
