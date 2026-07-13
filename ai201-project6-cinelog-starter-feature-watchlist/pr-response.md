# PR Response Doc — CineLog Watchlist Feature

## AI Usage
<!-- Fill in at the end — how you used AI tools during this project -->

## Comment 1 — Rename
**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` in `services/watchlist_service.py`, matching the naming convention used by `add_to_collection()` in `services/collection_service.py`. Updated the one call site in `routes/watchlist/watchlist.py` (both the import and the call in `add_film()`).
**How I verified:** Ran `grep -rn "save_to_watchlist" --include="*.py" .` from the project root after the edit to confirm zero remaining references to the old name. Also ran `pytest tests/ -v` — all 4 existing tests still pass, confirming nothing else depended on the old name.

## Comment 2 — Deduplication
**What I did:** Added an `AlreadyInWatchlistError` exception and a duplicate check to `add_to_watchlist()` in `services/watchlist_service.py`, following the exact pattern in `add_to_collection()` (`services/collection_service.py`): after confirming the film exists, query `WatchlistEntry.query.filter_by(user_id=user_id, film_id=film_id).first()`, and if a row is returned, raise before ever constructing/adding the new entry. I read `add_to_collection()` first to understand that the check returns `None` for no match vs. a model instance for a match, and that the raise has to happen before `db.session.add()`/`commit()`, not after — otherwise a duplicate row would already be flushed to the DB.
**How I verified:** Wrote a throwaway script that creates a user + film, calls `add_to_watchlist()` twice with the same `(user_id, film_id)`, and confirmed the first call returns an entry while the second raises `AlreadyInWatchlistError` with no second row created. Then ran `pytest tests/ -v` — all 4 existing tests still pass. (The permanent regression test for this lives in Comment 3's new `tests/test_watchlist.py`.)

## Comment 3 — Missing test
**What I did:** Created `tests/test_watchlist.py`, modeled directly on `tests/test_collection.py::test_add_to_collection_nonexistent_film_raises`. Reused the same `app` fixture (isolated in-memory SQLite app) and a trimmed-down `sample_user` fixture (no `sample_film`, since this test intentionally never creates one). Wrote `test_add_to_watchlist_nonexistent_film_raises`, which calls `add_to_watchlist()` with a film_id that doesn't exist and asserts it raises `FilmNotFoundError` via `pytest.raises`, mirroring the collection test's structure and naming convention.
**How I verified:** Ran `pytest tests/test_watchlist.py -v` — the new test passes. Then ran the full suite with `pytest tests/ -v` — all 5 tests (4 existing + 1 new) pass, confirming the new test file doesn't break fixture isolation or collide with anything in `test_collection.py`.

## Comment 4 — Default visibility
**My position:**
**Reasoning:**
**Tradeoff acknowledged:**

## Comment 5 — Sort order
**My position:**
**Reasoning:**
**Engagement with reviewer's point:**

## Comment 6 — Rebase
**What conflicted:**
**How I resolved it:**
**How I verified no conflict remains:**

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->
