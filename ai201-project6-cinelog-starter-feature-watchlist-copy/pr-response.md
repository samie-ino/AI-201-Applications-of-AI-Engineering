# PR Response Doc — CineLog Watchlist Feature

## AI Usage
<!-- Fill in at the end — how you used AI tools during this project -->
For Comments 4 and 5, I wrote a first draft of each position, then used AI as a devil's advocate: "What counterargument would a careful code reviewer raise against this position? What tradeoff am I not acknowledging?" against each draft independently.

- **Comment 4:** The AI pushed back on two points — that "want to watch" can be at least as revealing as "already watched" (not less, as I'd assumed), and that privacy-by-default isn't just a UX preference for an app with EU users, it maps to a real compliance principle (GDPR's data-protection-by-design/by-default). Both were real gaps, not restatements of what I'd already said, so I revised the response to acknowledge them and to propose an onboarding opt-in prompt as a fast-follow rather than presenting the current default as a closed question.
- **Comment 5:** The AI challenged my "newest = most relevant" assumption by pointing out that watchlists (unlike collections) are often bulk-populated in one session, which makes recency a weak signal, and that watchlists grow larger and live longer than collections, which makes alphabetical findability matter *more* over time, not less. I hadn't accounted for either case, so I revised the response to treat the `?sort=` parameter less as a hypothetical future nice-to-have and more as the real resolution to the disagreement.

I did not ask AI to write either position from scratch — both drafts were mine before the stress-test pass, and I only incorporated critiques that pointed at genuine gaps rather than accepting restated points.

- **Commit format check:** Before finalizing, I checked the `git log --oneline` output against CONTRIBUTING.md's own prefix table (`feat`/`fix`/`test`/`docs`/`refactor`/`chore`) rather than assuming the first draft was right. That review caught two mismatches: the rename commit was originally prefixed `fix:`, but a pure rename with no behavior change is what CONTRIBUTING.md defines `refactor:` for, so I reworded it. The sort-order commit was originally prefixed `feat:`, but it changes existing behavior rather than adding a new capability, so I reworded it to `fix:`. Both rewords were done via a real `git rebase -i` reword, not a squash-and-recommit.

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
**My position:** I'm keeping `public = db.Column(db.Boolean, default=True)` as-is. I'm optimizing for the social/discovery mechanic that is CineLog's core value proposition, not for privacy-by-default.

**Reasoning:** CineLog is described in its own README as "a community film tracking app" — the product's differentiation from a plain checklist app is that other users can see what you're watching and want to watch. A watchlist entry is also lower-sensitivity than a `CollectionEntry`: it records intent ("I want to see this"), not an opinion or a rating, so the exposure risk of a default-public watchlist is smaller than it would be for, say, a public-by-default rating or review. There's also a cold-start argument specific to a *new* feature: if watchlist entries default to private, most users will never discover the visibility toggle at all (most users don't proactively open settings for a feature they didn't know existed), and the social layer this feature is meant to feed — activity feeds, "friends want to watch this too," recommendations — stays empty during the exact window when engagement matters most for the feature to take off.

**Tradeoff acknowledged:** Defaulting to public is a real privacy-by-default violation of least-surprise: a user who doesn't read documentation or visit settings can have their watchlist entries visible to others before they've made an active choice about it. This could matter for a film someone doesn't want known (sensitive subject matter, a surprise gift for a partner who might see it, etc.), and "public unless you know to change it" places the burden on the user rather than the platform. If we ever have evidence that this surprises users in practice (support tickets, a privacy complaint), that's a signal to revisit the default — but I'd address it with clearer onboarding messaging (e.g., a one-time notice when the first watchlist entry is added) rather than flipping the default and re-introducing the cold-start problem.

*Revised after stress-testing this position (see AI Usage):* the argument above understates two things. First, "want to watch" can be at least as revealing as "already watched" — it shows a live, unfiltered interest before the person has had any chance to reconsider or contextualize it, so I'm not confident the sensitivity gap between a watchlist and a collection is as wide as I first argued. Second, privacy-by-default isn't only a UX nicety in a community app that could have EU users — regimes like GDPR's "data protection by design and by default" principle treat public-by-default as something you need a specific justification for, not a free starting point. I still land on keeping `True` for this PR because the feature has no real users yet and the cold-start problem is concrete today while the compliance exposure is hypothetical, but a stronger version of this default would pair it with an explicit onboarding opt-in prompt ("Share your watchlist with others?") rather than a silent boolean — that gets most of the discovery benefit without the silent-default problem, and I'd push for that as a fast-follow rather than treating the current implementation as final.

## Comment 5 — Sort order
**My position:** I implemented the maintainer's preference — `get_watchlist()` now sorts by `date_added` descending (newest first), matching `get_collection()`'s ordering, replacing the previous `Film.title.asc()` alphabetical sort.

**Reasoning:** Two lists that represent "things attached to a user over time" (collection entries and watchlist entries) should behave the same way unless there's a specific reason for them to diverge — a client consuming both endpoints shouldn't have to remember that one is chronological and the other is alphabetical. Recency is also more useful here than alphabetical order: a "want to watch" list is inherently about what's top of mind *right now*, and burying the film someone added an hour ago under "A" titles works against the point of a watchlist — the newest addition is usually the one the user most wants to act on next.

**Engagement with reviewer's point:** Alphabetical does have a real advantage the maintainer's preference gives up: on a long watchlist, alphabetical order makes it fast to jump to a specific known title, while chronological order requires a linear scan or a client-side search/filter. I don't think that's enough to keep alphabetical as the *default* sort, since it optimizes for a "look something up" use case at the expense of the more common "what's new / what's next" use case — but it's a legitimate reason a future PR might add a `?sort=alpha` query param rather than treating this as fully settled.

*Revised after stress-testing this position (see AI Usage):* my "top of mind" argument is weaker than I first gave it credit for in two cases I hadn't accounted for. A collection tends to grow one entry at a time as someone finishes a film, so "most recent" reliably means "most relevant right now" — but a watchlist is often bulk-populated in a single browsing session (e.g., adding a dozen films from a "best of the decade" list at once), and in that scenario "newest first" clusters near-identical timestamps that don't carry a meaningful priority signal. And a watchlist is longer-lived than a collection — it isn't cleared as items get watched the way a collection accumulates finished films, so it can grow into the hundreds over months, which is exactly when alphabetical findability starts to matter *more*, not less. That's a real argument the "consistency with `get_collection`" framing doesn't answer. I'm still implementing date-added descending for this PR because it's the maintainer's stated preference and the simpler behavior to ship correctly under review, but I'm treating the `?sort=` follow-up less as a nice-to-have and more as the actual resolution to this disagreement — chronological and alphabetical are each right for a different use case, and the honest fix is letting the client choose rather than the service picking one winner permanently.

## Comment 6 — Rebase
**What conflicted:** I ran `git fetch origin && git rebase origin/main` on `feature/watchlist`. `main` had moved ahead with `refactor: migrate film IDs from integer to UUID` (`Film.id` went from `db.Integer` to `db.String(36)`, and `CollectionEntry.film_id` was updated to match) plus a `.gitignore` commit. Git reported "Successfully rebased" with **no conflict markers at all** — but that was misleading. The commit that originally added `WatchlistEntry` to `models.py` landed in the same region of the file that the UUID refactor touched, and git's merge silently resolved it by dropping the `WatchlistEntry` class entirely (`git diff` between that replayed commit and its new parent came back empty). Nothing in the rebase output flagged this — I only found it because `pytest` failed to collect `tests/test_watchlist.py` with `ImportError: cannot import name 'WatchlistEntry' from 'models'`.

**How I resolved it:** Re-added the `WatchlistEntry` class to `models.py`, this time with `film_id = db.Column(db.String(36), db.ForeignKey("film.id"), nullable=False)` instead of `db.Integer`, matching `Film.id`'s new UUID type and the same pattern `CollectionEntry.film_id` already uses post-refactor. I then swept the rest of the watchlist code for leftover integer-ID assumptions from the pre-refactor branch: the `film_id (int)` docstring in `add_to_watchlist()` (now `film_id (str): UUID of the film.`), the `Body: { "film_id": <int> }` docstring in `routes/watchlist/watchlist.py` (now `"<uuid>"`, matching `routes/collection.py`'s convention), and `tests/test_watchlist.py`'s `fake_film_id = 999999` (now a fake UUID string, `"00000000-0000-0000-0000-000000000000"`, matching `test_collection.py`'s pattern).

**How I verified no conflict remains:** Ran `pytest tests/ -v` — all 5 tests pass. Then manually exercised the full flow in a Python shell: created a `User` and `Film` (confirming `film.id` is now a UUID string), called `add_to_watchlist()` and `get_watchlist()` with that UUID, and confirmed `AlreadyInWatchlistError` fires correctly on a second add — all working with real UUIDs rather than integers. Finally, ran `git log --merges origin/main..HEAD`, which returned nothing, confirming a linear history with no merge commits in the range unique to this branch (the one merge commit visible in `git log --graph` belongs to `main`'s own pre-existing history, not something introduced by merging `main` into the feature branch).

## Final Commit History

<!-- TODO: after pushing, run `git log --oneline` in your own terminal and paste
     a real screenshot here, e.g.: ![git log --oneline](./git-log-screenshot.png) -->

`git log --oneline` on `feature/watchlist` (rebased onto `main`, no merge commits in this branch's own range) as of the last commit before this doc was added:

```
bc556b6 fix: migrate WatchlistEntry film_id to UUID after rebasing onto main
ebab210 fix: sort get_watchlist by date added instead of alphabetically
1b2d31f fix: add missing Film-WatchlistEntry relationship
ece6ca7 test: add test for nonexistent film_id in add_to_watchlist
a044659 fix: add deduplication check to prevent duplicate watchlist entries
e3df718 refactor: rename save_to_watchlist to add_to_watchlist per naming convention
d020ead feat: add watchlist model and add_to_watchlist endpoint
```

Plus this doc's own commit on top: `docs: add pr-response.md with review responses and PR description`.

(`git log --merges origin/main..HEAD` returns nothing — the only merge commit reachable from this branch belongs to `main`'s own pre-existing history, not something introduced by merging `main` into the feature branch.)

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->

### What this PR does
Adds a watchlist feature to CineLog: users can save films they want to watch later (distinct from the existing collection, which tracks films already watched). A `WatchlistEntry` links a user to a film with a `date_added` timestamp and a `public` visibility flag. Two endpoints: `GET /watchlist/<user_id>` returns a user's watchlist (newest first), and `POST /watchlist/<user_id>/add` adds a film to it.

### Design decisions
- **Default visibility (`public=True`):** New watchlist entries default to public rather than private. This optimizes for CineLog's core social/discovery mechanic and avoids a cold-start problem where a brand-new feature ships invisible-by-default and never gets used. The tradeoff — this is a real privacy-by-default deviation, and "want to watch" can be as revealing as "already watched" — is acknowledged in Comment 4 below, along with a proposed onboarding opt-in prompt as a fast-follow.
- **Sort order (`date_added` descending):** `get_watchlist()` sorts newest-first, matching `get_collection()`'s ordering, rather than alphabetically by title. This is discussed in Comment 5 below, including where the "newest first" argument is weaker (bulk-added entries, very long-lived watchlists) and why a future `?sort=` parameter is likely the real long-term answer rather than picking one default forever.

### How to manually test
1. `pip install -r requirements.txt`
2. `python app.py` (starts on `http://localhost:5000` with a local SQLite DB)
3. Create a user and a film via the existing `films`/collection setup (or directly in a Python shell via `db.session.add(...)`, as done throughout this PR's verification steps).
4. Add a film to the watchlist:
   ```
   POST /watchlist/<user_id>/add
   Body: { "film_id": "<uuid>" }
   ```
   Expect `201` with the new entry (including `public: true` by default).
5. Repeat the same request with the same `user_id`/`film_id` — expect it to fail with `AlreadyInWatchlistError` (no duplicate row created).
6. `GET /watchlist/<user_id>` — expect the film(s) back sorted by `date_added` descending (add a second film and confirm it appears first).
7. Run the automated suite: `pytest tests/ -v` — all 5 tests should pass (4 collection tests + `test_add_to_watchlist_nonexistent_film_raises`).
