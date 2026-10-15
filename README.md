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

## Development

```sh
uv run pytest
uv run python -m sybarite_feed download --id 2NgIPVQbK8g --out ./tmp
```
