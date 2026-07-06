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

---

# Mixtape Bug Hunt — Milestone 3 Root Cause Analysis

Bugs fixed in this milestone: **Issue #1 (streak)**, **Issue #2 (Friends Listening Now)**, and **Issue #5 (playlist last song)**. Each is committed separately on the `bugfix/mixtape` branch.

> **Note on Issue #3 (search duplicates):** During Milestone 2 the search bug was listed as reproducing with three duplicate rows. On re-investigation for Milestone 3, `tests/test_search.py` actually *passes* unchanged. The `search_songs` query uses the legacy SQLAlchemy `db.session.query(Song).outerjoin(...).all()` API, which de-duplicates full mapped entities by primary key before returning them, so the `outerjoin(song_tags)` never yields visible duplicate `Song` objects. The duplicate-generating join is a real *latent* defect (it would surface if the query were rewritten to select columns, or moved to the 2.0 `select(...).scalars()` API without `.unique()`), but it does not reproduce as user-visible behavior today. Because the checkpoint requires triggering the bug and confirming it no longer reproduces, Issue #2 was fixed in its place. Issue #3 is left documented here rather than "fixed" so the RCA stays honest.

---

## Issue #1 — My listening streak keeps resetting

**How I reproduced it.** Ran `pytest tests/test_streaks.py` against the starter code. Four of five tests passed; `test_streak_increments_on_sunday` failed with `assert 1 == 2`. The test records a listen on Saturday 2024-06-15 (streak → 1) and then Sunday 2024-06-16 (a consecutive day, so streak should reach 2), but the streak stayed at 1. I confirmed the trigger is specifically *the second day being a Sunday* — the consecutive-day test using Monday→Tuesday passed, so it was not general consecutive-day logic that broke.

**How I found the root cause.** Call chain: `record_listening_event()` → `update_listening_streak(user, now)` in [streak_service.py](ai201-project5-mixtape-starter/services/streak_service.py). Reading `update_listening_streak` top-down, the branch that increments the streak is `elif days_since_last == 1 and today.weekday() != 6:` at [streak_service.py:73](ai201-project5-mixtape-starter/services/streak_service.py#L73). The `today.weekday() != 6` half of that condition was the moment it clicked — there is no reason in the documented streak rules for the increment to depend on which weekday it is. I confirmed with the Python docs that `datetime.weekday()` returns **6 for Sunday** (Monday = 0 … Sunday = 6).

**The root cause.** The increment branch required both `days_since_last == 1` *and* `today.weekday() != 6`. On any Sunday, `today.weekday()` equals 6, so the whole condition evaluated `False`, execution fell through to the `else` branch, and the streak was reset to 1 instead of incremented. As a result, a real Saturday→Sunday consecutive listen — or any streak that crossed into a Sunday — was silently reset every week. The weekday check served no purpose in the documented rules; it was an incorrect extra condition.

**My fix and side-effect check.** I removed the `and today.weekday() != 6` clause so the branch is simply `elif days_since_last == 1:`, restoring the documented rule ("listened yesterday → increment"). Side-effect check: re-ran the full `test_streaks.py` suite — all 5 pass, including `test_streak_does_not_double_count_same_day` (the `days_since_last == 0` early return still fires) and `test_streak_resets_after_skipped_day` (the `else` reset still fires when `days_since_last > 1`). Both sides of the day boundary are intact; only the spurious Sunday reset is gone.

**AI usage.** After locating line 73 myself, I asked an AI to confirm the return values of `datetime.weekday()` vs `isoweekday()` to be certain 6 = Sunday. I read the change and verified it against the passing tests myself.
