# AGENTS.md

Genadi Valdberg's YouTube channel as a podcast feed. The author has agreed to it. See `README.md`
for how it works and `docs/roadmap.md` for what is planned.

## Layout
- `sybarite_feed/`: the Python package (Python 3.12, uv).
  - `run.py`: the daily update: list videos, download, upload to R2, save state, publish the feed.
  - `rss.py`: builds `feed.xml`. `channel.py`, `download.py`, `metadata.py`: YouTube via yt-dlp.
  - `storage.py`: Cloudflare R2. `state.py`: `state.json`, the list of published episodes.
  - `cookies.py`: checks and masks the YouTube cookies used on GitHub Actions.
- `config.toml`: channel, feed text and storage URL.
- `site/`: the static listener page at `https://sibarit.org`, no build step.
- `tests/`: pytest; `factories.py` builds episodes and configs. Tests never use the network.
- `docs/roadmap.md`, `docs/plans/`: one plan per roadmap item, updated with results.

## Commands
```sh
uv run pytest
uv run --env-file .env python -m sybarite_feed run --limit 10   # real run: needs .env with R2 keys
uv run --env-file .env python -m sybarite_feed run --limit 0    # rebuild and upload feed.xml only
uv run python -m sybarite_feed download --id VIDEO_ID --out ./tmp
```

## `master` is production
- The daily workflow (`.github/workflows/daily.yml`, 21:17 UTC) runs the code on `master`; GitHub
  runs schedules only on the default branch.
- Cloudflare Pages deploys `site/` on every push to `master` that changes it.
- `test.yml` runs pytest on pushes to `master` and on pull requests.
- A feed change made with `run --limit 0` from an unpushed checkout is overwritten by the next daily
  run.

## Rules
- Never commit `.env`, cookies or any R2 key. Never print cookie values: errors in `cookies.py`
  give only line numbers.
- `storage.base_url` is part of the feed URL that subscribers store. Don't change it.
- Episode `guid` is the YouTube video ID. Changing it makes apps show every episode as new.
- `state.json` is saved with an ETag check. Don't run a laptop run while the workflow runs.
- Text from YouTube goes through `xml_safe`, and the feed is parsed before upload. Keep both.
- In the workflow, pin actions to a commit SHA with a `# vX.Y.Z` comment. Keep `actions: write`
  out of the job that has the secrets.
- Code, comments and docs are in English. Text listeners see (feed, `site/`) is in Russian.
- Commit messages: one lowercase subject line with `feat:`, `fix:`, `ci:`, `docs:` or `test:`.
