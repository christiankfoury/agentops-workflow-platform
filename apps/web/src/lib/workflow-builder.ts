export type ObjectValue = Record<string, unknown>;
export type DraftDefinition = {
  id: string; organization_id: string; name: string; description: string;
  draft_graph: ObjectValue; draft_revision: number; archived: boolean;
  published_version_id: string | null;
};
export type DraftBody = { name: string; description: string; graph: ObjectValue; expected_revision?: number };
export type DraftResult = { definition?: DraftDefinition; error?: string; fields?: string[] };
export type CatalogItem = { id: string; name: string };
export const nodeTypes = ["llm", "code", "tool", "condition", "approval", "transform", "parallel", "delay"] as const;
export type NodeType = typeof nodeTypes[number];
export type GraphNode = ObjectValue & { id: string; type: NodeType; config: ObjectValue };
export type GraphEdge = { source: string; target: string; label?: string | null };
export type EditableGraph = ObjectValue & { nodes: GraphNode[]; edges: GraphEdge[] };
export const objectSchema = { type: "object" };
export function isObject(value: unknown): value is ObjectValue {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
export function editableGraph(graph: ObjectValue): graph is EditableGraph {
  return Array.isArray(graph.nodes) && graph.nodes.every(n => isObject(n) && typeof n.id === "string"
    && nodeTypes.includes(n.type as NodeType) && isObject(n.config))
    && new Set(graph.nodes.map(n => (n as GraphNode).id)).size === graph.nodes.length
    && Array.isArray(graph.edges) && graph.edges.every(e => isObject(e)
      && typeof e.source === "string" && typeof e.target === "string"
      && (e.label == null || typeof e.label === "string"));
}
export function newNode(type: NodeType, id: string): GraphNode {
  const configs: Record<NodeType, ObjectValue> = {
    llm: { prompt_version_id: "", model: "", max_tokens: 2048 },
    code: { handler: "builtin.identity", version: 1 },
    tool: { tool_id: "", version: 1, adapter: "http" },
    condition: { cases: [{ label: "match", when: { op: "literal", value: true } }], default: "default" },
    approval: { reviewer_roles: ["reviewer", "admin"], max_review_retries: 2, timeout_action: "fail" },
    transform: { assign: {} }, parallel: { mode: "fork", branches: [], join_node: "" }, delay: { seconds: 1 },
  };
  return { id, type, config: configs[type], input_schema: objectSchema, output_schema: objectSchema, inputs: {}, timeout_seconds: 60 };
}
export function starterGraph(): EditableGraph {
  const node = newNode("transform", "message");
  node.config.assign = { text: { op: "literal", value: "Ready" } };
  node.output_schema = { type: "object", properties: { text: { type: "string" } }, required: ["text"] };
  return { schema_version: 1, entry_node: node.id, input_schema: objectSchema,
    output_schema: node.output_schema, outputs: { text: { op: "ref", ref: { source: "node", node_id: node.id, path: ["text"] } } },
    nodes: [node], edges: [], overall_timeout_seconds: 86400 };
}
// Drafts may be incomplete. These authoring diagnostics do not claim runtime validation.
export function draftIssues(graph: ObjectValue): string[] {
  if (!editableGraph(graph)) return ["Graph structure is incomplete or unsupported. Repair it in Graph JSON."];
  const issues: string[] = [], ids = new Set(graph.nodes.map(n => n.id));
  if (!ids.has(String(graph.entry_node))) issues.push("Graph · entry_node: select an existing node.");
  if (graph.nodes.length > 100) issues.push("Graph · nodes: use at most 100 nodes.");
  const links = new Set<string>();
  for (const e of graph.edges) {
    const key = JSON.stringify([e.source, e.target, e.label ?? null]);
    if (links.has(key)) issues.push(`Edges · ${e.source} → ${e.target}: duplicate connection.`);
    links.add(key);
    if (!ids.has(e.source) || !ids.has(e.target)) issues.push(`Edges · ${e.source} → ${e.target}: endpoint is missing.`);
    if (e.source === e.target) issues.push(`Edges · ${e.source}: self connections are not allowed.`);
  }
  const active = new Set<string>(), seen = new Set<string>();
  const edges = graph.edges;
  function visit(id: string): boolean {
    if (active.has(id)) return true;
    if (seen.has(id)) return false;
    seen.add(id); active.add(id);
    const cycle = edges.some(e => e.source === id && ids.has(e.target) && visit(e.target));
    active.delete(id); return cycle;
  }
  if (graph.nodes.some(n => visit(n.id))) issues.push("Edges · cycle: remove the back edge; use bounded quality revision settings for review loops.");
  for (const n of graph.nodes) {
    const problem = (field: string, message: string) => issues.push(`${n.id} · ${field}: ${message}`);
    const bounded = (field: string, value: unknown, min: number, max: number, integer = false) => {
      if (value != null && (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value)))) problem(field, `use ${integer ? "an integer" : "a number"} from ${min} to ${max}.`);
    };
    bounded("timeout_seconds", n.timeout_seconds, 0.001, 3600);
    for (const key of ["inputs", "input_schema", "output_schema", "retry"]) {
      if (n[key] != null && !isObject(n[key])) problem(key, "enter a JSON object.");
    }
    if (isObject(n.retry)) bounded("retry.max_attempts", n.retry.max_attempts, 1, 10, true);
    if (n.type === "code" || n.type === "tool") bounded("version", n.config.version, 1, Number.MAX_SAFE_INTEGER, true);
    if (n.type === "transform" && !isObject(n.config.assign)) problem("assign", "enter an object mapping output fields to expressions.");
    if (n.type === "condition" && (!Array.isArray(n.config.cases) || !n.config.cases.length || n.config.cases.length > 8)) problem("cases", "enter 1–8 labeled conditions.");
    if (n.type === "approval") {
      bounded("max_review_retries", n.config.max_review_retries, 0, 5, true);
      if (!Array.isArray(n.config.reviewer_roles) || !n.config.reviewer_roles.length || n.config.reviewer_roles.some(r => r !== "admin" && r !== "reviewer")) problem("reviewer_roles", "choose reviewer, admin, or both.");
    }
    if (n.type === "llm") {
      bounded("max_tokens", n.config.max_tokens, 1, 32768, true);
      bounded("max_cost_usd", n.config.max_cost_usd, 0.000001, 100);
      bounded("max_tool_calls", n.config.max_tool_calls, 1, 32, true);
    }
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(n.id)) issues.push(`${n.id} · id: use a letter followed by up to 63 letters, digits, underscores or hyphens.`);
    for (const key of n.type === "llm" ? ["prompt_version_id", "model"] : n.type === "tool" ? ["tool_id"] : []) {
      if (!n.config[key]) issues.push(`${n.id} · ${key}: choose a value.`);
    }
    if (n.type === "parallel" && n.config.mode === "fork" && (!Array.isArray(n.config.branches) || n.config.branches.length < 2)) issues.push(`${n.id} · branches: a fork needs at least two named branches.`);
    if (n.type === "delay" && (n.config.seconds == null) === (n.config.wake_at == null)) issues.push(`${n.id} · delay: set exactly one duration or wake time.`);
    if (n.type === "delay") {
      bounded("seconds", n.config.seconds, 0, 604800);
      if (n.config.wake_at != null && (typeof n.config.wake_at !== "string" || !/(Z|[+-]\d\d:\d\d)$/.test(n.config.wake_at) || !Number.isFinite(Date.parse(n.config.wake_at)))) problem("wake_at", "enter an ISO timestamp including its UTC offset.");
    }
    if (n.type === "parallel") for (const key of n.config.mode === "join" ? ["fork_node"] : ["join_node"]) {
      if (!ids.has(String(n.config[key]))) problem(key, "select an existing node.");
    }
  }
  function references(value: unknown, depth = 0) {
    if (depth > 32) { issues.push("Graph · nesting exceeds 32 levels."); return; }
    if (Array.isArray(value)) value.forEach(v => references(v, depth + 1));
    else if (isObject(value)) {
      if (value.source === "node" && !ids.has(String(value.node_id))) issues.push(`Bindings · ${String(value.node_id)}: referenced node is missing.`);
      Object.values(value).forEach(v => references(v, depth + 1));
    }
  }
  references(graph);
  return [...new Set(issues)];
}
