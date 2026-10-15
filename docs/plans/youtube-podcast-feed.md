# Plan: Genadi Valdberg lectures as a public podcast

## Task
Genadi Valdberg's YouTube channel (`@GenadiValdberg`, `UC4pFACFhLkbr4rbZVbm5jag`) has about 1054 lectures, roughly 473 hours in total. The goal is to give his audience a podcast feed they can add to any podcast app. It should contain the archive plus new videos, update once a day, and need no server. It is non-commercial. The author will be contacted once a working version is ready, so the feed must be good enough to show him, while sharing it widely waits for his agreement.

## Non-goals
- **Live streams:** not needed.
- **Submitting to Apple Podcasts, Spotify or Yandex Music:** only after the author agrees. The feed will already include everything those directories require, so submitting is a manual step later.
- **One feed per playlist (topic):** possible later.
- **Updates within minutes of a new upload:** once a day is enough.
- **Reusing feed-master** (github.com/umputun/feed-master): its channel source is YouTube's channel RSS, which lists only the ~15 most recent videos, and it needs a server that is always on.

## Decisions & rationale
| Decision | Why | Rejected |
|---|---|---|
| A scheduled GitHub Actions job, once a day, **plus a manual run from a laptop** with the same command | No server; the laptop is the fallback if the job breaks, the cookies expire, or YouTube blocks runners again | feed-master on a VPS |
| **YouTube login cookies** of a separate Google account, stored as the repo secret `YT_COOKIES` | Phase 1: anonymous downloads from runners fail with `LOGIN_REQUIRED` ("Sign in to confirm you're not a bot"), with and without a PO token; with cookies they succeed. feed-master uses cookies in production too. A separate account keeps the ban and leak risk away from a personal account | PO-token provider (tested: blocked; not needed together with cookies); laptop as the main runner (needs the Mac to be on); residential proxy (paid, gray area); self-hosted runner (unsafe on a public repo) |
| ffmpeg installed wherever yt-dlp runs | Without it yt-dlp writes a DASH m4a ("Only some players support this container"). With it yt-dlp repackages the file into a normal m4a, without re-encoding, which some podcast players need for correct seeking and duration | Shipping the DASH m4a |
| **Public** GitHub repo (earlier draft: private) | The audience is public, so nothing needs hiding. Unlimited free minutes. Secrets stay in GitHub Secrets and are hidden in logs | Private: its only advantage was keeping the project hard to find |
| A daily keepalive call in the workflow | GitHub disables scheduled workflows in a public repo after 60 days with no repo activity. The job doesn't commit, so it would stop quietly | Bot commits every month: they add noise to the history |
| Cloudflare R2 for the audio files, `feed.xml`, `state.json`, `cover.jpg` | Downloads are free, which matters with many listeners; 10 GB free; S3-compatible | GitHub Releases (using GitHub as a media CDN is against its intended use), GitHub Pages (1 GB per site, 100 MB per file) |
| **A custom domain** for the public URL (earlier draft: r2.dev): `podcast.sibarit.org`, minimum TLS 1.2 | r2.dev is rate-limited and Cloudflare says it isn't for production. The feed URL is what subscribers store, so changing it later loses them. `sibarit.org` is short, takes the word from the channel name in Russian spelling, and doesn't use the author's name before he agrees; the subdomain leaves the root free for a page for listeners | r2.dev (testing only); `zapiski-sibarita.com` (long); TLS 1.3 minimum (shuts out older devices) |
| Daily run at 21:17 UTC | The last 15 videos were published between 08:12 and 19:39 UTC, about once a week; a run after that window gets a new video into the feed the same day. Minute 17 avoids the top of the hour, when GitHub's scheduler is busiest | 05:17 UTC (runs before any upload, so every video waits 10–21 hours) |
| Cover: the channel avatar at 1400 px, committed as `cover.jpg` and uploaded by every run | Same image as on YouTube; 1400 px is Apple's minimum and only 151 KB; uploading it every run restores it if the bucket loses it | The 3000 px variant (most likely upscaled) |
| State in R2, not in the repo | The laptop run then needs no git pull/commit/push; the repo stays code only | `state.json` committed by the job |
| A conditional write of `state.json` (`If-Match` on its ETag) | A laptop run and a GitHub run at the same time must not overwrite each other's progress. The second writer fails and stops | Hoping they never overlap |
| Full archive, newest first, 50 per daily run | Storage ~$0.26 per month; the feed is useful from day one; low profile with YouTube | Only recent videos |
| Original Russian audio track, chosen explicitly | Some videos have AI-dubbed `en-US` tracks (seen on `2NgIPVQbK8g`) | yt-dlp's default choice |
| **Titles from YouTube oEmbed** (`youtube.com/oembed?url=…`) | Returns the original title in every request language (tested with en, ru, de), including mixed titles like "«Роза мира», Leon Madoff и…". yt-dlp's default listing returned auto-translated English titles for 271 videos, and `lang=ru` could translate an English original | Titles from the yt-dlp listing |
| Descriptions from yt-dlp with `lang=ru` | No neutral source for descriptions exists; `lang=ru` matches the channel's language | Default (English) metadata, which may be auto-translated |
| Credit the author: each episode links to its original video, and the feed links to the channel | Fair to the author, and it sends listeners to his channel | — |
| Python 3.12 + `uv` + yt-dlp used as a library | yt-dlp is Python | Go |

## Assumptions
- **Audio format:** YouTube's original m4a, format `140` (~129 kbps, ~27 GB in total, ~$0.26 per month), repackaged by ffmpeg but not re-encoded. Set in config; format `139` (~49 kbps, ~10 GB, fits the free tier) is the alternative.
- **Short videos:** videos under 2 minutes are skipped (`min_duration` in config).
- **Failed videos** (removed, members-only): marked as failed in `state.json` and skipped after 3 attempts.
- **The laptop** needs `brew install uv deno ffmpeg` once (the system Python is 3.9, and current yt-dlp needs 3.10+). A home IP needs no cookies (downloads from the Mac worked without them), so `YT_COOKIES_FILE` is optional there.
- **Cookies last weeks to months.** When they expire, the daily job fails and GitHub emails the repo owner. Renewing them takes about 5 minutes: in a private window, log in with the separate account, open `youtube.com/robots.txt`, export the cookies with "Get cookies.txt LOCALLY", close the window without logging out, then run `gh secret set YT_COOKIES < cookies.txt` and delete the file.
- **R2 supports `If-Match` on PutObject.** Phase 4 checks this; if it doesn't, a lock object in the bucket is used instead.
- **The keepalive works:** calling the "enable workflow" API resets the 60-day counter. This is the method of `gautamkrishnar/keepalive-workflow`. GitHub also emails a warning before it disables a workflow.

## Phases

### Phase 1 — Public repo skeleton + GitHub Actions download test (done)
- **Goal:** find out whether YouTube allows downloads from GitHub runners, and what setup they need.
- **Changes:** `git init`; the public repo `BuHogeJI2/sybarite-feed` (branch `master`); `.gitignore` (includes `.env`, `tmp/`); `.github/workflows/smoke.yml` (manual run only) that installs `yt-dlp` and `deno` and downloads video `2NgIPVQbK8g` with `-f "bestaudio[ext=m4a][language=ru]"`.
- **Result:**
  - Listing the channel works from runners (1054 videos), with no extra setup.
  - Plain and PO-token downloads both fail with `LOGIN_REQUIRED` (run 38590073026).
  - With cookies (`YT_COOKIES` secret), the download works both with and without the PO-token provider: format `140-1`, `language=ru`, the title "Трусость или мудрость? №184", 27.4 MB in about 5 seconds (run 38709646013).
  - yt-dlp warned that it wrote a DASH m4a because ffmpeg is missing on the runner.
- **Commits:** `ci: add YouTube download smoke test`, `ci: test YouTube download with cookies`

### Phase 2 — Channel listing, metadata and download (done)
- **Goal:** pick the next videos to process and download one with the original metadata.
- **Changes:**
  - `pyproject.toml` (`yt-dlp[default]`, which includes the JavaScript challenge solver, and pytest) and `config.toml` (channel, format, `min_duration`, batch size, feed metadata, `base_url`);
  - `sybarite_feed/channel.py`: flat listing of `https://www.youtube.com/@GenadiValdberg/videos`;
  - `sybarite_feed/select.py`: a pure function that picks the next batch (newest first; skips done items, short videos, items failed 3 times);
  - `sybarite_feed/metadata.py`: the oEmbed title;
  - `sybarite_feed/download.py`: downloads the Russian audio track (with the cookie file from `YT_COOKIES_FILE` when it is set; ffmpeg repackages the DASH m4a) and returns an `Episode` (id, original title, description with `lang=ru`, upload date, duration, size, mime type, video URL);
  - `tests/test_select.py`, and `tests/test_metadata.py` with a recorded oEmbed response.
- **Verification:** `uv run pytest`; `uv run python -m sybarite_feed download --id 2NgIPVQbK8g --out ./tmp` gives Russian audio and the title "Трусость или мудрость? №184", and the log has no "writing DASH m4a" warning.
- **Done when:** the tests pass and the file is correct.
- **Result:**
  - 10 tests passed. The download picked track `140-1` «Русский (оригинальная)» with the original title, a Russian description and the publish date. There was no DASH warning: ffmpeg repackaged the file (27,455,537 → 27,436,185 bytes), and `ffprobe` reads it as a normal m4a.
  - Differences from the plan:
    - `Episode` lives in `sybarite_feed/episode.py`, because `download` already returns it.
    - `audio_format` is the selector `bestaudio[ext=m4a][language=ru]/bestaudio[ext=m4a]` instead of `140`: with several audio tracks, `140` is ambiguous (`140-0` English, `140-1` Russian). Old single-track videos are labeled `[ru]` too.
    - `config.toml` got only the `[channel]` section; the feed settings came in Phase 3 and `base_url` in Phase 4.
    - `YT_COOKIES_FILE` is read by the command, not inside `download.py`.
    - Extra tests: `tests/test_channel.py` and `tests/test_download.py` (publish date).
- **Commit:** `feat: list channel videos and download audio`

### Phase 3 — Directory-ready feed generation (done)
- **Goal:** a valid feed that Apple, Spotify and Yandex would accept.
- **Changes:**
  - `sybarite_feed/state.py`: the `State`/`Episode` model and JSON load/save;
  - `sybarite_feed/rss.py`: `State + config → feed.xml`. It covers RSS 2.0 + iTunes tags, `language` = `ru`, `itunes:author`, `itunes:owner` with an email, `itunes:category`, `itunes:explicit`, `itunes:image`, and a channel link. Per episode: `enclosure` (with length and type), `guid` = video ID, `pubDate`, `itunes:duration`, and a description ending with a link to the original video;
  - `tests/test_rss.py` (escaping of Cyrillic text and `&`, date format, required tags).
- **Verification:** `uv run pytest`; check a generated sample at castfeedvalidator.com or podba.se/validate.
- **Done when:** the tests pass and the validator shows no errors.
- **Result:**
  - 18 tests passed. A feed built from the real downloaded episode passed the W3C Feed Validator with 0 errors; the one warning (self link doesn't match) came only from pasting the XML instead of giving a URL. The Apple-specific validators need a public URL, so the live feed was checked in Phase 4 instead.
  - `[feed]` in `config.toml`: title «Записки воинствующего сибарита» (the channel's own name), author «Геннадий Вальдберг», category Society & Culture → Philosophy. `itunes:owner` is written only when `owner_email` is set, and it stays empty until directory submission.
  - Episode descriptions become simple HTML: paragraphs and line breaks are kept, the text is escaped, and a link «Видео на YouTube» is added at the end.
  - `build_feed` takes `base_url` as a parameter; it moved into config in Phase 4. Shared test data lives in `tests/factories.py`.
- **Commit:** `feat: generate podcast RSS from state`

### Phase 4 — R2 storage, `run` command, laptop fallback (done)
- **Goal:** one command for the whole update that works the same on a runner and on the laptop.
- **Manual setup:**
  - a Cloudflare account (R2 may ask for a payment method even on the free tier);
  - a bucket `sybarite-feed` with r2.dev access on for testing;
  - an API token with Object Read & Write limited to that bucket.
- **Changes:**
  - `sybarite_feed/storage.py`: `LocalStorage` (for tests) and `R2Storage` (boto3 with the R2 endpoint), with `put_state(if_match=etag)`;
  - `sybarite_feed/run.py`: load the state and its ETag, select a batch, then for each video upload `audio/<id>.m4a` → save the state with a conditional write → rebuild `feed.xml`. Audio goes up before the state, and the state before the feed, so the feed never points to a missing file. The state is saved after every episode, so a run that times out loses nothing. A conflict stops the run;
  - `.env.example` (committed) listing `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, and the optional `YT_COOKIES_FILE`. The real `.env` is gitignored;
  - `README.md` section "Run from laptop": `uv run --env-file .env python -m sybarite_feed run --limit N`;
  - `tests/test_run.py` covering order of writes, resume after a failure, and a state conflict.
- **Verification:**
  - `uv run pytest`;
  - on the laptop, run `run --limit 3` against R2, then subscribe to `https://<bucket>.r2.dev/feed.xml` in a podcast app and play an episode, seeking inside it;
  - start two runs at once and confirm that one stops with a conflict.
- **Done when:** 3 episodes play; running again with `--limit 0` changes nothing; the conflict check works.
- **Result:**
  - 31 tests passed. R2 rejects a stale `If-Match` and a repeated `If-None-Match: *` with `412 PreconditionFailed`, so the lock-object fallback isn't needed.
  - `run --limit 3` added 3 episodes; the feed played in Apple Podcasts. The files have the right content types, range requests return `206`, and the live feed passed the W3C validator with 0 errors and 0 warnings.
  - `--limit 0` left `state.json` with the same ETag. Of two runs started at once, the second to save got `412`, stopped with exit code 1, and the state stayed correct.
  - Speed on the laptop: ~19 s to download from YouTube, ~68 s to upload 27.7 MB to R2, limited by the home upload speed (~3 Mbit/s).
  - Differences from the plan:
    - Storage has a generic interface (`get`, `put` with `if_match` / `if_none_match`, `upload_file`) instead of `put_state`.
    - **Failure rule:** a failure counts against a video only when a later download in the same run succeeds. After 3 failures in a row, the run stops without counting anything and exits with code 1. This way expired cookies or a YouTube block can't use up the attempts of a whole batch.
    - Cache headers: audio `immutable`, `feed.xml` 5 minutes, `state.json` `no-store`.
    - boto3 runs with `request_checksum_calculation="when_required"`, as Cloudflare advises for boto3 1.36+.
    - `state.json` is publicly readable from the bucket; it holds only episode metadata and failure counts.
- **Commit:** `feat: upload episodes and feed to R2`

### Phase 5 — Daily workflow (done, waiting for the first scheduled run)
- **Goal:** daily updates on GitHub with no manual work.
- **Changes:** `.github/workflows/daily.yml` with:
  - `schedule` (once a day) plus `workflow_dispatch` with a `limit` input;
  - `concurrency: { group: feed, cancel-in-progress: false }`;
  - the setup proven in Phase 1: Python, `deno`, ffmpeg (`apt-get install ffmpeg`), and the `YT_COOKIES` secret written to `$RUNNER_TEMP/cookies.txt` and passed as `YT_COOKIES_FILE`; no PO-token provider;
  - R2 secrets from GitHub Secrets;
  - `timeout-minutes` below the 6-hour limit;
  - a keepalive step (`permissions: actions: write`; calls the enable-workflow API);
  - only `schedule` and `workflow_dispatch` triggers. No `pull_request_target`, so forks never get the secrets.

  Delete `smoke.yml`. Add a `README.md` section "Refresh cookies" with the renewal steps from Assumptions.
- **Verification:** one manual run with `limit=5`; `state.json` and `feed.xml` in R2 are updated and the new episodes show up in the app.
- **Done when:** a scheduled run has worked unattended, and the backfill is in progress at 50 videos per day.
- **Result:**
  - `daily.yml` runs at 21:17 UTC (see Decisions). Actions: `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.0`, `denoland/setup-deno@v2`, all on Node 24. `setup-uv` publishes no short `v10` tag, so it is pinned to the full version.
  - The update runs as `uv run --locked --no-dev`, with `timeout-minutes: 90`.
  - The R2 keys were stored as repo secrets with `gh secret set -f .env`, so the values were never printed.
  - The first run (38734898935) failed at setup because of the `v10` tag. The manual run 38735011226 with `limit=5` added 5 episodes with 0 failures, about 10–15 s per video on the runner plus the 5–15 s pauses; the keepalive step passed.
  - Still open: the first scheduled run (from 2026-10-15, 21:17 UTC).
- **Commits:** `ci: add daily feed update workflow`, `ci: pin setup-uv to an existing version`

### Phase 6 — Public launch setup (done, waiting for the check in a second app)
- **Goal:** a final feed URL and a page for listeners, ready to show the author.
- **Manual setup:** a domain on Cloudflare DNS (~$10/year), connected to the bucket as a custom domain.
- **Changes:** `base_url` in `config.toml` (it changes the enclosure URLs; the guids stay, so episodes aren't duplicated); `cover.jpg` (square, 1400–3000 px); `README.md` for listeners (the feed URL and how to add it in common apps).
- **Verification:** the validator passes on the new URL; adding the feed to Apple Podcasts and AntennaPod by URL works.
- **Done when:** the feed on the custom domain plays in two apps.
- **Result:**
  - The cover was done before the domain: the channel avatar at 1400 px, `cover = "cover.jpg"` in `[feed]`, uploaded at the start of every run.
  - `sibarit.org` was bought through Cloudflare Registrar. The R2 custom domain `podcast.sibarit.org` (minimum TLS 1.2) became usable about an hour after the purchase; the R2 dialog keeps **Continue** disabled until the zone is active.
  - Checks on `https://podcast.sibarit.org`:
    - `feed.xml`, `cover.jpg` and the audio return `200` with the right headers, and range requests return `206`;
    - the certificate covers the subdomain; TLS 1.2 is accepted and TLS 1.1 is rejected.
  - After `base_url` changed, a `--limit 0` run republished the feed with 29 episodes and no r2.dev links. The W3C validator: valid, 0 errors, 0 warnings, at the new URL.
  - `README.md` has a section «Как слушать» (in Russian, for listeners): the feed URL and how to add it in Apple Podcasts, Pocket Casts, Overcast and AntennaPod. Spotify and Yandex Music can't add a podcast by URL.
  - Still open: checking playback in a second app, then turning off the bucket's r2.dev URL.
- **Commits:** `feat: add channel avatar as podcast cover`, `feat: move feed to custom domain`

## Phase dependencies
| Phase | Depends on | Blocks | Parallel with | Nature of the dependency |
|---|---|---|---|---|
| 1 (done) | — | 5 | 2, 3 | `daily.yml` reuses the cookie setup proven here |
| 2 (done) | — | 4 | 1, 3 | `run.py` calls the listing, metadata and download code |
| 3 (done) | — | 4 | 1, 2 | `run.py` calls `rss.py`; `State` is defined here |
| 4 (done) | 2, 3 | 5, 6 | — | The workflow and the launch need the `run` command and the R2 bucket |
| 5 (done) | 1, 4 | — | 6 | Needs the working download setup and `run` |
| 6 (done) | 4 | — | 5 | Needs the bucket and the feed in R2; independent of where the job runs |

## Open questions
| Question | What's unclear | Why it matters | Needed by |
|---|---|---|---|
| How long do the cookies last? | Only time will tell | Sets how often they must be renewed; if it is too often, the laptop becomes the main runner | Ongoing after Phase 5 |
| Does 50 downloads a day get the account limited? | One test download says nothing about volume | If it does, lower the batch size or download the archive from the laptop | First week of Phase 5 |
| Owner email for `itunes:owner` | The project owner's or the author's | Directories (Apple, Spotify, Yandex Music) send a verification code there | Directory submission, after the author agrees |
| Does the keepalive really reset the 60-day counter? | Can only be confirmed after 60 days | Otherwise the job stops quietly; GitHub sends a warning email before that | ~60 days after Phase 5 |
