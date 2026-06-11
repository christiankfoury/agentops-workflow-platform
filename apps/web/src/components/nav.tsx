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
            href="/demo"
            className="transition-colors hover:text-foreground"
          >
            Demo
          </Link>
          <Link
            href="/agent-performance"
            className="transition-colors hover:text-foreground"
          >
            Agents
          </Link>
          <Link
            href="/workflow-comparison"
            className="transition-colors hover:text-foreground"
          >
            Compare
          </Link>
          <Link
            href="/failures"
            className="transition-colors hover:text-foreground"
          >
            Failures
          </Link>
          <Link
            href="/improvements"
            className="transition-colors hover:text-foreground"
          >
            Trends
          </Link>
          <Link
            href="/prompt-versions"
            className="transition-colors hover:text-foreground"
          >
            Prompts
          </Link>
          <Link
            href="/settings"
            className="transition-colors hover:text-foreground"
          >
            Settings
          </Link>
        </div>
      </nav>
    </header>
  );
}
