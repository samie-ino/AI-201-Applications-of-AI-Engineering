# JOURNAL

## Week 7 — Issue selection

**Issue link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/issues/52

**Issue title:** Add a `contribution_streak` field to the GitHub analysis (longest consecutive days of commits)

**Tier:** [x] Tier 2  [ ] Tier 1  [ ] Tier 3

**Problem summary:**
The PathReview repository analysis pipeline exposes repository metadata such as stars, tests, and last commit date, but it does not surface a contribution-streak metric when contribution-history data is available. That leaves a useful portfolio signal missing from repo analysis and makes the GitHub analysis less informative for contribution tracking. A successful fix will compute the longest consecutive-day streak and expose it in the repo metadata that downstream tools can use.

**Branch name:** feat/52-contribution-streak

**Setup confirmation:** [ ] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/commit/edf609e

**Reproduction summary:**
I reproduced the issue by adding a regression test in [ai201-pathreview/tests/unit/test_repo_analyzer.py](ai201-pathreview/tests/unit/test_repo_analyzer.py) that passed repository metadata with contribution-history data. The test failed with `KeyError: 'contribution_streak'`, confirming that the repo analysis pipeline was not exposing the expected field.

**PLAN.md link:** [PLAN.md](PLAN.md)

**Walkthrough video (recommended):** Not recorded yet

**Blockers or open questions:**
None at the moment.

