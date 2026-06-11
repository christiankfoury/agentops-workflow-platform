import { NewWorkflowForm } from "./form";

export default function NewWorkflowPage() {
  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">New Sales Workflow</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Store a sales report input for the upcoming agent pipeline.
      </p>

      <NewWorkflowForm />
    </div>
  );
}
