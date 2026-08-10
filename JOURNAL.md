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
I reproduced the issue with a focused regression test and then implemented the parser-level change so repo analysis now exposes a `contribution_streak` value when contribution-history data is present. The work stayed scoped to the repository metadata analysis path and its targeted regression coverage.

**Next steps:**
I am wrapping up the PR summary, preserving the verification evidence, and documenting the repo-wide baseline failures observed during self-review so the submission clearly shows that this issue-specific change did not introduce new breakage.

**Blockers:**
None for the targeted issue. The repository still shows unrelated baseline lint and test failures in other areas, so the full self-check commands are not completely green even though the contribution-streak regression path is now passing.

---

### Check-in 2 (end of week)

**PR link:** https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/pull/5

**Branch:** feat/52-contribution-streak

**What you built:**
This fix adds a `contribution_streak` field to the repo-analysis metadata path by computing the longest consecutive-day streak from GitHub contribution-history data. The analyzer now carries that signal through its output metadata so downstream GitHub analysis can consume it cleanly.

**Tests added or updated:**
I touched [ai201-pathreview/tests/unit/test_repo_analyzer.py](ai201-pathreview/tests/unit/test_repo_analyzer.py) to lock in the regression scenario and confirm that the metadata now exposes the expected streak value. I also validated the existing contribution-streak coverage in [ai201-pathreview/tests/unit/test_github_tool.py](ai201-pathreview/tests/unit/test_github_tool.py).

**Self-review confirmation:**
- [ ] `make check` passes
- [ ] `make test-unit` passes

Verification note: I ran both repo-wide self-check commands and confirmed the targeted issue regression path passes, but the repository still reports unrelated baseline failures outside the scope of this contribution. This submission is therefore documented as a scoped fix for the `contribution_streak` issue rather than a claim that the entire codebase is clean.

**Draft PR feedback received from:** none

## Week 10 — Iteration & reflection

### Reviewer feedback

**Feedback received:** [ ] Yes  [x] No — still awaiting review

**Summary of feedback:**
No reviewer feedback was provided in Summer 2026. The pull request remained open without review comments as of August 10, 2026.

**How you responded:**

---

### Reflection

**What was harder than you expected?**
The hardest part was separating issue-specific behavior from the repository's broader health. The contribution-streak regression was narrow and its focused tests passed, but the initial full-suite run reported 53 failures and `make check` stopped at 183 Ruff errors. Investigating those failures showed that many were real defects hidden by broad exception handlers, including broken PDF parsing, an always-unhealthy health check, an uninitialized BM25 keyword index, and incorrect primary-language detection. I had expected to finish once the targeted regression passed; instead, I had to establish a baseline, identify which failures were inherited, and decide how far remediation should go without losing the original scope.

**What did you learn about working in a large codebase?**
Contributing to an existing codebase requires understanding contracts and boundaries before changing implementation. For this issue, the repository analyzer was the right place to normalize contribution-history data for downstream consumers, and focused edge-case tests clarified behavior for empty histories, gaps, duplicate dates, alternate fields, and explicit pre-computed values. I also learned that a technically mergeable branch is not necessarily easy to review: when the base branch has diverged, the complete changed-file list matters as much as the conflict status. In someone else's production code, tests, configuration, dependency declarations, and history are all part of the feature's context.

**How did AI tools help — and where did they fall short?**
AI assistance was most useful for quickly locating the analyzer, tracing the `contribution_streak` data flow, drafting focused regression cases, and identifying nearby implementation and test boundaries. It also helped organize the failure investigation once the full suite exposed problems outside the original issue. It fell short when broad failures looked like baseline noise: I still had to run the commands, inspect tracebacks, verify dependency and configuration facts, and make the judgment that several failures represented real application bugs. AI could suggest likely fixes, but it could not replace checking the actual branch diff, confirming the environment, or deciding which changes were justified.

**What would you do differently if you started over?**
I would capture the exact baseline from `make check`, `make test-unit`, and the full suite before making any edits, then record which failures belong to the issue. I would also inspect the pull request's changed-file list and base-branch relationship earlier instead of treating mergeability as sufficient evidence that the PR was clean. For implementation, I would define the edge-case contract before writing the parser change and keep the issue-specific test separate from any broader repository remediation. That process would make the scope, regression evidence, and remaining technical debt easier for a reviewer to evaluate.

**What are you most proud of from this module?**
I am most proud that I did not stop at a passing happy-path regression test. I made the contribution-streak behavior explicit, added coverage for the important data-shape edge cases, and followed the broader failures far enough to distinguish inherited problems from regressions. The final verification showed 435 tests passing with no failures and Ruff clean, while the remaining mypy issues were documented as bounded annotation work rather than hidden.

### Deliverables Checklist

- **Reviewer feedback documented in `JOURNAL.md`:** [x] No feedback received in Summer 2026; no reviewer response was required
- **Reflection completed in `JOURNAL.md`:** [x] All five reflection prompts answered
- **Branch URL submitted via course portal:** [ ] https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/tree/feat/52-contribution-streak

