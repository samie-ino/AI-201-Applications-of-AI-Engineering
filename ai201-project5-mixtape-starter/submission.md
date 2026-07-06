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

---

## Issue #5 — The last song in a playlist never shows up

**How I reproduced it.** Ran `pytest tests/test_playlists.py`. `test_playlist_returns_all_songs` failed (`assert 4 == 5`) and `test_playlist_returns_songs_in_order` failed (returned `["Track 1"…"Track 4"]`, missing `"Track 5"`). The fixture seeds a playlist with five songs at positions 1–5; retrieval returned only the first four. I confirmed the missing item is always the *last* one by position, not a random omission.

**How I found the root cause.** Call chain from the README: `GET /playlists/<id>/songs` → `routes/playlists.py` → `get_playlist_songs()` in [playlist_service.py](ai201-project5-mixtape-starter/services/playlist_service.py). The SQL is correct — it joins `playlist_entries`, filters by `playlist_id`, and orders `asc(position)`. The tell was the very last line, [playlist_service.py:66](ai201-project5-mixtape-starter/services/playlist_service.py#L66): `return [song.to_dict() for song in songs[:-1]]`. The `[:-1]` slice drops the final element of an already-correct, correctly-ordered list. The function's own docstring says "returns all songs in the playlist," which directly contradicts the slice.

**The root cause.** After the query returns all N songs in position order, the list comprehension iterates over `songs[:-1]` — a slice that excludes the last element — so exactly one song, the highest-position one, is always omitted. There was nothing wrong with the query or the ordering; the truncation was purely in the Python slice applied to the result.

**My fix and side-effect check.** Changed `songs[:-1]` to `songs` so all rows are serialized. Side-effect check: re-ran `test_playlists.py` — all 3 pass, including `test_empty_playlist_returns_empty_list`. That empty-playlist case is the important other side of the boundary: on an empty list `[]`, both `[][:-1]` and `[]` evaluate to `[]`, so removing the slice does not introduce an index error or change the empty-playlist behavior. Ordering is unaffected because the `order_by(asc(position))` clause was never touched.

**AI usage.** I gave the AI the `get_playlist_songs` function and asked "what edge cases could make this return fewer rows than the query fetched?"; it flagged the `[:-1]` slice, which matched what I had already spotted reading the last line. Diagnosis and fix verified by re-running the tests myself.

---

## Issue #2 — Friends Listening Now shows people from yesterday

**How I reproduced it.** There was no existing test for the feed, so I wrote a small repro script (`scratchpad/repro_feed.py`): create a user `me` with one friend, insert a single `ListeningEvent` for the friend timestamped **20 hours ago**, then call `get_friends_listening_now(me.id)`. With today being 2026-07-06, the 20h-old event lands on **2026-07-05 (yesterday)**. The feed returned that friend (`feed length = 1`) — a person from yesterday appearing in a feed labeled "Listening Now." That matches the reported symptom.

**How I found the root cause.** Call chain: `GET /<user_id>/listening-now` → `routes/feed.py` → `get_friends_listening_now()` in [feed_service.py](ai201-project5-mixtape-starter/services/feed_service.py). Reading the function, the recency filter is `ListeningEvent.listened_at >= cutoff` where `cutoff = datetime.now(timezone.utc) - RECENT_THRESHOLD`, and `RECENT_THRESHOLD = timedelta(hours=24)` at [feed_service.py:13](ai201-project5-mixtape-starter/services/feed_service.py#L13). The filter direction and the `>=` comparison are correct; the defect is the *size* of the window. A rolling 24-hour window, by definition, reaches back into the previous calendar day, so "Listening Now" was really "listened at any point in the last day."

**The root cause.** The recency boundary for the "Listening Now" feed was set to 24 hours. Because the cutoff is `now - 24h`, any friend whose most recent listen was up to a full day ago still satisfied `listened_at >= cutoff` and was included. "Listening Now" is meant to reflect friends who are *currently or very recently* active, so a day-long window is far too wide and pulls in yesterday's activity. It is a boundary-value bug: the threshold constant, not the comparison logic, was wrong.

**My fix and side-effect check.** I changed `RECENT_THRESHOLD` from `timedelta(hours=24)` to `timedelta(minutes=15)` (roughly the span of a few songs — "actively listening right now") and added a comment explaining the intent. To verify both sides of the boundary I added `tests/test_feed.py`: `test_recent_listen_appears` (a friend who listened 5 minutes ago **does** appear) and `test_yesterday_listen_does_not_appear` (a friend who listened 20h ago **does not**). Side-effect check: `get_activity_feed()` is documented as *not* recency-filtered and does not reference `RECENT_THRESHOLD`, so it is unaffected — I locked that in with `test_activity_feed_still_shows_older_events`, which confirms the older event still surfaces there. Re-ran the repro script: feed length is now 0 for the 20h-old event. Full suite: 16 passed.

**AI usage.** I asked the AI to explain the difference between a rolling `now - timedelta` window and a same-calendar-day filter once I'd narrowed the bug to the `cutoff` computation, to sanity-check that shrinking the constant (rather than switching to a date-equality filter) was the smaller, correct fix for "Now" semantics. The reproduction, the choice of window, and the verification tests were mine.

---

## Verification — final state

```
$ python -m pytest tests/ -q
................                                                          [100%]
16 passed
```

All three fixes are on branch `bugfix/mixtape`, each in its own commit:
- `fix: remove spurious Sunday guard that reset listening streak` (Issue #1)
- `fix: return all playlist songs instead of dropping the last one` (Issue #5)
- `fix: scope "Friends Listening Now" to a recent window, not 24h` (Issue #2)
