"use client";

import { useEffect, useState } from "react";

function parseApiDateTime(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

export function LocalDateTime({ value }: { value: string | null }) {
  const [formatted, setFormatted] = useState<string | null>(null);

  useEffect(() => {
    if (!value) {
      setFormatted("-");
      return;
    }
    setFormatted(
      new Intl.DateTimeFormat(undefined, {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(parseApiDateTime(value)),
    );
  }, [value]);

  if (!value) return <span>-</span>;

  return (
    <time dateTime={value} suppressHydrationWarning>
      {formatted ?? "..."}
    </time>
  );
}
