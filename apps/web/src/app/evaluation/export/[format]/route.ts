import { fetchEvaluationExport } from "@/lib/api";

export async function GET(_request: Request, context: { params: Promise<{ format: string }> }) {
  const { format } = await context.params;
  if (format !== "csv" && format !== "json" && format !== "markdown") {
    return new Response("Unknown export format", { status: 404 });
  }
  const result = await fetchEvaluationExport(format);
  if (!result.ok) return new Response("Export unavailable", { status: result.status });
  return new Response(result.body, { headers: {
    "Content-Type": result.headers.get("content-type") ?? "application/octet-stream",
    "Content-Disposition": result.headers.get("content-disposition") ?? "attachment",
    "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
  } });
}
