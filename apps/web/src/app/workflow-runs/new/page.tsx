import { NewWorkflowForm } from "./form";

const workflowExamples = [
  {
    title: "Sales Report",
    body: "Revenue updates, pipeline notes, churn risks, and regional performance.",
  },
  {
    title: "Customer Feedback",
    body: "Reviews, support tickets, NPS comments, feature requests, and CSV exports.",
  },
  {
    title: "Incident Log",
    body: "Timestamped events, impact notes, mitigations, and follow-up actions.",
  },
];

export default function NewWorkflowPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-col gap-3 border-b border-border pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Workflow intake
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">
            New Workflow
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Add a business input, choose the workflow path, and launch either a
            multi-agent run or a single-agent baseline for comparison.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm sm:flex">
          <span className="rounded-md border border-border bg-muted px-3 py-2">
            Analyst
          </span>
          <span className="rounded-md border border-border bg-muted px-3 py-2">
            Reviewer
          </span>
          <span className="rounded-md border border-border bg-muted px-3 py-2">
            Approval
          </span>
          <span className="rounded-md border border-border bg-muted px-3 py-2">
            Writer
          </span>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
        <NewWorkflowForm />

        <aside className="space-y-4 lg:sticky lg:top-28">
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-base font-semibold">Supported inputs</h2>
            <div className="mt-4 space-y-4">
              {workflowExamples.map((example) => (
                <div key={example.title} className="border-l-2 border-border pl-3">
                  <p className="text-sm font-medium">{example.title}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    {example.body}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-base font-semibold">Run mode choice</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="font-medium">Multi-Agent</dt>
                <dd className="mt-1 leading-6 text-muted-foreground">
                  Routes through the analyst, reviewer, approval, and writer
                  path for traceable output.
                </dd>
              </div>
              <div>
                <dt className="font-medium">Baseline</dt>
                <dd className="mt-1 leading-6 text-muted-foreground">
                  Creates the single-agent comparison side for the same input.
                </dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>
    </div>
  );
}
