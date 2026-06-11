import { existsSync } from "node:fs";

interface ResolveApiBaseUrlOptions {
  apiInternalUrl?: string;
  publicApiUrl?: string;
  isContainer?: boolean;
}

const defaultApiUrl = "http://localhost:8000";

function isDockerServiceUrl(value: string): boolean {
  try {
    return new URL(value).hostname === "api";
  } catch {
    return false;
  }
}

function isRunningInContainer(): boolean {
  return existsSync("/.dockerenv");
}

export function resolveApiBaseUrl({
  apiInternalUrl = process.env.API_INTERNAL_URL,
  publicApiUrl = process.env.NEXT_PUBLIC_API_URL,
  isContainer = isRunningInContainer(),
}: ResolveApiBaseUrlOptions = {}): string {
  if (apiInternalUrl) {
    if (isDockerServiceUrl(apiInternalUrl) && !isContainer) {
      return publicApiUrl ?? defaultApiUrl;
    }

    return apiInternalUrl;
  }

  return publicApiUrl ?? defaultApiUrl;
}

export function apiUrl(path: string): string {
  return `${resolveApiBaseUrl()}${path}`;
}
