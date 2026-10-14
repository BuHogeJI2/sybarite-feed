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
| A scheduled GitHub Actions job, once a day, **plus a manual run from a laptop** with the same command | No server; the laptop is the fallback if YouTube blocks GitHub runners or the job breaks | feed-master on a VPS |
| **Public** GitHub repo (earlier draft: private) | The audience is public, so nothing needs hiding. Unlimited free minutes. Secrets stay in GitHub Secrets and are hidden in logs | Private: its only advantage was keeping the project hard to find |
| A daily keepalive call in the workflow | GitHub disables scheduled workflows in a public repo after 60 days with no repo activity. The job doesn't commit, so it would stop quietly | Bot commits every month: they add noise to the history |
| Cloudflare R2 for the audio files, `feed.xml`, `state.json`, `cover.jpg` | Downloads are free, which matters with many listeners; 10 GB free; S3-compatible | GitHub Releases (using GitHub as a media CDN is against its intended use), GitHub Pages (1 GB per site, 100 MB per file) |
| **A custom domain** for the public URL (earlier draft: r2.dev) | r2.dev is rate-limited and Cloudflare says it isn't for production. The feed URL is what subscribers store, so changing it later loses them. It must be final before anyone subscribes | r2.dev (stays for testing only) |
| State in R2, not in the repo | The laptop run then needs no git pull/commit/push; the repo stays code only | `state.json` committed by the job |
| A conditional write of `state.json` (`If-Match` on its ETag) | A laptop run and a GitHub run at the same time must not overwrite each other's progress. The second writer fails and stops | Hoping they never overlap |
| Full archive, newest first, 50 per daily run | Storage ~$0.26 per month; the feed is useful from day one; low profile with YouTube | Only recent videos |
| Original Russian audio track, chosen explicitly | Some videos have AI-dubbed `en-US` tracks (seen on `2NgIPVQbK8g`) | yt-dlp's default choice |
| **Titles from YouTube oEmbed** (`youtube.com/oembed?url=…`) | Returns the original title in every request language (tested with en, ru, de), including mixed titles like "«Роза мира», Leon Madoff и…". yt-dlp's default listing returned auto-translated English titles for 271 videos, and `lang=ru` could translate an English original | Titles from the yt-dlp listing |
| Descriptions from yt-dlp with `lang=ru` | No neutral source for descriptions exists; `lang=ru` matches the channel's language | Default (English) metadata, which may be auto-translated |
| Credit the author: each episode links to its original video, and the feed links to the channel | Fair to the author, and it sends listeners to his channel | — |
| Python 3.12 + `uv` + yt-dlp used as a library | yt-dlp is Python | Go |

## Assumptions
- **Audio format:** YouTube's original m4a, format `140` (~129 kbps, ~27 GB in total, ~$0.26 per month), no re-encoding. Set in config; format `139` (~49 kbps, ~10 GB, fits the free tier) is the alternative.
- **Short videos:** videos under 2 minutes are skipped (`min_duration` in config).
- **Failed videos** (removed, members-only): marked as failed in `state.json` and skipped after 3 attempts.
- **The laptop** needs `brew install uv deno` once (the system Python is 3.9, and current yt-dlp needs 3.10+). A home IP probably needs no PO-token provider.
- **R2 supports `If-Match` on PutObject.** Phase 4 checks this; if it doesn't, a lock object in the bucket is used instead.
- **The keepalive works:** calling the "enable workflow" API resets the 60-day counter. This is the method of `gautamkrishnar/keepalive-workflow`. GitHub also emails a warning before it disables a workflow.

## Phases

### Phase 1 — Public repo skeleton + GitHub Actions download test
- **Goal:** find out whether YouTube allows downloads from GitHub runners, and what setup they need.
- **Changes:** `git init`; a public GitHub repo; `.gitignore` (includes `.env`, `tmp/`); `.github/workflows/smoke.yml` (manual run only) that installs `yt-dlp` and `deno` and tries video `2NgIPVQbK8g` in three ways:
  1. variant A: plain `-f "bestaudio[ext=m4a][language=ru]"`;
  2. variant B: plus the `brainicism/bgutil-ytdlp-pot-provider` service container and the `bgutil-ytdlp-pot-provider` plugin;
  3. each variant prints the file size, the audio track language and the download time.
- **Verification:** run the workflow by hand from the GitHub UI and read the logs.
- **Done when:** one variant downloads the Russian track. If none does, try cookies from a throwaway account. If that fails too, the daily job runs on the laptop (launchd), which changes Phase 5 only.
- **Commit:** `ci: add YouTube download smoke test`

### Phase 2 — Channel listing, metadata and download
- **Goal:** pick the next videos to process and download one with the original metadata.
- **Changes:**
  - `pyproject.toml` (yt-dlp, pytest) and `config.toml` (channel, format, `min_duration`, batch size, feed metadata, `base_url`);
  - `sybarite_feed/channel.py`: flat listing of `https://www.youtube.com/@GenadiValdberg/videos`;
  - `sybarite_feed/select.py`: a pure function that picks the next batch (newest first; skips done items, short videos, items failed 3 times);
  - `sybarite_feed/metadata.py`: the oEmbed title;
  - `sybarite_feed/download.py`: downloads the Russian audio track and returns an `Episode` (id, original title, description with `lang=ru`, upload date, duration, size, mime type, video URL);
  - `tests/test_select.py`, and `tests/test_metadata.py` with a recorded oEmbed response.
- **Verification:** `uv run pytest`; `uv run python -m sybarite_feed download --id 2NgIPVQbK8g --out ./tmp` gives Russian audio and the title "Трусость или мудрость? №184".
- **Done when:** the tests pass and the file is correct.
- **Commit:** `feat: list channel videos and download audio`

### Phase 3 — Directory-ready feed generation
- **Goal:** a valid feed that Apple, Spotify and Yandex would accept.
- **Changes:**
  - `sybarite_feed/state.py`: the `State`/`Episode` model and JSON load/save;
  - `sybarite_feed/rss.py`: `State + config → feed.xml`. It covers RSS 2.0 + iTunes tags, `language` = `ru`, `itunes:author`, `itunes:owner` with an email, `itunes:category`, `itunes:explicit`, `itunes:image`, and a channel link. Per episode: `enclosure` (with length and type), `guid` = video ID, `pubDate`, `itunes:duration`, and a description ending with a link to the original video;
  - `tests/test_rss.py` (escaping of Cyrillic text and `&`, date format, required tags).
- **Verification:** `uv run pytest`; check a generated sample at castfeedvalidator.com or podba.se/validate.
- **Done when:** the tests pass and the validator shows no errors.
- **Commit:** `feat: generate podcast RSS from state`

### Phase 4 — R2 storage, `run` command, laptop fallback
- **Goal:** one command for the whole update that works the same on a runner and on the laptop.
- **Manual setup:**
  - a Cloudflare account (R2 may ask for a payment method even on the free tier);
  - a bucket `sybarite-feed` with r2.dev access on for testing;
  - an API token with Object Read & Write limited to that bucket.
- **Changes:**
  - `sybarite_feed/storage.py`: `LocalStorage` (for tests) and `R2Storage` (boto3 with the R2 endpoint), with `put_state(if_match=etag)`;
  - `sybarite_feed/run.py`: load the state and its ETag, select a batch, then for each video upload `audio/<id>.m4a` → save the state with a conditional write → rebuild `feed.xml`. Audio goes up before the state, and the state before the feed, so the feed never points to a missing file. The state is saved after every episode, so a run that times out loses nothing. A conflict stops the run;
  - `.env.example` (committed) listing `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`. The real `.env` is gitignored;
  - `README.md` section "Run from laptop": `uv run --env-file .env python -m sybarite_feed run --limit N`;
  - `tests/test_run.py` covering order of writes, resume after a failure, and a state conflict.
- **Verification:**
  - `uv run pytest`;
  - on the laptop, run `run --limit 3` against R2, then subscribe to `https://<bucket>.r2.dev/feed.xml` in a podcast app and play an episode, seeking inside it;
  - start two runs at once and confirm that one stops with a conflict.
- **Done when:** 3 episodes play; running again with `--limit 0` changes nothing; the conflict check works.
- **Commit:** `feat: upload episodes and feed to R2`

### Phase 5 — Daily workflow
- **Goal:** daily updates on GitHub with no manual work.
- **Changes:** `.github/workflows/daily.yml` with:
  - `schedule` (once a day) plus `workflow_dispatch` with a `limit` input;
  - `concurrency: { group: feed, cancel-in-progress: false }`;
  - the download setup that worked in Phase 1;
  - R2 secrets from GitHub Secrets;
  - `timeout-minutes` below the 6-hour limit;
  - a keepalive step (`permissions: actions: write`; calls the enable-workflow API);
  - only `schedule` and `workflow_dispatch` triggers. No `pull_request_target`, so forks never get the secrets.

  Delete `smoke.yml`.
- **Verification:** one manual run with `limit=5`; `state.json` and `feed.xml` in R2 are updated and the new episodes show up in the app.
- **Done when:** a scheduled run has worked unattended, and the backfill is in progress at 50 videos per day.
- **Commit:** `ci: add daily feed update workflow`

### Phase 6 — Public launch setup
- **Goal:** a final feed URL and a page for listeners, ready to show the author.
- **Manual setup:** a domain on Cloudflare DNS (~$10/year), connected to the bucket as a custom domain.
- **Changes:** `base_url` in `config.toml` (it changes the enclosure URLs; the guids stay, so episodes aren't duplicated); `cover.jpg` (square, 1400–3000 px); `README.md` for listeners (the feed URL and how to add it in common apps).
- **Verification:** the validator passes on the new URL; adding the feed to Apple Podcasts and AntennaPod by URL works.
- **Done when:** the feed on the custom domain plays in two apps.
- **Commit:** `feat: move feed to custom domain`

## Phase dependencies
| Phase | Depends on | Blocks | Parallel with | Nature of the dependency |
|---|---|---|---|---|
| 1 | — | 5 | 2, 3 | `daily.yml` reuses the setup that worked here |
| 2 | — | 4 | 1, 3 | `run.py` calls the listing, metadata and download code |
| 3 | — | 4 | 1, 2 | `run.py` calls `rss.py`; `State` is defined here |
| 4 | 2, 3 | 5, 6 | — | The workflow and the launch need the `run` command and the R2 bucket |
| 5 | 1, 4 | — | 6 | Needs the working download setup and `run` |
| 6 | 4 | — | 5 | Needs the bucket and the feed in R2; independent of where the job runs |

## Open questions
| Question | What's unclear | Why it matters | Needed by |
|---|---|---|---|
| Which download setup works on GitHub runners? | Plain, PO token, cookies, or none | If none works, the daily job runs on the laptop (launchd) | Phase 5 |
| How long does one video take on a runner? | Download speed and YouTube throttling | Sets the batch size and `timeout-minutes` | Phase 5 |
| Which domain? | Needs to be chosen and paid for (~$10/year) | The feed URL is permanent once people subscribe | Phase 6 |
| Cover image | The channel avatar may be smaller than 1400 px | Apple and Spotify reject smaller covers | Phase 6 |
| Owner email for `itunes:owner` | The project owner's or the author's | Directories send verification mail there; matters when submitting after the author agrees | Phase 6 |
| Does the keepalive really reset the 60-day counter? | Can only be confirmed after 60 days | Otherwise the job stops quietly; GitHub sends a warning email before that | ~60 days after Phase 5 |
