"use client";

import { useState } from "react";
import { PromptVersionForm } from "./form";

export function CreatePromptVersionModal() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-90"
      >
        Create Prompt Version
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/45 px-4 py-8"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-prompt-version-title"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-4xl rounded-lg border border-border bg-background p-5 shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 id="create-prompt-version-title" className="text-xl font-semibold">
                  Create Prompt Version
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Choose the agent, add the template, and optionally activate it for future runs.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-fit rounded-md border border-border px-3 py-2 text-sm font-medium"
                aria-label="Close create prompt version modal"
              >
                Close
              </button>
            </div>
            <PromptVersionForm />
          </div>
        </div>
      ) : null}
    </>
  );
}
