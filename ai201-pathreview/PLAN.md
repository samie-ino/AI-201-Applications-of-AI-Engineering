# Week 8 Plan: Add contribution streak support to repo analysis

## Solution plan

**Issue:** Add a `contribution_streak` field to the GitHub analysis (longest consecutive days of commits) — https://github.com/samie-ino/AI-201-Applications-of-AI-Engineering/issues/52

### Understand
The root cause is that the repo analysis pipeline does not expose a contribution-streak field even when contribution-history data is present. The expected behavior is to compute and surface the longest consecutive-day streak, while the current behavior leaves this metadata missing.

### Map
The work touches the repo analysis flow in:
- ai201-pathreview/tests/unit/test_repo_analyzer.py
- ai201-pathreview/ingestion/parsers/repo_analyzer.py
- ai201-pathreview/agent/tools/github_tool.py

### Plan
1. Reproduce the missing field with a regression test using contribution-history data.
2. Implement contribution-streak computation in the repo parser and include it in parsed metadata and summary text.
3. Ensure the GitHub metadata tool carries contribution-history data into the parser.
4. Run the relevant unit tests and update the journal with the verified result.

### Inputs & outputs
The fix takes repository metadata with contribution-history information as input and should output repo metadata that includes a numeric `contribution_streak` value.

### Risks & unknowns
Some repository payloads may provide contribution history in slightly different shapes, so the parser should tolerate a few common formats. The GitHub API may not expose contribution history directly in the basic repository endpoint, so the implementation may need to rely on data already supplied by the environment or future ingestion sources.

### Edge cases
The fix should handle repositories with no contribution history, partial history, and entries with different date or count field names without crashing.
