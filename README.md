# sybarite-feed

Lectures from Genadi Valdberg's YouTube channel
[«Записки воинствующего сибарита»](https://www.youtube.com/@GenadiValdberg) ("Notes of a Militant
Sybarite") as a podcast feed. The lectures are in Russian.

Once a day the update downloads the audio of new videos, uploads it to Cloudflare R2 and
rebuilds `feed.xml`. The archive is filled in batches, newest videos first.

When a video fails, the run downloads the shortest episodes already in the feed, up to three. If
one of them works, the video is skipped and tried again by the next runs, at most 3 times. If all
fail, YouTube access is broken (usually expired cookies): the run stops with an error and counts
nothing.

## How to listen

Page for listeners: **https://sibarit.org** ("Open in app" buttons).

Feed URL: **https://podcast.sibarit.org/feed.xml**

Add it to a podcast app by URL:

- **Apple Podcasts** (iPhone, Mac): Library → ⋯ → "Follow a Show by URL".
- **Pocket Casts**: Search → paste the URL.
- **Overcast**: + → "Add URL".
- **AntennaPod** (Android): + → "Add podcast by RSS address".

Spotify and Yandex Music can't add a podcast by URL.

## Run from laptop

Needs [uv](https://docs.astral.sh/uv/), deno and ffmpeg:

```sh
brew install uv deno ffmpeg
cp .env.example .env   # fill in the R2 keys
uv run --env-file .env python -m sybarite_feed run --limit 10
```

Without `--limit` a run takes `batch_size` videos from `config.toml`. A home connection needs no
YouTube cookies. If a run on GitHub Actions saves the state at the same time, the later run stops
with an error and loses nothing; start it again.

The daily workflow always takes the newest yt-dlp, while the laptop uses the version in `uv.lock`.
If downloads fail on the laptop, upgrade it with
`uv lock --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs`.

## Remove an episode

Episodes stay in the feed even if the video is deleted or changed on YouTube. To remove one, run the
**remove** workflow on GitHub (Actions → remove → Run workflow) with the video ID, or several IDs
separated by spaces. From the laptop:

```sh
uv run --env-file .env python -m sybarite_feed remove --id VIDEO_ID
```

The episode leaves the feed, its audio is deleted from R2, and the ID goes into `removed` in
`state.json`, so later runs never download it again. This also works for a video that isn't in the
feed yet. Apps that already downloaded the episode keep their copy. To undo, delete the ID from
`removed` in `state.json`; the next run downloads the video again.

## Refresh cookies

GitHub runners can download from YouTube only with the cookies of a logged-in account, stored in
the repository secret `YT_COOKIES`. They expire after weeks or months; then the daily workflow fails
with "Sign in to confirm you're not a bot" and GitHub sends an email. To renew them:

1. Open a private browser window and log in to YouTube with the separate account used for this
   project.
2. In the same tab open `https://www.youtube.com/robots.txt`.
3. Export the youtube.com cookies with the "Get cookies.txt LOCALLY" extension (Netscape format;
   allow the extension in private windows first).
4. Close the private window without logging out; logging out invalidates the cookies.
5. `gh secret set YT_COOKIES < cookies.txt`, then delete the file.

## Listener page

`site/` is a static page with no build step. Cloudflare Pages deploys it on every push to `master`
that changes `site/`.

The page shows the episode count, hours and latest episodes from `stats.json`, which the daily run
writes next to `feed.xml`. The R2 bucket's CORS policy must allow `GET` from `https://sibarit.org`;
without it the page hides that block.

## Development

```sh
uv run pytest
uv run python -m sybarite_feed download --id 2NgIPVQbK8g --out ./tmp
```
