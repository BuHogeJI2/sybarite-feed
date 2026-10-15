# sybarite-feed

Lectures from Genadi Valdberg's YouTube channel
[«Записки воинствующего сибарита»](https://www.youtube.com/@GenadiValdberg) as a podcast feed.

Once a day the update downloads the audio of new videos, uploads it to Cloudflare R2 and
rebuilds `feed.xml`. The archive is filled in batches, newest videos first.

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

## Development

```sh
uv run pytest
uv run python -m sybarite_feed download --id 2NgIPVQbK8g --out ./tmp
```
