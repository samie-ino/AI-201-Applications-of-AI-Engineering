# Week 8 Plan: Add contribution streak support to repo analysis

## Problem
The pathreview repo analysis pipeline exposes repository metadata fields such as stars, tests, and last commit date, but it does not expose a contribution streak metric even when contribution-history data is available. This makes the portfolio review less informative for contributors and leaves the issue described in the project backlog unresolved.

## Approach
1. Reproduce the gap by adding a focused regression test that expects a contribution-streak field from repo metadata with contribution-history entries.
2. Implement support in the repo parser so it computes the longest consecutive-day streak from contribution-history data and includes it in the parsed metadata and summary text.
3. Ensure the GitHub metadata tool passes through contribution-history information so the parser can consume it.
4. Run the relevant unit tests and record the result in the journal.

## Files to touch
- ai201-pathreview/tests/unit/test_repo_analyzer.py
- ai201-pathreview/ingestion/parsers/repo_analyzer.py
- ai201-pathreview/agent/tools/github_tool.py

## Risks / unknowns
- Some repository payloads may provide contribution history in slightly different shapes, so the parser should tolerate a few common formats.
- The GitHub API may not expose contribution data directly in the basic repository endpoint, so the implementation currently relies on the repository payload structure already supplied by the environment and future ingestion sources.
