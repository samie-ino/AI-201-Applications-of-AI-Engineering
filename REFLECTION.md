# Week 10 Reflection

## PR and review status

PR: https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/pull/5

As of August 10, 2026, no reviewer feedback or review comments were received on the pull request. There are therefore no reviewer comments to answer and no documented reviewer-response commits for Week 10. The PR remains open for review.

## What I learned

This contribution taught me that a small feature can still require careful decisions about data contracts, test boundaries, and repository history. I learned to make the intended behavior explicit before extending defensive parsing, to use focused edge-case tests to define the contract, and to inspect a pull request's complete diff instead of treating a green merge status as proof that the change is safe to merge.

### Implementation

The contribution-streak behavior belongs in the repository analyzer, where repository metadata is normalized for downstream consumers. The implementation needs to tolerate inconsistent history payloads, including alternate date and contribution-count field names, string entries, invalid dates, empty history, gaps, and duplicate dates.

I also documented the precedence rule for an explicit `contribution_streak` value: when a non-null pre-computed value is supplied, it is authoritative; otherwise, the analyzer computes the value from contribution history. Making that decision explicit reduces ambiguity for future maintainers.

### Testing

The initial regression test caught the missing metadata field. Additional focused tests made the calculation contract clearer by covering empty history, a single day, non-consecutive days, duplicate dates, and an explicit pre-computed value alongside history. These tests protect the edge cases most likely to be affected by a future refactor.

The repository-wide `make check` and `make test-unit` commands were not fully green because of pre-existing failures outside this change. The targeted streak assertions passed, and the commit hooks passed Ruff, Black, and mypy. A future contribution should capture the exact baseline failures before editing and compare them with the post-change results. I acted on that note within the same week; see "Remediation of the pre-existing failures" below.

### Pull request process

The PR initially reported conflicts because its `main` base had diverged from the PathReview project tree. I learned that a branch can be technically mergeable while still having a much broader diff than intended. Before merging, I should inspect the PR changed-file list and confirm that the base branch represents the same project state as the feature branch.

The conflict was resolved with an ours-strategy merge so the feature branch file tree stayed unchanged. This cleared GitHub's conflict status, but it also reinforced that mergeability is not the same as review safety: the final PR diff still needs to be reviewed before merging.

## Verification snapshot

First run on August 10, 2026, before the remediation described below:

- Contribution-streak tests: `6 passed`
- Unit suite: `382 passed, 53 failed, 3 warnings`
- Full suite: `382 passed, 53 failed, 3 warnings`
- `make check`: stopped at Ruff with 183 existing errors in unrelated files; the working tree remained unchanged

Representative pre-existing failures were in markdown parsing, password-hash error handling, skill extraction, structural chunking, and tech detection. None of the 53 failures came from `test_repo_analyzer.py`.

Second run on August 10, 2026, after the remediation:

- Contribution-streak tests: `6 passed`
- Full suite: `435 passed, 0 failed, 2 warnings`
- Ruff: `All checks passed`
- Mypy: 10 remaining errors, all missing annotations; it previously aborted before checking any project code

## Remediation of the pre-existing failures

Rather than leave the 53 failures as inherited noise, I worked through them. The most useful discovery was that most of them were not flaky or obsolete tests: 49 of the 53 were failing because the implementation was wrong, and only 4 because the test was wrong.

### Defects the failing tests were pointing at

Four of these would have affected anyone actually running the application, and each was hidden by a broad `except Exception` that converted a crash into a plausible-looking failure response:

- `api/routes/profiles.py` imported `PyPDF2`, which is neither installed nor listed as a dependency; the project uses `pypdf`. Every PDF resume upload raised `ImportError` and was reported to the user as "Failed to parse PDF". The same call also passed raw bytes where a file-like object is required.
- `api/routes/health.py` read `settings.redis_host` and `settings.redis_port`, which do not exist on `Settings`; only `redis_url` does. It also passed a raw SQL string to `execute()`, which SQLAlchemy 2.0 rejects. Both dependency checks therefore always failed, so the endpoint reported the service as unhealthy no matter what was actually running.
- `rag/retriever/hybrid.py` fetched every chunk in the collection "for keyword indexing" and then discarded them. `KeywordSearcher.index()` was never called anywhere in the codebase, so BM25 always scored against an empty index and hybrid retrieval silently degraded to vector-only search.
- `agent/tools/tech_detector.py` selected the primary language alphabetically rather than by file count, counted `Build` and `Infrastructure` categories as languages, and only skipped vendor directories when they appeared mid-path, so a top-level `node_modules/` was counted in full.

### What I learned

The lesson I did not expect is how much a broad `except Exception` can cost. In all four cases the code caught the exception, logged it, and returned a reasonable-looking error, so the failure looked like an external problem rather than a bug in the code. The tests had been recording these behaviors as failures the whole time, and I had read them as someone else's problem.

The second lesson is that a test that asserts nothing is worse than a missing test, because it still counts as coverage. Nineteen tests in the suite called into the code and then made no assertion at all; several had a comment describing the intended check that was never written. Adding the intended assertion to each one is what surfaced the `tech_detector` primary-language bug.

The third lesson concerns the tooling itself. `make check` runs lint, then format, then typecheck, so Ruff's 183 errors meant mypy had never run once on this project. When I cleared Ruff and unblocked it, mypy immediately found the `PyPDF2` import and, once the database session was annotated, the invalid `execute("SELECT 1")` call. A type checker that never runs provides no value, and the reason it never ran was a configuration mismatch rather than anything about the code: `python_version` was pinned to 3.11 while the virtual environment runs 3.12, so it aborted while parsing numpy's stubs.

Finally, I now understand the baseline advice I gave myself last time more concretely. Capturing the 53 failures before editing was what made it possible to show that this work removed exactly those failures and introduced none.

### What remains

Mypy still reports 10 errors, all of them missing type annotations rather than type conflicts. They are mechanical to resolve but touch a number of files, so I stopped at a point where the suite and linter are both clean and the remaining work is clearly bounded.

## Reviewer response log

- Reviewer feedback received: none.
- Reviewer responses required: none.
- Follow-up action: monitor the open PR and respond if maintainer feedback arrives before the course ends.

## Next steps

1. Keep the PR open for reviewer feedback.
2. Review the final changed-file list before merging.
3. If feedback arrives, respond in the PR discussion and link each response to the corresponding code or test change.
4. Finish the 10 remaining mypy annotations so `make check` completes end to end.
5. Narrow the broad `except Exception` handlers in the routes, which is what let the PDF-upload and health-check bugs stay invisible.
