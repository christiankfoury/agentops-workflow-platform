import { BarChart3, Cog, GitBranch, PlusCircle, PlayCircle } from "lucide-react";
import Link from "next/link";

export function Nav() {
  const topActions = [
    { href: "/demo", label: "Demo", icon: PlayCircle },
    { href: "/workflow-runs/new", label: "New Workflow", icon: PlusCircle },
  ];
  const navGroups = [
    {
      label: "Workflow",
      icon: GitBranch,
      links: [
        { href: "/workflow-runs", label: "Runs" },
        { href: "/human-approvals", label: "Approvals" },
        { href: "/workflow-comparison", label: "Compare" },
      ],
    },
    {
      label: "Insights",
      icon: BarChart3,
      links: [
        { href: "/evaluation", label: "Evaluation" },
        { href: "/costs", label: "Costs" },
        { href: "/agent-performance", label: "Agents" },
        { href: "/failures", label: "Failures" },
        { href: "/improvements", label: "Trends" },
      ],
    },
    {
      label: "Admin",
      icon: Cog,
      links: [
        { href: "/prompt-versions", label: "Prompts" },
        { href: "/settings", label: "Settings" },
      ],
    },
  ];

  return (
    <header className="sticky top-0 z-10 border-b border-border/80 bg-background/90 shadow-sm backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-3">
          <Link
            href="/"
            className="flex w-fit shrink-0 items-center gap-2 text-sm font-semibold tracking-tight"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground shadow-sm">
              AO
            </span>
            <span>AgentOps Workflow Platform</span>
          </Link>
          <div className="flex shrink-0 items-center gap-2 text-sm">
            {topActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.href}
                  href={action.href}
                  className={
                    index === 0
                      ? "hidden items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 font-medium text-foreground shadow-sm hover:border-primary/35 hover:bg-accent sm:inline-flex"
                      : "inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 font-medium text-primary-foreground hover:opacity-90"
                  }
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {action.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 text-sm lg:grid-cols-[1.15fr_1.45fr_1fr]">
          <Link
            href={topActions[0].href}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border/80 bg-card/80 px-3 py-2 font-medium text-foreground shadow-sm hover:border-primary/35 hover:bg-accent sm:hidden"
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" />
            {topActions[0].label}
          </Link>
          {navGroups.map((group) => {
            const Icon = group.icon;
            return (
              <div
                key={group.label}
                className="flex min-w-0 items-center gap-1.5 rounded-lg border border-border/80 bg-card/80 p-1 shadow-sm"
              >
                <div className="flex min-w-0 items-center gap-1">
                  {group.links.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="whitespace-nowrap rounded-md px-2.5 py-1.5 font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
                <span className="ml-auto flex shrink-0 items-center gap-1.5 px-2 text-[11px] font-semibold uppercase text-primary/80">
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {group.label}
                </span>
              </div>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
