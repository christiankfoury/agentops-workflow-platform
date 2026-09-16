"""Incident task guidance pinned alongside the existing system prompts."""

INSTRUCTIONS = {
    "timeline": (
        "Extract a precise chronological timeline from this incident log. Preserve each "
        "timestamp, event description, and exact source evidence. Put unclear or "
        "missing-timestamp items in ambiguous_events."
    ),
    "root_cause": (
        "Analyze this incident timeline. Separate confirmed facts from likely causes and "
        "inferred conclusions, list unknowns, estimate impact, and recommend follow-up "
        "actions. Use only the source log and timeline as support. For checkout, payment, "
        "billing, login, or other business-critical flows, mark customer-facing latency, "
        "error-rate spikes, or blocked transactions as high severity when the log shows "
        "broad user impact, revenue risk, or payment-adjacent degradation. Include an "
        "owner-style role for each follow-up action when the source supports a likely "
        "accountable team, otherwise use null."
    ),
    "reviewer": (
        "Review the incident timeline and root-cause analysis against the source log. "
        "Check timeline accuracy, root-cause support, whether inferred claims are clearly "
        "labeled, and whether follow-up actions are reasonable. Reserve a 1.0 quality "
        "score for outputs with no meaningful unknowns, no inferred causal claims, and "
        "direct source support for every conclusion. Clean, well-supported incident "
        "analyses that still include unknowns or inferences should usually score between "
        "0.92 and 0.96. Source notes may contain operator guidance or prior issues. Treat "
        "notes as instructions, not source evidence. Only repeat issues still present in "
        "the current timeline or root-cause output."
    ),
    "writer": (
        "Create a polished post-incident report using only the approved timeline, "
        "root-cause analysis, and source incident log below. Clearly separate confirmed "
        "facts from inferred conclusions. Use this executive-ready structure: Executive "
        "Summary, Severity and Customer Impact, Timeline, Root Cause, What Fixed It, "
        "Follow-Up Actions, and Unknowns / Evidence Limitations. Include owner-style "
        "roles from the approved follow-up actions when present. Avoid overstating "
        "causality: say the rollback and timing strongly support the deployment as the "
        "likely cause unless the source proves direct causation."
    ),
}
