# Journal

## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/52

**Issue title:** Add a `contribution_streak` field to the GitHub analysis (longest consecutive days of commits)

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
The agent's GitHub analysis tool (`agent/tools/github_tool.py`) doesn't currently capture how consistently a user has been contributing over time, even though a steady commit history is a useful portfolio signal. There's no logic today that takes a user's GitHub contribution history, groups it by calendar day, and finds the longest unbroken run of consecutive active days. A successful fix adds a `contribution_streak` computation to the tool, exposes it as a new field in the tool's output, and covers edge cases like gaps between commits, single-day streaks, and streaks that span multiple months. This affects the `agent/` subsystem specifically, since the GitHub tool's output feeds into the review the agent generates for a user's portfolio.

**Branch name:** feat/52-contribution-streak

**Setup confirmation:** [ ] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger
