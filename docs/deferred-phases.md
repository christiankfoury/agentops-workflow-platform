# Deferred Phases

These phases were removed from the main implementation sequence to keep the portfolio plan focused, but they remain useful future work.

# Deferred: Notifications

Add simple notifications.

Notify users when:

```text
workflow completed
workflow needs human approval
workflow failed
evaluation run completed
```

Start with in-app notifications.

Optional later:

```text
email notifications
Slack webhook
```

This makes the app more useful and realistic.

---

# Phase 54: Authentication

Add basic authentication.

Use something like:

```text
NextAuth
Clerk
Auth.js
Supabase Auth
```

Protect:

```text
workflow runs
prompt versions
evaluation results
admin settings
```

This makes the project more enterprise-like.

---

# Phase 55: User and Organization Model

Add support for users and organizations.

Tables:

```text
users
organizations
organization_members
```

Associate workflow runs with an organization.

This prepares the app for permissions and team-based workflows.

---

# Phase 56: Role-Based Permissions

Add role-based access control.

Example roles:

```text
admin
reviewer
analyst
viewer
```

Permissions:

```text
admins can edit prompts and settings
reviewers can approve workflows
analysts can create workflows
viewers can only read results
```

This is optional for many projects, but very strong for enterprise credibility.

---

# Phase 57: Approval Permissions

Restrict human approval actions by role.

For example:

```text
Only reviewers and admins can approve final outputs.
Only admins can approve outputs with high-severity reviewer issues.
Only admins can change reviewer thresholds.
```

This connects authentication to your agent workflow in a meaningful way.

---

# Phase 58: Audit Trail

Add an audit trail for important user actions.

Track:

```text
user created workflow
user approved workflow
user rejected workflow
user edited analysis
user changed prompt version
user changed threshold
user exported evaluation report
```

This is a strong enterprise feature, especially for human-in-the-loop AI systems.

---

# Phase 59: Background Jobs

Move long-running workflows to background jobs.

Use:

```text
Celery
RQ
Dramatiq
Arq
FastAPI background tasks for simple version
```

This prevents the frontend from waiting on long LLM calls.

A workflow should be started by the API, then processed asynchronously by a worker.

---

# Phase 60: Live Workflow Updates

Add live progress updates.

Options:

```text
polling
Server-Sent Events
WebSockets
```

The UI should update as agents complete:

```text
Analyst Agent running...
Reviewer Agent completed...
Waiting for human approval...
Writer Agent running...
Workflow completed.
```

This makes the app feel polished.

---

# Phase 61: Queue and Worker Observability

Add visibility into background jobs.

Show:

```text
queued workflows
running workflows
failed jobs
retrying jobs
worker status
average queue time
```

This is especially useful if you use a background worker system.

---

# Phase 62: Caching and Duplicate Run Detection

Add caching for repeated evaluation runs or duplicate inputs.

If the same evaluation case is run with the same prompt version and model settings, you can reuse results or warn the user.

Track cache hits.

This is a nice advanced optimization and shows cost awareness.

---

# Phase 64: Advanced Evaluation: LLM Judge

Add an evaluator agent that scores outputs using a rubric.

Use it to evaluate:

```text
factual accuracy
completeness
clarity
business usefulness
unsupported claims
```

Store the judge reasoning summary, but avoid relying only on it.

The best evaluation system combines deterministic checks and LLM-as-judge.

---

# Phase 75: Deployment Setup

Prepare for deployment.

Add:

```text
production Dockerfiles
production environment config
database migration command
deployment README
health check endpoints
logging config
```

Deploy options:

```text
Render
Railway
Fly.io
Azure
AWS
GCP
```

Since you previously mentioned Montreal, Toronto, and NYC, Azure is a good choice if you want enterprise alignment, but Railway or Render may be faster for a portfolio demo.

---

# Phase 76: Production Deployment

Deploy the app.

At minimum deploy:

```text
frontend
backend
PostgreSQL database
worker if using background jobs
```

Make sure the live demo has:

```text
seed demo data
auth demo account
working evaluation dashboard
no exposed secrets
```
