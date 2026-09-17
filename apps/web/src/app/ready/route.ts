import { apiUrl } from "@/lib/api-url";

export const dynamic = "force-dynamic";
export async function GET() {
  try {
    const response = await fetch(apiUrl("/ready"), {
      cache: "no-store", signal: AbortSignal.timeout(3000),
    });
    if (response.ok) return Response.json({ status: "ready" });
  } catch { /* A dependency failure removes this instance from service. */ }
  return Response.json({ status: "unavailable" }, { status: 503 });
}
