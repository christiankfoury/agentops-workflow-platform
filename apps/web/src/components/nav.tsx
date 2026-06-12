import Link from "next/link";

export function Nav() {
  const primaryLinks = [
    { href: "/demo", label: "Demo" },
    { href: "/workflow-runs", label: "Runs" },
    { href: "/workflow-runs/new", label: "New" },
    { href: "/human-approvals", label: "Approvals" },
    { href: "/evaluation", label: "Evaluation" },
    { href: "/workflow-comparison", label: "Compare" },
  ];
  const secondaryLinks = [
    { href: "/costs", label: "Costs" },
    { href: "/agent-performance", label: "Agents" },
    { href: "/failures", label: "Failures" },
    { href: "/improvements", label: "Trends" },
    { href: "/prompt-versions", label: "Prompts" },
    { href: "/settings", label: "Settings" },
  ];

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="w-fit text-sm font-semibold tracking-tight">
          AgentOps Workflow Platform
        </Link>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {primaryLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md border border-border px-2.5 py-1 text-foreground transition-colors hover:bg-accent"
            >
              {link.label}
            </Link>
          ))}
          <span className="hidden h-5 w-px bg-border sm:block" />
          {secondaryLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-2.5 py-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
