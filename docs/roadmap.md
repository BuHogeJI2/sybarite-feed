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

### 2. Author info
- **Why:** this was left out until the author agreed.
- **Notes:**
  - `itunes:owner` (name and email). The email is public in the feed, and catalogs use it to
    verify ownership. **Open:** his email or the feed maintainer's.
  - A link to his site, `https://genadivaldberg.wordpress.com/`.
  - `podcast:funding` with the PayPal link; apps that support it show a "Support" button.

### 3. Remove an episode
- **Why:** the author may ask to remove a lecture; that should take a minute.
- **Notes:** a `remove --id` command: delete the audio from R2, drop the episode from the state
  and the feed, and add the video to a blocklist so later runs don't download it again. Also
  settles review finding #10 (videos deleted or edited on YouTube): keep them unless removed by
  hand.

### 4. Submit to catalogs
- **Why:** listeners should find the podcast by search, not only by link.
- **Notes:**
  - Apple Podcasts Connect (needs an Apple ID). Pocket Casts and Overcast pick it up from Apple.
  - Яндекс Музыка (Яндекс Подкасты form).
  - Spotify for Creators (accepts an RSS link).
  - Podcast Index.
  - Depends on 2 (owner email) and preferably on 1 (feed size).

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

### 8. Page for listeners at `sibarit.org`
- "Open in Apple Podcasts / Pocket Casts / Overcast / …" buttons and the feed URL. Simpler than
  a raw `feed.xml` link for non-technical listeners. The root domain is free for it.

### 9. Richer episodes
- Clickable links in episode descriptions.
- An image per episode from the YouTube thumbnail (`itunes:image` in each item).
- The episode number from "№184" in the title (`itunes:episode`).

### 10. Transcripts
- `podcast:transcript` from YouTube subtitles. Apple shows them, and they make the lectures
  searchable by text. The largest item here.
