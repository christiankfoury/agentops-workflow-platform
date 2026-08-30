"use client";

import {
  BarChart3,
  Bot,
  CheckCircle2,
  CircleDollarSign,
  FileText,
  GitCompare,
  GitBranch,
  Home,
  PanelLeftClose,
  PanelLeftOpen,
  PlayCircle,
  Plus,
  Settings,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
};

const primaryItems: NavItem[] = [
  { href: "/", label: "Dashboard", icon: Home, exact: true },
  { href: "/workflow-runs", label: "Runs", icon: GitBranch },
  { href: "/human-approvals", label: "Approvals", icon: CheckCircle2 },
  { href: "/workflow-comparison", label: "Compare", icon: GitCompare },
];

const insightItems: NavItem[] = [
  { href: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { href: "/costs", label: "Costs", icon: CircleDollarSign },
  { href: "/agent-performance", label: "Agents", icon: Bot },
  { href: "/failures", label: "Failures", icon: TriangleAlert },
  { href: "/improvements", label: "Trends", icon: TrendingUp },
];

const adminItems: NavItem[] = [
  { href: "/prompt-versions", label: "Prompts", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

const allItems = [...primaryItems, ...insightItems, ...adminItems];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavLink({
  collapsed,
  item,
  pathname,
}: {
  collapsed: boolean;
  item: NavItem;
  pathname: string;
}) {
  const Icon = item.icon;
  const active = isActive(pathname, item);

  return (
    <Link
      href={item.href}
      className={
        active
          ? `relative flex h-10 items-center gap-3 overflow-hidden rounded-xl bg-blue-50 text-sm font-semibold text-blue-700 transition-[padding] duration-200 dark:bg-blue-950/45 dark:text-blue-200 ${collapsed ? "px-3" : "px-3.5"}`
          : `flex h-10 items-center gap-3 overflow-hidden rounded-xl text-sm font-medium text-muted-foreground transition-[padding] duration-200 hover:bg-accent hover:text-foreground ${collapsed ? "px-3" : "px-3.5"}`
      }
      title={collapsed ? item.label : undefined}
    >
      {active ? (
        <span className="absolute -left-3 top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-full bg-blue-600" />
      ) : null}
      <span className="flex w-4 shrink-0 justify-center">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <span
        className={
          collapsed
            ? "max-w-0 truncate opacity-0 transition-[max-width,opacity] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
            : "max-w-36 truncate opacity-100 transition-[max-width,opacity] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
        }
      >
        {item.label}
      </span>
    </Link>
  );
}

function NavSection({
  collapsed,
  items,
  pathname,
  title,
}: {
  collapsed: boolean;
  items: NavItem[];
  pathname: string;
  title: string;
}) {
  return (
    <div>
      <p
        className={
          collapsed
            ? "mb-1.5 h-5 overflow-hidden px-3.5 text-[11px] font-bold uppercase tracking-wide text-foreground/65 opacity-0 transition-opacity duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
            : "mb-1.5 h-5 overflow-hidden px-3.5 text-[11px] font-bold uppercase tracking-wide text-foreground/65 opacity-100 transition-opacity duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
        }
      >
        {title}
      </p>
      <div className="space-y-0.5">
        {items.map((item) => (
          <NavLink
            key={item.href}
            collapsed={collapsed}
            item={item}
            pathname={pathname}
          />
        ))}
      </div>
    </div>
  );
}

function NewWorkflowButton() {
  return (
    <Link
      href="/workflow-runs/new"
      className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-95"
    >
      <Plus className="h-4 w-4" aria-hidden="true" />
      New Workflow
    </Link>
  );
}

export function Nav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const storedSidebar = window.localStorage.getItem("agentops-sidebar");
    const nextCollapsed = storedSidebar === "collapsed";
    // Hydrate the browser-only preference after mount to keep server markup deterministic.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCollapsed(nextCollapsed);
    document.documentElement.dataset.sidebar = nextCollapsed ? "collapsed" : "expanded";
  }, []);

  function toggleSidebar() {
    const nextCollapsed = !collapsed;
    setCollapsed(nextCollapsed);
    document.documentElement.dataset.sidebar = nextCollapsed ? "collapsed" : "expanded";
    window.localStorage.setItem(
      "agentops-sidebar",
      nextCollapsed ? "collapsed" : "expanded",
    );
  }
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[var(--sidebar-width)] border-r border-border bg-card transition-[width] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)] md:flex md:flex-col">
        <div className="relative flex h-20 items-center px-6">
          <Link
            href="/"
            aria-label="AgentOps dashboard"
            className="relative flex h-10 w-full min-w-0 items-center font-semibold tracking-tight"
          >
            <span
              className={
                collapsed
                  ? "max-w-0 overflow-hidden text-3xl opacity-0 transition-[max-width,opacity] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
                  : "max-w-40 overflow-hidden text-3xl opacity-100 transition-[max-width,opacity] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)]"
              }
            >
              AgentOps
            </span>
            <span
              aria-hidden="true"
              className={
                collapsed
                  ? "absolute left-1/2 -translate-x-1/2 text-xl opacity-100 transition-opacity delay-200 duration-100 ease-out"
                  : "absolute left-1/2 -translate-x-1/2 text-xl opacity-0 transition-opacity duration-75 ease-out"
              }
          >
            AO
          </span>
        </Link>
        </div>

        <nav className="flex flex-1 flex-col px-3.5 py-4">
          <div className="space-y-6">
            <NavSection
              collapsed={collapsed}
              title="Workflow"
              items={primaryItems}
              pathname={pathname}
            />
            <NavSection
              collapsed={collapsed}
              title="Insights"
              items={insightItems}
              pathname={pathname}
            />
            <NavSection
              collapsed={collapsed}
              title="Admin"
              items={adminItems}
              pathname={pathname}
            />
          </div>
          <button
            type="button"
            aria-label={collapsed ? "Open sidebar" : "Close sidebar"}
            title={collapsed ? "Open sidebar" : undefined}
            onClick={toggleSidebar}
            className={`mt-auto flex h-10 w-full items-center gap-3 overflow-hidden rounded-xl text-sm font-medium text-muted-foreground transition-[padding] duration-200 hover:bg-accent hover:text-foreground ${collapsed ? "px-3" : "px-3.5"}`}
          >
            <span className="relative flex h-4 w-4 shrink-0 items-center justify-center">
              <PanelLeftClose
                className={
                  collapsed
                    ? "absolute h-4 w-4 opacity-0 transition-opacity duration-200"
                    : "absolute h-4 w-4 opacity-100 transition-opacity duration-200"
                }
                aria-hidden="true"
              />
              <PanelLeftOpen
                className={
                  collapsed
                    ? "absolute h-4 w-4 opacity-100 transition-opacity duration-200"
                    : "absolute h-4 w-4 opacity-0 transition-opacity duration-200"
                }
                aria-hidden="true"
              />
            </span>
            <span
              className={
                collapsed
                  ? "max-w-0 truncate opacity-0 transition-[max-width,opacity] duration-200"
                  : "max-w-36 truncate opacity-100 transition-[max-width,opacity] duration-200"
              }
            >
              Collapse sidebar
            </span>
          </button>
        </nav>
      </aside>

      <header className="fixed left-0 right-0 top-0 z-10 hidden h-20 items-center justify-end border-b border-border bg-card/95 px-8 backdrop-blur-xl transition-[left] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)] md:left-[var(--sidebar-width)] md:flex">
        <div className="flex items-center gap-3">
          <Link
            href="/demo"
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-background px-4 text-sm font-semibold text-foreground shadow-sm hover:bg-accent"
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" />
            Demo
          </Link>
          <NewWorkflowButton />
          <ThemeToggle />
        </div>
      </header>

      <header className="sticky top-0 z-20 border-b border-border bg-card/95 px-3 py-3 shadow-sm backdrop-blur-xl md:hidden">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="flex min-w-0 items-center gap-2 font-semibold">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              AO
            </span>
            <span className="truncate">AgentOps</span>
          </Link>
          <div className="flex shrink-0 items-center gap-2">
            <ThemeToggle />
            <NewWorkflowButton />
          </div>
        </div>
        <nav className="-mx-3 mt-3 flex gap-1 overflow-x-auto px-3 pb-1">
          {allItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  active
                    ? "inline-flex shrink-0 items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 dark:bg-blue-950/45 dark:text-blue-200"
                    : "inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
    </>
  );
}
