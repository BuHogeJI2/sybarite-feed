# Roadmap

The author (Genadi Valdberg) has agreed to the podcast (2026-10-16). The feed works, and the
backfill is in progress. Each item below gets its own plan in `docs/plans/` before work starts.

## Next — before submitting to the catalogs

### 1. Smaller feed
- **Why:** `feed.xml` was 436 KB for 79 episodes, so about 5.8 MB for all 1054. Apps download it
  often, though compressed (gzip) it is about 11 times smaller. Catalogs may have size limits;
  check Apple's, Яндекс Музыка's and Spotify's before submitting.
- **Done:** the `-----` separator lines (133 dashes each) become paragraph breaks and trailing
  spaces are dropped when the feed is built: 436 → 385 KB for 79 episodes.
- **Kept:** the block repeated at the end of every description (the site, VK, PayPal, about
  700 bytes); it has the author's links, and gzip makes the repetition almost free.

### 2. Author info (done)
- **Why:** this was left out until the author agreed.
- **Done (2026-10-16):**
  - `itunes:owner`: «Геннадий Вальдберг», `podcast@sibarit.org`. The email is public in the feed,
    and catalogs send ownership checks to it. Cloudflare Email Routing forwards it to the
    maintainer's Gmail; it works only while `sibarit.org` is renewed (auto-renew is on).
  - «Сайт: https://genadivaldberg.wordpress.com/» in the show description, before PayPal.
    `<link>` stays the YouTube channel.
  - `podcast:funding` with the PayPal link; apps that support it show a "Support" button.

### 3. Remove an episode (done)
- **Why:** the author may ask to remove a lecture; that should take a minute.
- **Done (2026-10-19):** `remove --id` and a `remove` workflow (run by hand, in the daily job's
  concurrency group, so it works from a phone and never overlaps a daily run).
  - Order: save the state (ETag check), publish the feed, then delete the audio, so a failed step
    never leaves the feed pointing at a missing file.
  - The blocklist is `removed` in `state.json` (video ID → date), not `config.toml`: it is saved in
    the same write as the episode removal and needs no commit.
  - No undo command; delete the ID from `removed` by hand.
  - Settles review finding #10: episodes whose videos are deleted or edited on YouTube stay until
    removed by hand.

### 4. Submit to catalogs
- **Why:** listeners should find the podcast by search, not only by link.
- **Notes:**
  - Apple Podcasts Connect (needs an Apple ID). Pocket Casts and Overcast pick it up from Apple.
  - Яндекс Музыка (Яндекс Подкасты form).
  - Spotify for Creators (accepts an RSS link).
  - Podcast Index.
  - Ready: 1 and 2 are done.
  - **Postponed (2026-10-16).** Apple's sign-up form rejected `podcast@sibarit.org` as an Apple ID,
    most likely because the domain was registered the day before. The Apple ID email doesn't have
    to match the feed: use a Gmail address, or try the domain again later.

## Reliability

### 5. Watch the daily runs
- The first scheduled runs (21:17 UTC) and the backfill reaching all 1054 videos.
- Whether the keepalive really resets GitHub's 60-day counter.
- A check from outside GitHub, e.g. an alert if `feed.xml` hasn't changed in N days. GitHub
  can't report a schedule that silently stopped.
- The canary failure rule worked in the first scheduled run (2026-10-15, 23:42 UTC; GitHub started
  it 25 minutes late): `_TC27-Igwdw` broke off mid-download ("1464540 more expected"), the check
  with `_hZ8V1Zc59s` passed, the failure was counted, and 49 of 50 videos were added.

### 6. Leftover review findings
- **#7** Overlapping runs (laptop and Actions) can publish a stale `feed.xml`. Cheap part: re-read
  the state before publishing; a real fix needs a lock.
- **#8** Skipped fragments can produce incomplete audio: set `skip_unavailable_fragments=False`,
  compare the file's duration (ffprobe) with a tolerance.
- **#9** The format fallback `bestaudio[ext=m4a]` also accepts a track labeled in another
  language; allow only `ru` or unlabeled.
- **#11** Check that ffmpeg is installed before a laptop run.

## Later

### 7. Playlists
- One feed per YouTube playlist (`feed-<name>.xml`) that reuses the same audio files, so no extra
  storage. Needs the playlist list from YouTube and each video's playlists in the state.

### 8. Page for listeners at `sibarit.org` (done)
- "Open in Apple Podcasts / Pocket Casts / Overcast / …" buttons and the feed URL. Simpler than
  a raw `feed.xml` link for non-technical listeners.
- **Done (2026-10-16):** static `site/index.html`, deployed by Cloudflare Pages on pushes to
  `master` that change `site/`; `www.sibarit.org` redirects to the root (a Redirect Rule).
  - `podcast://` fills in the URL on iPhone, but Podcasts on macOS opens an empty "Follow a Show by
    URL" box (`podcasts://`, `pcast://` and `itpc://` are no better), so the button also copies the
    feed URL. Once the show is in Apple's catalog, link to its `podcasts.apple.com` page instead.

### 9. Richer episodes
- Clickable links in episode descriptions.
- An image per episode from the YouTube thumbnail (`itunes:image` in each item).
- The episode number from "№184" in the title (`itunes:episode`).

### 10. Transcripts
- `podcast:transcript` from YouTube subtitles. Apple shows them, and they make the lectures
  searchable by text. The largest item here.

### 11. Listener stats (partly done)
- **Why:** to know whether anyone listens, and which apps they use.
- **Rule:** no third-party tools (OP3, Plausible, …); only what Cloudflare already gives.
- **Done (2026-10-24):**
  - `site/404.html`. Without it Pages answered every path with `index.html` and 200, so scanners
    (`/.git/config`, `*.php`, about 500 requests from Sydney in an hour) looked like page views.
  - App buttons and "Копировать" send `GET /click/<name>` (`apple`, `overcast`, `pocketcasts`,
    `antennapod`, `copy`). There is no file there, so they get 404; Cloudflare's HTTP analytics
    still counts them. Check: zone `sibarit.org` → Analytics → Requests, filter Host equals
    `sibarit.org` and Path starts with `/click/`. The free plan keeps about 30 days, which is enough.
- **Notes:**
  - Web Analytics (the Visitors tab) seems to be on already: the page sends `/cdn-cgi/rum`.
  - Feed and audio: filter Host equals `podcast.sibarit.org`. `feed.xml` requests are apps polling,
    not people; audio requests are closer to listens, but with no per-listener deduplication.
  - Don't turn on Bot Fight Mode: on the free plan it covers the whole zone and may challenge podcast
    apps fetching the feed and audio.
  - Real numbers per episode and app would need a Worker in front of `podcast.sibarit.org` that
    logs requests; the catalogs (item 4) add their own stats.
