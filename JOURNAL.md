# JOURNAL

## Week 7 — Issue selection

**Issue link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/issues/52

**Issue title:** Add a `contribution_streak` field to the GitHub analysis (longest consecutive days of commits)

**Tier:** [x] Tier 2  [ ] Tier 1  [ ] Tier 3

**Problem summary:**
The PathReview repository analysis pipeline exposes repository metadata such as stars, tests, and last commit date, but it does not surface a contribution-streak metric when contribution-history data is available. That leaves a useful portfolio signal missing from repo analysis and makes the GitHub analysis less informative for contribution tracking. A successful fix will compute the longest consecutive-day streak and expose it in the repo metadata that downstream tools can use.

**Selection notes / "Is this right for me?" reasoning:**
This issue is a good fit for a first contribution because the scope is narrow and testable: it affects the repository metadata parser and a small slice of GitHub analysis behavior, not the whole UI or database workflow. The expected change is well defined by the regression test and by the existing `contribution_streak` data flow in the GitHub tool path, so the work stays focused on one clear contract change. A successful solution only needs to wire the metadata through the analyzer and keep the existing formatting and test expectations intact.

**Branch name:** feat/52-contribution-streak

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/commit/edf609e

**Reproduction summary:**
I reproduced the issue by adding a regression test in [ai201-pathreview/tests/unit/test_repo_analyzer.py](ai201-pathreview/tests/unit/test_repo_analyzer.py) that passed repository metadata with contribution-history data. The test failed with `KeyError: 'contribution_streak'`, confirming that the repo analysis pipeline was not exposing the expected field.

**PLAN.md link:** [PLAN.md](PLAN.md)

**Walkthrough video (recommended):** Not recorded yet

**Blockers or open questions:**
None at the moment.

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**
I reproduced the issue with a focused regression test, then implemented the parser and metadata-path change so the repo analysis now exposes a `contribution_streak` value when `contribution_history` is available. The work is confined to the repository metadata analysis path and its regression coverage.

**Next steps:**
I am documenting the self-review evidence, verifying the issue-related tests that prove the behavior, and preparing the PR summary around the repo-wide baseline failures that are unrelated to this fix.

**Blockers:**
None for the targeted issue. The repository still has unrelated baseline lint/test violations that show up in `make check` and `make test-unit` outside the scope of this change.

---

### Check-in 2 (end of week)

**PR link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/pull/5

**Branch:** feat/52-contribution-streak

**What you built:**
This fix adds a `contribution_streak` field to the repo-analysis metadata path by computing the longest consecutive-day streak from GitHub contribution-history data. The analyzer now keeps that signal in the output metadata so downstream GitHub analysis can consume it cleanly.

**Tests added or updated:**
I touched [ai201-pathreview/tests/unit/test_repo_analyzer.py](ai201-pathreview/tests/unit/test_repo_analyzer.py) to guard the regression case and confirm the metadata now includes the expected streak value. I also validated the existing contribution-streak coverage in [ai201-pathreview/tests/unit/test_github_tool.py](ai201-pathreview/tests/unit/test_github_tool.py).

**Self-review confirmation:** [ ] make check passes  [ ] make test-unit passes

**Draft PR feedback received from:** none

