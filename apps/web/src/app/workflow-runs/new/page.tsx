import { NewWorkflowForm } from "./form";

export default function NewWorkflowPage() {
  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">New Workflow</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Store an input and start a workflow run.
      </p>

      <NewWorkflowForm />
    </div>
  );
}
