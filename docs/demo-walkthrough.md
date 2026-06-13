# Demo Walkthrough

This walkthrough is designed for a live portfolio demo after the app is running
and demo data has been seeded.

## Start And Seed

1. Start the app:

   ```powershell
   docker compose up -d --build
   ```

2. Open `http://localhost:3000/demo`.
3. Click `Run Full Evaluation`.
4. Wait for the cards to refresh, then open `Compare`.

## Workflow Comparison

1. On `/workflow-comparison`, point out the dashboard header:
   - `Comparisons` shows the paired baseline and multi-agent evaluations.
   - Accuracy and completeness deltas are quality signals.
   - Unsupported deltas now say `better`, `worse`, or `no change`.
   - Cost and latency deltas are tradeoffs.

2. Search for:

   ```text
   [Demo] Reviewer issue correction path
   ```

3. Open details. This case is action-ready:
   - The card should show `Needs review`.
   - Metric chips should say `vs baseline`.
   - The reviewer issue explains that declining pipeline coverage was framed as an
     opportunity.
   - The `Create corrected run` button should be visible.

4. Search for:

   ```text
   [Demo] Remediation impact showcase
   ```

5. Open details. This case is impact-ready:
   - The card should show the latest corrected multi-agent result.
   - The `Remediation impact` panel should be visible.
   - Impact chips should say `vs previous run`.
   - Reviewer issues should show improvement from the previous run to the
     corrected run.
   - If unsupported claims worsened, call that out as a mixed remediation outcome.

## Inspect The Runs

1. In the remediation impact panel, open the `previous` run link.
2. Return to the comparison and open the `corrected` run link.
3. On each workflow run detail page, show:
   - run mode
   - final output
   - agent step timeline
   - reviewer output
   - cost, token, and latency metadata

## Dashboard Tour

After the comparison flow, visit:

- `/workflow-runs`: all baseline, multi-agent, and corrected runs.
- `/evaluation`: aggregate baseline vs multi-agent quality tradeoffs.
- `/costs`: workflow and agent-level cost/token aggregation.
- `/agent-performance`: latency, retry, and reviewer quality by agent.
- `/failures`: low-quality runs and recorded issue categories.

## Talk Track

The key story is that the app does not blindly trust AI output. It records each
workflow run, compares baseline and multi-agent behavior, flags reviewer issues,
supports corrected runs, and shows when remediation improves review quality while
possibly worsening deterministic benchmark metrics.
