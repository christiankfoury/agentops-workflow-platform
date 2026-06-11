from sqlalchemy.orm import Session

from src.models.evaluation_case import EvaluationCase
from src.models.workflow_run import WorkflowType

DEFAULT_SALES_EVALUATION_CASES = [
    {
        "title": "Q1 regional growth and churn",
        "input_text": (
            "Q1 Sales Report\n"
            "Revenue increased 12% from $4.2M to $4.7M. North America grew 18% "
            "and was the strongest region. EMEA declined 4%. Enterprise churn "
            "increased from 5% to 7%. Analytics Suite was the top product."
        ),
        "expected_facts_json": [
            "Revenue increased 12% from $4.2M to $4.7M",
            "North America grew 18% and was the strongest region",
            "EMEA declined 4%",
            "Enterprise churn increased from 5% to 7%",
            "Analytics Suite was the top product",
        ],
        "expected_risks_json": ["Enterprise churn increased", "EMEA declined"],
        "expected_recommendations_json": [
            "Prioritize enterprise retention",
            "Investigate EMEA performance decline",
        ],
        "expected_output_notes": "Executive summary should not say churn doubled.",
    },
    {
        "title": "Pipeline softness with SMB expansion",
        "input_text": (
            "Q2 Sales Report\n"
            "Total revenue was flat at $5.1M. SMB revenue increased 9%. Enterprise "
            "pipeline coverage fell from 3.2x to 2.4x. The West region missed target "
            "by $300K. Expansion revenue from existing customers increased 14%."
        ),
        "expected_facts_json": [
            "Total revenue was flat at $5.1M",
            "SMB revenue increased 9%",
            "Enterprise pipeline coverage fell from 3.2x to 2.4x",
            "West region missed target by $300K",
            "Expansion revenue increased 14%",
        ],
        "expected_risks_json": [
            "Enterprise pipeline coverage fell",
            "West region missed target",
        ],
        "expected_recommendations_json": [
            "Rebuild enterprise pipeline",
            "Review West region execution",
        ],
        "expected_output_notes": "Summary should separate flat revenue from segment growth.",
    },
    {
        "title": "New product momentum and support load",
        "input_text": (
            "Monthly Sales Report\n"
            "Revenue grew 7% month over month. The new Automation add-on generated "
            "$420K in first-month bookings. Support-related churn risk was noted in "
            "mid-market accounts. APAC grew 11%, while Latin America was unchanged."
        ),
        "expected_facts_json": [
            "Revenue grew 7% month over month",
            "Automation add-on generated $420K in first-month bookings",
            "Support-related churn risk was noted in mid-market accounts",
            "APAC grew 11%",
            "Latin America was unchanged",
        ],
        "expected_risks_json": ["Support-related churn risk in mid-market accounts"],
        "expected_recommendations_json": [
            "Invest in Automation add-on momentum",
            "Address mid-market support issues",
        ],
        "expected_output_notes": "Summary should not invent Latin America decline.",
    },
    {
        "title": "Discounting pressure in enterprise deals",
        "input_text": (
            "Enterprise Sales Update\n"
            "Bookings increased 10%, but average discounting rose from 12% to 19%. "
            "Three large healthcare deals slipped into next quarter. North America "
            "closed 104% of target. Gross retention remained stable at 91%."
        ),
        "expected_facts_json": [
            "Bookings increased 10%",
            "Average discounting rose from 12% to 19%",
            "Three large healthcare deals slipped into next quarter",
            "North America closed 104% of target",
            "Gross retention remained stable at 91%",
        ],
        "expected_risks_json": [
            "Average discounting increased",
            "Healthcare deals slipped into next quarter",
        ],
        "expected_recommendations_json": [
            "Review discount approval discipline",
            "Recover slipped healthcare deals",
        ],
        "expected_output_notes": "Summary should mention margin pressure as a risk.",
    },
    {
        "title": "Renewal strength with product gap",
        "input_text": (
            "Renewals Sales Report\n"
            "Renewal bookings reached $2.3M, 15% above plan. Churn decreased from "
            "6% to 4%. Customers in manufacturing cited missing reporting exports as "
            "a blocker for expansion. The Central region delivered 98% of target."
        ),
        "expected_facts_json": [
            "Renewal bookings reached $2.3M, 15% above plan",
            "Churn decreased from 6% to 4%",
            "Manufacturing customers cited missing reporting exports as expansion blocker",
            "Central region delivered 98% of target",
        ],
        "expected_risks_json": [
            "Missing reporting exports blocked manufacturing expansion",
        ],
        "expected_recommendations_json": [
            "Prioritize reporting export improvements",
            "Use renewal motion as expansion lever",
        ],
        "expected_output_notes": "Summary should not describe churn as increasing.",
    },
    {
        "title": "Channel growth with onboarding drag",
        "input_text": (
            "Channel Sales Report\n"
            "Partner-sourced revenue increased 22% to $1.8M. Direct sales revenue "
            "grew 4%. New reseller onboarding took an average of 41 days, up from "
            "29 days last quarter. The Northeast region exceeded target by 12%. "
            "Attach rate for premium support fell from 33% to 25%."
        ),
        "expected_facts_json": [
            "Partner-sourced revenue increased 22% to $1.8M",
            "Direct sales revenue grew 4%",
            "Reseller onboarding increased from 29 days to 41 days",
            "Northeast region exceeded target by 12%",
            "Premium support attach rate fell from 33% to 25%",
        ],
        "expected_risks_json": [
            "Reseller onboarding slowed",
            "Premium support attach rate declined",
        ],
        "expected_recommendations_json": [
            "Streamline reseller onboarding",
            "Review premium support attach motion",
        ],
        "expected_output_notes": "Summary should not treat all revenue as partner-sourced.",
    },
    {
        "title": "Public sector bookings delayed",
        "input_text": (
            "Public Sector Sales Update\n"
            "Total bookings were $3.4M, 8% below forecast. Two state government "
            "contracts worth $900K moved to legal review. Education segment revenue "
            "grew 16%. Federal pipeline coverage improved from 2.1x to 2.8x. "
            "Average sales cycle lengthened from 74 to 89 days."
        ),
        "expected_facts_json": [
            "Total bookings were $3.4M, 8% below forecast",
            "Two state government contracts worth $900K moved to legal review",
            "Education segment revenue grew 16%",
            "Federal pipeline coverage improved from 2.1x to 2.8x",
            "Average sales cycle lengthened from 74 to 89 days",
        ],
        "expected_risks_json": [
            "Bookings were below forecast",
            "State government contracts moved to legal review",
            "Sales cycle lengthened",
        ],
        "expected_recommendations_json": [
            "Unblock legal review for state contracts",
            "Monitor public sector cycle time",
        ],
        "expected_output_notes": (
            "Summary should separate education growth from total booking miss."
        ),
    },
    {
        "title": "Expansion lift with implementation backlog",
        "input_text": (
            "Expansion Sales Report\n"
            "Expansion ARR increased 19% from existing customers. New logo ARR "
            "declined 6%. Implementation backlog reached 37 active projects, compared "
            "with 24 last month. Financial services expansion contributed $760K. "
            "Customer satisfaction among recently onboarded accounts was 82%."
        ),
        "expected_facts_json": [
            "Expansion ARR increased 19%",
            "New logo ARR declined 6%",
            "Implementation backlog reached 37 active projects, up from 24",
            "Financial services expansion contributed $760K",
            "Recently onboarded customer satisfaction was 82%",
        ],
        "expected_risks_json": [
            "New logo ARR declined",
            "Implementation backlog increased",
        ],
        "expected_recommendations_json": [
            "Add implementation capacity",
            "Rebuild new logo demand generation",
        ],
        "expected_output_notes": (
            "Summary should not describe satisfaction as poor without context."
        ),
    },
    {
        "title": "Healthcare win rate falls despite pipeline",
        "input_text": (
            "Healthcare Sales Snapshot\n"
            "Healthcare pipeline grew 31% quarter over quarter. Win rate fell from "
            "28% to 21%. Competitor displacement deals generated $510K. Security "
            "questionnaire delays were cited in five lost opportunities. South region "
            "bookings finished 5% above plan."
        ),
        "expected_facts_json": [
            "Healthcare pipeline grew 31%",
            "Win rate fell from 28% to 21%",
            "Competitor displacement deals generated $510K",
            "Security questionnaire delays were cited in five lost opportunities",
            "South region bookings finished 5% above plan",
        ],
        "expected_risks_json": [
            "Healthcare win rate declined",
            "Security questionnaire delays contributed to lost opportunities",
        ],
        "expected_recommendations_json": [
            "Improve security questionnaire turnaround",
            "Analyze healthcare win-rate decline",
        ],
        "expected_output_notes": "Summary should not infer pipeline growth caused higher bookings.",
    },
    {
        "title": "Usage-based pricing adoption",
        "input_text": (
            "Usage Pricing Sales Report\n"
            "Forty-two customers moved to usage-based pricing. Net revenue retention "
            "rose from 108% to 114%. Three large accounts requested spend guardrails "
            "before expanding. Self-serve upgrades increased 26%. EMEA enterprise "
            "renewals were flat at $1.1M."
        ),
        "expected_facts_json": [
            "Forty-two customers moved to usage-based pricing",
            "Net revenue retention rose from 108% to 114%",
            "Three large accounts requested spend guardrails before expanding",
            "Self-serve upgrades increased 26%",
            "EMEA enterprise renewals were flat at $1.1M",
        ],
        "expected_risks_json": [
            "Large accounts requested spend guardrails before expanding",
            "EMEA enterprise renewals were flat",
        ],
        "expected_recommendations_json": [
            "Add spend guardrails for usage-based pricing",
            "Investigate flat EMEA enterprise renewals",
        ],
        "expected_output_notes": "Summary should not claim EMEA renewals declined.",
    },
]

DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES = [
    {
        "title": "Mobile performance and export requests",
        "input_text": (
            "Review 1: The mobile app is slow during checkout. Review 2: Checkout "
            "freezes on older Android phones. Ticket 9: Please add bulk export for "
            "reports. NPS: Support was helpful but performance is frustrating."
        ),
        "expected_facts_json": [
            "Mobile app is slow during checkout",
            "Checkout freezes on older Android phones",
            "Customers requested bulk export for reports",
            "Support was helpful",
        ],
        "expected_risks_json": ["Mobile checkout performance may hurt conversion"],
        "expected_recommendations_json": [
            "Prioritize mobile checkout performance",
            "Add bulk export for reports",
        ],
        "expected_themes_json": ["performance", "feature_requests", "support_experience"],
        "expected_output_notes": "Report should not claim support sentiment is negative.",
    },
    {
        "title": "Pricing concerns from small businesses",
        "input_text": (
            "Survey: Small business users said the new plan is too expensive. Review: "
            "Great product, but pricing jumped before we saw value. Ticket: Annual "
            "discount options are confusing. Review: Enterprise features are not needed "
            "for our five-person team."
        ),
        "expected_facts_json": [
            "Small business users said the new plan is too expensive",
            "Pricing jumped before value was clear",
            "Annual discount options are confusing",
            "Enterprise features are not needed for small teams",
        ],
        "expected_risks_json": ["Pricing friction among small business customers"],
        "expected_recommendations_json": [
            "Test clearer SMB pricing",
            "Simplify annual discount messaging",
        ],
        "expected_themes_json": ["pricing", "usability"],
        "expected_output_notes": "Report should not generalize pricing complaints to enterprise.",
    },
    {
        "title": "Bug reports after dashboard release",
        "input_text": (
            "Ticket 101: Dashboard filters reset after refresh. Ticket 102: Saved views "
            "sometimes disappear. Review: The new dashboard is useful when it loads. "
            "Ticket 103: Exported CSV files have duplicated rows."
        ),
        "expected_facts_json": [
            "Dashboard filters reset after refresh",
            "Saved views sometimes disappear",
            "New dashboard is useful when it loads",
            "Exported CSV files have duplicated rows",
        ],
        "expected_risks_json": ["Dashboard reliability issues may reduce trust"],
        "expected_recommendations_json": [
            "Fix dashboard filter persistence",
            "Investigate CSV duplicate rows",
        ],
        "expected_themes_json": ["bugs", "usability"],
        "expected_output_notes": "Report should separate usefulness from reliability bugs.",
    },
    {
        "title": "Support delays and onboarding confusion",
        "input_text": (
            "NPS comment: It took three days to get a support response. Review: Setup "
            "docs skipped the SSO configuration step. Ticket: Onboarding checklist is "
            "unclear for admins. Review: Once configured, the product works well."
        ),
        "expected_facts_json": [
            "Support response took three days",
            "Setup docs skipped SSO configuration",
            "Onboarding checklist is unclear for admins",
            "Product works well once configured",
        ],
        "expected_risks_json": ["Slow support and unclear onboarding may delay activation"],
        "expected_recommendations_json": [
            "Improve support response times",
            "Update SSO setup documentation",
            "Clarify admin onboarding checklist",
        ],
        "expected_themes_json": ["support_experience", "usability"],
        "expected_output_notes": "Report should not say the product fails after setup.",
    },
    {
        "title": "Feature requests for integrations",
        "input_text": (
            "Ticket: We need Salesforce sync for account owners. Review: Slack alerts "
            "would help our team act faster. Survey: HubSpot integration is required "
            "before rollout. Review: Current CSV import works but takes too long."
        ),
        "expected_facts_json": [
            "Customers need Salesforce sync for account owners",
            "Slack alerts would help teams act faster",
            "HubSpot integration is required before rollout",
            "CSV import works but takes too long",
        ],
        "expected_risks_json": ["Missing integrations may block rollout"],
        "expected_recommendations_json": [
            "Prioritize CRM integrations",
            "Evaluate Slack alerts",
            "Reduce CSV import friction",
        ],
        "expected_themes_json": ["feature_requests", "usability"],
        "expected_output_notes": "Report should not claim integrations already exist.",
    },
    {
        "title": "Positive sentiment with reporting gaps",
        "input_text": (
            "Review: The automation saves our team hours every week. NPS: Reporting is "
            "too limited for executives. Ticket: Need scheduled PDF reports. Review: "
            "Support answered our question quickly."
        ),
        "expected_facts_json": [
            "Automation saves hours every week",
            "Reporting is too limited for executives",
            "Customers need scheduled PDF reports",
            "Support answered quickly",
        ],
        "expected_risks_json": ["Reporting gaps may limit executive adoption"],
        "expected_recommendations_json": [
            "Add scheduled PDF reports",
            "Improve executive reporting",
        ],
        "expected_themes_json": ["feature_requests", "support_experience"],
        "expected_output_notes": "Report should preserve positive automation sentiment.",
    },
    {
        "title": "Usability friction in permissions",
        "input_text": (
            "Ticket: Role permissions are hard to understand. Review: We accidentally "
            "gave contractors admin access. Survey: Permission templates would help. "
            "Ticket: Audit log labels are confusing."
        ),
        "expected_facts_json": [
            "Role permissions are hard to understand",
            "Contractors were accidentally given admin access",
            "Permission templates were requested",
            "Audit log labels are confusing",
        ],
        "expected_risks_json": ["Permission confusion may create access control risk"],
        "expected_recommendations_json": [
            "Improve permission UX",
            "Add permission templates",
            "Clarify audit log labels",
        ],
        "expected_themes_json": ["usability", "feature_requests"],
        "expected_output_notes": "Report should treat contractor admin access as a risk.",
    },
    {
        "title": "Performance complaints in search",
        "input_text": (
            "Review: Search takes more than ten seconds for large accounts. Ticket: "
            "Results are stale after imports. NPS: Search relevance is good when it "
            "finishes. Survey: Faster filtering is our top request."
        ),
        "expected_facts_json": [
            "Search takes more than ten seconds for large accounts",
            "Search results are stale after imports",
            "Search relevance is good when it finishes",
            "Faster filtering is the top request",
        ],
        "expected_risks_json": ["Slow search may reduce usage in large accounts"],
        "expected_recommendations_json": [
            "Improve search latency",
            "Refresh search results after imports",
            "Speed up filtering",
        ],
        "expected_themes_json": ["performance", "feature_requests"],
        "expected_output_notes": "Report should not ignore the positive relevance note.",
    },
    {
        "title": "Mixed support and billing feedback",
        "input_text": (
            "Review: Billing invoices are hard to reconcile. Ticket: Support resolved "
            "our billing issue in one call. Survey: Need separate invoices by workspace. "
            "Review: Renewal reminders arrived too late."
        ),
        "expected_facts_json": [
            "Billing invoices are hard to reconcile",
            "Support resolved a billing issue in one call",
            "Customers need separate invoices by workspace",
            "Renewal reminders arrived too late",
        ],
        "expected_risks_json": ["Billing confusion may create renewal friction"],
        "expected_recommendations_json": [
            "Improve invoice clarity",
            "Add workspace-level invoices",
            "Send earlier renewal reminders",
        ],
        "expected_themes_json": ["pricing", "support_experience", "feature_requests"],
        "expected_output_notes": "Report should distinguish billing UX from support quality.",
    },
    {
        "title": "Accessibility and usability requests",
        "input_text": (
            "Review: Keyboard navigation skips the settings menu. Ticket: Low contrast "
            "text is hard to read. Survey: Screen reader labels are missing on charts. "
            "Review: The new layout is cleaner overall."
        ),
        "expected_facts_json": [
            "Keyboard navigation skips the settings menu",
            "Low contrast text is hard to read",
            "Screen reader labels are missing on charts",
            "The new layout is cleaner overall",
        ],
        "expected_risks_json": ["Accessibility gaps may block users from key workflows"],
        "expected_recommendations_json": [
            "Fix keyboard navigation",
            "Improve text contrast",
            "Add screen reader labels to charts",
        ],
        "expected_themes_json": ["usability"],
        "expected_output_notes": "Report should include accessibility-specific recommendations.",
    },
]

DEFAULT_INCIDENT_EVALUATION_CASES = [
    {
        "title": "API latency from database pool saturation",
        "input_text": (
            "09:58 - API p95 latency was 180ms. 10:04 - Latency rose to 2.8s on "
            "checkout and account endpoints. 10:08 - Error budget alert fired. "
            "10:15 - Database connection pool saturation reached 100%. 10:21 - "
            "On-call increased pool size and restarted two API workers. 10:27 - "
            "API p95 returned below 250ms. Unknown: the log does not show why pool "
            "usage spiked."
        ),
        "expected_facts_json": [
            "Latency rose to 2.8s on checkout and account endpoints",
            "Database connection pool saturation reached 100%",
            "API p95 returned below 250ms after pool size increase and worker restart",
            "Root cause is database connection pool saturation",
        ],
        "expected_risks_json": [
            "Do not claim a database outage occurred",
            "Label worker restart causality as inferred if mentioned",
        ],
        "expected_recommendations_json": [
            "Add connection pool saturation alerts",
            "Review pool sizing under checkout load",
        ],
        "expected_timeline_json": [
            {"time": "09:58", "event": "API p95 latency was 180ms"},
            {"time": "10:04", "event": "Latency rose to 2.8s"},
            {"time": "10:15", "event": "Database pool saturation reached 100%"},
            {"time": "10:27", "event": "API p95 returned below 250ms"},
        ],
        "expected_output_notes": (
            "Incident report should identify pool saturation as the supported root cause "
            "and not invent a database outage."
        ),
    },
    {
        "title": "Payment webhook backlog after deploy",
        "input_text": (
            "14:02 - Payment webhook deploy completed. 14:07 - Queue depth increased "
            "from 200 to 12,000 messages. 14:12 - Merchants reported delayed payment "
            "status updates. 14:18 - Logs showed webhook workers rejecting events with "
            "schema version v3. 14:30 - Deploy rolled back. 14:42 - Queue depth dropped "
            "below 500. Unknown: the log does not include the schema change owner."
        ),
        "expected_facts_json": [
            "Queue depth increased from 200 to 12,000 messages",
            "Webhook workers rejected events with schema version v3",
            "Rollback reduced queue depth below 500",
            "Root cause is incompatible webhook schema handling after deploy",
        ],
        "expected_risks_json": [
            "Do not claim payments were lost",
            "Do not assign ownership when the log says owner is unknown",
        ],
        "expected_recommendations_json": [
            "Add schema compatibility checks before deploy",
            "Alert on webhook queue depth growth",
        ],
        "expected_timeline_json": [
            {"time": "14:02", "event": "Payment webhook deploy completed"},
            {"time": "14:07", "event": "Queue depth increased to 12,000"},
            {"time": "14:18", "event": "Workers rejected schema version v3"},
            {"time": "14:30", "event": "Deploy rolled back"},
        ],
        "expected_output_notes": "Report should separate delayed status updates from payment loss.",
    },
    {
        "title": "Search outage from expired certificate",
        "input_text": (
            "01:00 - Search TLS certificate expired. 01:03 - Search API health checks "
            "failed in us-east. 01:09 - Users saw empty search results. 01:17 - New "
            "certificate was issued and deployed. 01:23 - Health checks recovered. "
            "Impact: search unavailable for 20 minutes in us-east. Unknown: renewal "
            "automation did not log its last run."
        ),
        "expected_facts_json": [
            "Search TLS certificate expired at 01:00",
            "Users saw empty search results",
            "Search was unavailable for 20 minutes in us-east",
            "Root cause is expired TLS certificate",
        ],
        "expected_risks_json": [
            "Do not claim all regions were affected",
            "Do not assert renewal automation failed without labeling it unknown",
        ],
        "expected_recommendations_json": [
            "Monitor certificate expiration",
            "Audit renewal automation logging",
        ],
        "expected_timeline_json": [
            {"time": "01:00", "event": "Search TLS certificate expired"},
            {"time": "01:03", "event": "Health checks failed in us-east"},
            {"time": "01:17", "event": "New certificate deployed"},
            {"time": "01:23", "event": "Health checks recovered"},
        ],
        "expected_output_notes": "Incident report should limit impact to us-east search.",
    },
    {
        "title": "Analytics delay from warehouse lock",
        "input_text": (
            "06:10 - Nightly analytics pipeline started. 06:45 - Customer dashboards "
            "stopped refreshing. 07:05 - Warehouse logs showed a long-running migration "
            "holding an exclusive lock on events_daily. 07:18 - Migration was canceled. "
            "07:36 - Backfill completed and dashboards refreshed. Unknown: migration "
            "approval record was not attached to the incident."
        ),
        "expected_facts_json": [
            "Dashboards stopped refreshing at 06:45",
            "Migration held an exclusive lock on events_daily",
            "Canceling migration and backfill restored dashboards",
            "Root cause is warehouse table lock from long-running migration",
        ],
        "expected_risks_json": [
            "Do not claim source event ingestion stopped",
            "Do not infer who approved the migration",
        ],
        "expected_recommendations_json": [
            "Block exclusive-lock migrations during analytics windows",
            "Require migration approval links in incident records",
        ],
        "expected_timeline_json": [
            {"time": "06:10", "event": "Analytics pipeline started"},
            {"time": "06:45", "event": "Dashboards stopped refreshing"},
            {"time": "07:05", "event": "Exclusive lock found"},
            {"time": "07:36", "event": "Dashboards refreshed"},
        ],
        "expected_output_notes": (
            "Report should distinguish analytics refresh delay from ingestion loss."
        ),
    },
    {
        "title": "Email delivery degradation from provider rate limit",
        "input_text": (
            "11:00 - Marketing email campaign began. 11:06 - Email provider returned "
            "429 rate-limit responses. 11:14 - Password reset emails were delayed up "
            "to 18 minutes. 11:22 - Campaign sending was paused. 11:31 - Password reset "
            "latency returned below two minutes. Unknown: campaign owner was not listed."
        ),
        "expected_facts_json": [
            "Email provider returned 429 rate-limit responses",
            "Password reset emails were delayed up to 18 minutes",
            "Pausing campaign sending restored password reset latency",
            "Root cause is provider rate limiting triggered during campaign sending",
        ],
        "expected_risks_json": [
            "Do not claim password resets failed permanently",
            "Do not name a campaign owner",
        ],
        "expected_recommendations_json": [
            "Reserve provider capacity for transactional email",
            "Throttle marketing campaigns during peak auth periods",
        ],
        "expected_timeline_json": [
            {"time": "11:00", "event": "Marketing campaign began"},
            {"time": "11:06", "event": "Provider returned 429 responses"},
            {"time": "11:14", "event": "Password reset emails delayed"},
            {"time": "11:31", "event": "Latency returned below two minutes"},
        ],
        "expected_output_notes": "Report should call out transactional email impact.",
    },
    {
        "title": "Mobile login failure from feature flag rollout",
        "input_text": (
            "16:00 - Login redesign feature flag enabled for 25% of mobile users. "
            "16:08 - Crash-free sessions dropped from 99.8% to 93.1% on Android. "
            "16:12 - Support tickets mentioned login screen crash. 16:20 - Feature "
            "flag disabled. 16:29 - Crash-free sessions recovered to 99.7%. Unknown: "
            "iOS impact was not observed in the log."
        ),
        "expected_facts_json": [
            "Feature flag enabled for 25% of mobile users",
            "Crash-free sessions dropped to 93.1% on Android",
            "Support tickets mentioned login screen crash",
            "Root cause is Android crash from login redesign feature flag rollout",
        ],
        "expected_risks_json": [
            "Do not claim iOS was affected",
            "Do not say all mobile users were impacted",
        ],
        "expected_recommendations_json": [
            "Gate mobile feature flags by platform",
            "Add crash-rate automatic rollback for login changes",
        ],
        "expected_timeline_json": [
            {"time": "16:00", "event": "Login flag enabled"},
            {"time": "16:08", "event": "Android crash-free sessions dropped"},
            {"time": "16:20", "event": "Feature flag disabled"},
            {"time": "16:29", "event": "Crash-free sessions recovered"},
        ],
        "expected_output_notes": (
            "Report should scope impact to Android users in the rollout cohort."
        ),
    },
    {
        "title": "Cache stampede during pricing update",
        "input_text": (
            "12:00 - Pricing table update published. 12:03 - Cache hit rate dropped "
            "from 94% to 22%. 12:06 - Product pages timed out for 14% of requests. "
            "12:11 - Application logs showed repeated price recomputation for the same "
            "SKUs. 12:19 - Hot SKU cache prewarm completed. 12:24 - Timeouts returned "
            "below 1%. Unknown: cache invalidation batch size was not recorded."
        ),
        "expected_facts_json": [
            "Cache hit rate dropped from 94% to 22%",
            "Product pages timed out for 14% of requests",
            "Repeated price recomputation occurred for the same SKUs",
            "Root cause is cache stampede after pricing update",
        ],
        "expected_risks_json": [
            "Do not claim checkout payments failed",
            "Do not state the invalidation batch size",
        ],
        "expected_recommendations_json": [
            "Prewarm hot SKU cache before pricing updates",
            "Record and limit cache invalidation batch size",
        ],
        "expected_timeline_json": [
            {"time": "12:00", "event": "Pricing update published"},
            {"time": "12:03", "event": "Cache hit rate dropped"},
            {"time": "12:11", "event": "Repeated recomputation observed"},
            {"time": "12:24", "event": "Timeouts returned below 1%"},
        ],
        "expected_output_notes": "Report should connect timeouts to cache stampede evidence.",
    },
    {
        "title": "Support portal errors from missing secret",
        "input_text": (
            "08:30 - Support portal deploy completed. 08:34 - Agents saw 500 errors "
            "opening customer profiles. 08:39 - Logs showed CUSTOMER_PROFILE_TOKEN was "
            "missing in the new deployment environment. 08:47 - Secret restored and "
            "pods restarted. 08:53 - Profile open success returned to 99%. Unknown: "
            "secret rotation status was not documented."
        ),
        "expected_facts_json": [
            "Support agents saw 500 errors opening customer profiles",
            "CUSTOMER_PROFILE_TOKEN was missing",
            "Restoring the secret and restarting pods recovered profile opens",
            "Root cause is missing deployment secret",
        ],
        "expected_risks_json": [
            "Do not claim customer data was exposed",
            "Do not assert secret rotation status",
        ],
        "expected_recommendations_json": [
            "Add deployment checks for required secrets",
            "Document secret rotation status in incident records",
        ],
        "expected_timeline_json": [
            {"time": "08:30", "event": "Support portal deploy completed"},
            {"time": "08:34", "event": "Agents saw 500 errors"},
            {"time": "08:39", "event": "Missing token found"},
            {"time": "08:53", "event": "Profile opens recovered"},
        ],
        "expected_output_notes": "Report should avoid unsupported security claims.",
    },
    {
        "title": "Data import failures from CSV parser regression",
        "input_text": (
            "13:15 - CSV parser version 2.4 deployed. 13:27 - Enterprise imports "
            "began failing validation. 13:35 - Error logs showed quoted newline fields "
            "parsed as separate rows. 13:50 - Parser rolled back to version 2.3. "
            "14:05 - Failed imports were retried successfully. Unknown: no data loss "
            "was reported in the log."
        ),
        "expected_facts_json": [
            "CSV parser version 2.4 deployed",
            "Enterprise imports failed validation",
            "Quoted newline fields were parsed as separate rows",
            "Root cause is CSV parser regression",
        ],
        "expected_risks_json": [
            "Do not claim data loss occurred",
            "Do not say all imports failed",
        ],
        "expected_recommendations_json": [
            "Add regression tests for quoted newline fields",
            "Canary CSV parser releases on enterprise import samples",
        ],
        "expected_timeline_json": [
            {"time": "13:15", "event": "Parser version 2.4 deployed"},
            {"time": "13:27", "event": "Enterprise imports failed validation"},
            {"time": "13:35", "event": "Quoted newline parsing bug found"},
            {"time": "14:05", "event": "Failed imports retried successfully"},
        ],
        "expected_output_notes": (
            "Report should state validation failures without inventing data loss."
        ),
    },
    {
        "title": "Notification duplication from retry misconfiguration",
        "input_text": (
            "17:40 - Notification retry policy changed from exponential to fixed 10s. "
            "17:52 - Users reported duplicate push notifications. 17:58 - Metrics "
            "showed retry attempts tripled for transient APNS failures. 18:07 - Retry "
            "policy reverted. 18:18 - Duplicate notification rate returned to baseline. "
            "Unknown: exact number of affected users was not captured."
        ),
        "expected_facts_json": [
            "Retry policy changed from exponential to fixed 10s",
            "Users reported duplicate push notifications",
            "Retry attempts tripled for transient APNS failures",
            "Root cause is notification retry misconfiguration",
        ],
        "expected_risks_json": [
            "Do not invent exact affected user count",
            "Do not claim notifications were not delivered",
        ],
        "expected_recommendations_json": [
            "Require retry policy review before notification changes",
            "Alert on duplicate notification rate",
        ],
        "expected_timeline_json": [
            {"time": "17:40", "event": "Retry policy changed"},
            {"time": "17:52", "event": "Duplicate notifications reported"},
            {"time": "17:58", "event": "Retry attempts tripled"},
            {"time": "18:18", "event": "Duplicate rate returned to baseline"},
        ],
        "expected_output_notes": "Report should mention unknown affected-user count.",
    },
]


def seed_default_evaluation_cases(db: Session) -> list[EvaluationCase]:
    seeded: list[EvaluationCase] = []
    defaults_by_workflow = {
        WorkflowType.sales_report: DEFAULT_SALES_EVALUATION_CASES,
        WorkflowType.customer_feedback: DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES,
        WorkflowType.incident_log: DEFAULT_INCIDENT_EVALUATION_CASES,
    }
    for workflow_type, defaults in defaults_by_workflow.items():
        seeded.extend(_seed_cases_for_workflow(db, workflow_type, defaults))

    db.commit()
    for case in seeded:
        db.refresh(case)
    return seeded


def _seed_cases_for_workflow(
    db: Session,
    workflow_type: WorkflowType,
    defaults: list[dict[str, object]],
) -> list[EvaluationCase]:
    seeded: list[EvaluationCase] = []
    for default in defaults:
        case = (
            db.query(EvaluationCase)
            .filter(
                EvaluationCase.workflow_type == workflow_type,
                EvaluationCase.title == default["title"],
            )
            .first()
        )
        if case is None:
            case = EvaluationCase(
                workflow_type=workflow_type,
                title=default["title"],
                input_text=default["input_text"],
                expected_facts_json=default["expected_facts_json"],
                expected_risks_json=default["expected_risks_json"],
                expected_recommendations_json=default["expected_recommendations_json"],
                expected_themes_json=default.get("expected_themes_json"),
                expected_timeline_json=default.get("expected_timeline_json"),
                expected_output_notes=default["expected_output_notes"],
            )
            db.add(case)
        else:
            case.input_text = default["input_text"]
            case.expected_facts_json = default["expected_facts_json"]
            case.expected_risks_json = default["expected_risks_json"]
            case.expected_recommendations_json = default["expected_recommendations_json"]
            case.expected_themes_json = default.get("expected_themes_json")
            case.expected_timeline_json = default.get("expected_timeline_json")
            case.expected_output_notes = default["expected_output_notes"]
        seeded.append(case)
    return seeded
