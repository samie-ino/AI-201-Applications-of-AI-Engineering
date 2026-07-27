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

## Week 8 — Reproduction and plan

**Issue link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/issues/52

**Issue title:** Add a `contribution_streak` field to the GitHub analysis (longest consecutive days of commits)

**Reproduction:**
I added a regression test in [ai201-pathreview/tests/unit/test_repo_analyzer.py](ai201-pathreview/tests/unit/test_repo_analyzer.py) that passes repository metadata including a contribution-history list. The test initially failed with `KeyError: 'contribution_streak'`, confirming the field was missing from the parsed repo metadata.

**Verification:**
I verified the fix locally by running:
`/workspaces/AI-201-Applications-of-AI-Engineering/.venv/bin/python -m pytest -q tests/unit/test_repo_analyzer.py`
Result: `1 passed in 0.16s`.

**Plan file:**
See [PLAN.md](PLAN.md) for the implementation plan and file list.

