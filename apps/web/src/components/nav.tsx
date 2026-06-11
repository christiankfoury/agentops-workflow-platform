import Link from "next/link";

export function Nav() {
  return (
    <header className="border-b border-border bg-background">
      <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          AgentOps
        </Link>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <Link
            href="/workflow-runs"
            className="transition-colors hover:text-foreground"
          >
            Workflow Runs
          </Link>
          <Link
            href="/workflow-runs/new"
            className="transition-colors hover:text-foreground"
          >
            New Workflow
          </Link>
          <Link
            href="/human-approvals"
            className="transition-colors hover:text-foreground"
          >
            Approvals
          </Link>
          <Link
            href="/costs"
            className="transition-colors hover:text-foreground"
          >
            Costs
          </Link>
          <Link
            href="/evaluation"
            className="transition-colors hover:text-foreground"
          >
            Evaluation
          </Link>
          <Link
            href="/prompt-versions"
            className="transition-colors hover:text-foreground"
          >
            Prompts
          </Link>
        </div>
      </nav>
    </header>
  );
}
