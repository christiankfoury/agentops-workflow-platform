"""Pinned task guidance preserved from the existing feedback agents."""

INSTRUCTIONS = {
    "reviewer": (
        "Review the Customer Feedback Insight Agent output against the source feedback. "
        "Check whether insights, risks, feature requests, and recommendations are supported "
        "by actual feedback examples. Return structured JSON with explicit passed checks, "
        "approval rationale, approval, quality score, issues, and retry recommendation. "
        "Include checks for evidence support, missing important feedback, priority/severity "
        "accuracy, recommendation evidence, and unsupported inference. Approved means "
        "factually supported by the source feedback, not business-perfect.  Source notes "
        "may include operator guidance or prior reviewer issues. Treat notes as "
        "instructions, not source evidence. Do not repeat old issues unless still present "
        "in the current output."
    ),
    "writer": (
        "Create a polished product insights report using only the approved customer "
        "feedback insights and source feedback below. Format the report as an "
        "executive-ready artifact with these sections in order: Executive Summary, Priority Table, "
        "Evidence-Backed Recommendations, Suggested Next Actions, Sample-Size Caveat, and "
        "Supporting Evidence. The Priority Table must separate feature requests by urgency "
        "when present: SSO as Enterprise blocker, CSV export as Reporting workflow need, "
        "and shared lists as Collaboration improvement. Clearly distinguish urgent bugs "
        "from strategic feature requests. Mention that the report was generated from "
        "human-approved analysis. Do not introduce claims that are not supported by the source "
        "feedback."
    ),
    "classifier": (
        "Classify this customer feedback and return structured JSON. Use bugs only for "
        "product defects such as crashes, freezes, broken flows, errors, or failed uploads. "
        "Classify noisy notifications, confusing settings, or hard-to-configure behavior as "
        "usability unless the feedback describes a concrete defect."
    ),
    "insight": (
        "Turn this classified customer feedback into product insights. Use only the source "
        "feedback and classifier output as support."
    ),
}
