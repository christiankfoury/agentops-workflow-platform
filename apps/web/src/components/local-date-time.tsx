"use client";

import { useMemo } from "react";

function parseApiDateTime(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

function formatApiDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(parseApiDateTime(value));
}

export function LocalDateTime({ value }: { value: string | null }) {
  const formatted = useMemo(
    () => (value ? formatApiDateTime(value) : "-"),
    [value],
  );

  if (!value) return <span>-</span>;

  return (
    <time dateTime={value} suppressHydrationWarning>
      {formatted}
    </time>
  );
}
