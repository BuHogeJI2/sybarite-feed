# Plan: Fix the review findings 1–6

## Task
The Codex review found problems in how the daily run handles failures, secrets and inputs:
- A malformed cookie line can print cookie values into the public Actions log.
- Three bad videos in a row block the backfill forever. After the backfill, one bad new video
  makes every daily run fail.
- Failures at the end of a run are counted, which contradicts the rule in the comment.
- yt-dlp is frozen by `uv.lock`, and YouTube changes will break it sooner or later.
- One control character in the metadata breaks the whole `feed.xml`.
- The keepalive's `actions: write` covers the job that holds the secrets, and the actions use
  tags that can change.

## Non-goals
- **#7, overlapping runs:** no lock. The only part included is publishing the feed when a run
  stops (Phase 2).
- **#8–#11:** fragments, the format fallback, deleted videos, and the ffmpeg preflight. #10 is a
  policy decision for the owner.
- Dependabot.

## Decisions & rationale
- **Failure rule (#2 and #4): test access with a known-good video instead of counting a
  streak.** When a video fails, the run downloads the **shortest episodes already in the state**,
  one at a time and at most three (`KNOWN_EPISODES_TO_TRY`), and deletes each file. At the time of
  writing the shortest is 894 s, about 14 MB. Revised after review: one fixed canary stalled every
  run once that episode was removed from YouTube.
  - One works: the failure is the video's fault. Count it now, save the state, continue.
  - All fail: YouTube access is broken. Count nothing, publish the feed, and exit red.
  - Empty state (no canary): treat it as an access failure.

  This replaces `MAX_CONSECUTIVE_FAILURES`, the `streak` list and the tail-counting block.
  Rejected:
  - Sorting errors by message text: this breaks when YouTube changes the wording.
  - A metadata-only probe (`download=False`): it passes while media requests return 403.
  - Counting every failure: expired cookies would use up the attempts of good videos.
- **Per-video failures keep the run green.** Only an access failure makes it red. A video that
  reaches `MAX_ATTEMPTS` gets an error log line.
- **Cookie check in our own code**, before yt-dlp sees the file. It copies yt-dlp's and
  `MozillaCookieJar`'s rules:
  - a header line;
  - 7 tab-separated fields;
  - `TRUE`/`FALSE` flags;
  - an empty or numeric expiry.

  Errors give only the line number. Rejected: catching yt-dlp's output, because it calls
  `write_string` directly and a logger doesn't catch it.
- **Masking:** in Actions, print `::add-mask::` for each cookie value of 8 or more characters.
  Values are escaped first (`%`→`%25`, CR→`%0D`, LF→`%0A`), because cookie values can contain
  `%`. Shorter values aren't secret, and masking them would hide common text in the log.
- **yt-dlp is updated at every run** with
  `uv sync --no-dev --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs`, and both versions are
  logged. Rejected:
  - Uploading the lock as an artifact: the logged versions are enough to reproduce a run, and an
    artifact needs one more third-party action.
  - Dependabot: it needs PRs that someone merges by hand.
- **XML safety:** remove XML 1.0 forbidden characters from the title and description **before**
  the state is saved. Also parse the feed before uploading it. Cleaning only at publish time
  would leave a bad episode in `state.json`.

## Assumptions
- Action SHAs come from `gh api` for the current tags. A `# vX.Y.Z` comment goes next to each.
- If the cookie file is set, the laptop runs the same cookie check (no masking there).

## Phases

### Phase 1 — Cookie validation and masking
- **Goal:** a bad cookie file fails with a message that contains no values, and good values are
  masked.
- **Changes:**
  - New `sybarite_feed/cookies.py`: `cookie_values(path) -> list[str]`, which raises
    `InvalidCookieFile(line_number)`.
  - `__main__.py`:
    - a new command `check-cookies PATH [--mask]` that prints the escaped `::add-mask::` lines;
    - `run` and `download` validate `YT_COOKIES_FILE` before they use it.
  - `daily.yml`: after "write cookies", add a step
    `uv run --locked --no-dev python -m sybarite_feed check-cookies --mask "$RUNNER_TEMP/cookies.txt"`.
  - New `tests/test_cookies.py`. It covers a valid file, a wrong field count, a bad expiry, bad
    flags, a missing header and `#HttpOnly_` lines. It also checks that the error text never
    contains the value, and tests the `%` escaping.
- **Verification:** `uv run pytest`. Then run `check-cookies` on a synthetic bad file and grep
  its output for the fake value; it should come back empty.
- **Done when:** the tests pass and the workflow has the check step.
- **Commit:** `fix: validate and mask YouTube cookies before use`

### Phase 2 — Canary-based failure rule
- **Goal:** bad videos are counted and skipped; only a real access failure stops the run.
- **Changes:**
  - `run.py`:
    - `_youtube_works` tries up to three of the shortest episodes;
    - count and save, or publish and return `ok=False`;
    - remove `MAX_CONSECUTIVE_FAILURES`, `streak` and the tail block.
  - `tests/test_run.py`:
    - replace `test_stops_after_consecutive_failures_without_counting`;
    - add tests: three bad videos followed by a good one (all three counted, the good one added);
      canary failing (nothing counted, feed published, `ok=False`); empty state with a failure; a
      trailing failure counted when the canary works.
  - `README.md`: one line on the rule.
- **Verification:** `uv run pytest`.
- **Done when:** the tests pass and `grep -rn MAX_CONSECUTIVE sybarite_feed tests` is empty.
- **Commit:** `fix: count failed videos only when a known video still downloads`

### Phase 3 — XML-safe text
- **Goal:** metadata can't break `feed.xml`.
- **Changes:**
  - `episode.py` gets `xml_safe(text)`, a regex for the characters outside the XML 1.0 range.
  - `download.py` uses it on the title and description.
  - `run._publish_feed` runs `ET.fromstring(feed)` before `put`.
  - Tests:
    - `xml_safe` on its own;
    - a state with an old bad episode makes `_publish_feed` raise, and the existing `feed.xml`
      stays unchanged.
- **Verification:** `uv run pytest`.
- **Done when:** the tests pass.
- **Commit:** `fix: strip XML-invalid characters from episode text`

### Phase 4 — Runtime yt-dlp upgrade
- **Goal:** each run uses the newest yt-dlp and logs which version it used.
- **Changes:**
  - `daily.yml`: a step after setup-deno that runs
    `uv sync --no-dev --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs`, then prints both
    versions with `importlib.metadata`.
  - `README.md`: how to do the same on the laptop with `uv lock --upgrade-package …`.
- **Verification:** run the same `uv sync` command locally, then `git checkout uv.lock`. After
  the push, run the workflow by hand with `limit=1` and read the version line in the log.
- **Done when:** a dispatched run logs the versions and finishes green.
- **Commit:** `ci: upgrade yt-dlp on every run`

### Phase 5 — Workflow hardening
- **Goal:** the job with the secrets has no write permission, and the actions can't change under
  us.
- **Changes:**
  - `daily.yml`:
    - top-level `permissions: contents: read`;
    - a new `keepalive` job with `needs: update`, `if: always()` and
      `permissions: actions: write`, with no checkout;
    - the three `uses:` lines pinned to SHAs.
- **Verification:** no local workflow linter is installed. After the push, run the workflow by
  hand with `limit=0`: both jobs should be green.
- **Done when:** that run is green.
- **Commit:** `ci: pin actions and isolate keepalive permissions`

## Phase dependencies
| Phase | Depends on | Blocks | Parallel with | Nature of the dependency |
|---|---|---|---|---|
| 1 | — | — | 2, 3 | — |
| 2 | — | — | 1, 3 | — |
| 3 | — | — | 1, 2 | — |
| 4 | — | — | 1–3 | Only text overlap with 1 and 5 in `daily.yml` |
| 5 | — | — | 1–3 | Pin any new `uses:` added by earlier phases (none are planned) |

Phases 4 and 5 can only be checked after a push.
