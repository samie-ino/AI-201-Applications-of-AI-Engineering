# Mixtape Bug Hunt — Milestone 2 Reproduction Notes

No production code changes were made during this milestone. The goal here was to reproduce each selected bug from the app’s real behavior before attempting any fixes.

## Bug 1 — Listening streak incorrectly resets on Sunday
- Issue: My listening streak keeps resetting.
- How you reproduced it:
  1. Create a new user in the test app.
  2. Call the streak update service for a Saturday timestamp (2024-06-15 12:00 UTC).
  3. Call the streak update service again for the following Sunday timestamp (2024-06-16 12:00 UTC).
  4. Inspect the user’s listening streak value.
- Observed behavior: The streak remained at 1 instead of increasing to 2.
- Expected behavior: A consecutive Saturday-to-Sunday listening pattern should extend the streak to 2.

## Bug 2 — Search returns duplicate results for songs with multiple tags
- Issue: The same song keeps showing up twice in search.
- How you reproduced it:
  1. Seed a song with three tags and a query that matches its title.
  2. Call the search service with a query such as "Crown Heights".
  3. Count how many results correspond to that same song.
- Observed behavior: The song appeared three times in the search results for the same query.
- Expected behavior: The song should appear exactly once, even when it has multiple tags.

## Bug 3 — Playlist retrieval drops the last song
- Issue: The last song in a playlist never shows up.
- How you reproduced it:
  1. Create a playlist with five songs and assign positions 1 through 5.
  2. Call the playlist retrieval service for that playlist.
  3. Compare the returned list length and titles to the playlist contents.
- Observed behavior: The service returned only four songs, and the last entry was missing.
- Expected behavior: All five playlist songs should be returned in the correct order.

## Verification evidence
- Reproduced via:
  - `python -m pytest -q tests/test_streaks.py tests/test_search.py tests/test_playlists.py`
- Result: 3 failures were observed before any fix was applied.
