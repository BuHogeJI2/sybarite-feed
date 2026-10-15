# Plan: Full podcast description with PayPal link and feed credit

## Task
The feed `<description>` in `config.toml` is a shortened copy of the YouTube channel's "About"
text, plus one sentence of our own. Listeners should see the author's full text, a clickable link
to support the author through PayPal, and at the end a short credit for who made the feed. The
credit links to the GitHub repo, so a listener who has trouble with the podcast can find where to
report it.

## Non-goals
- Clickable links inside episode descriptions. The video descriptions already contain the
  PayPal and other URLs as plain text; making them links is a separate change.
- Fetching the channel description from YouTube on every run. The text rarely changes, and the
  PayPal link isn't in the text yt-dlp returns.
- A `<generator>` tag or any other invisible credit.

## Decisions & rationale
- **Static text in `config.toml`.** The full "About" text, split into paragraphs by blank lines.
  Rejected: fetching it at run time (one more request, and the result still lacks the PayPal
  link).
- **The PayPal URL is the one the owner gave from the channel page:**
  `https://www.paypal.com/donate?hosted_button_id=QWPFEY2BG92S6`. The video descriptions use a
  different button (`TT7E9LTRK5P7N`); the channel one was chosen on purpose.
- **The feed description becomes HTML**, the same way `episode_html` already does it: `<p>` per
  paragraph, `<br>` for single line breaks, everything escaped by ElementTree. Apple Podcasts
  supports `<p>` and `<a>` in the show description. Apps that remove HTML show plain text, which
  is an acceptable fallback.
- **Order:** the author's text, then the PayPal link paragraph, then the credit as the last
  paragraph.
- **Credit text:** `Feed created by BuHogeJI`, in English, where "BuHogeJI" links to
  `https://github.com/BuHogeJI2/sybarite-feed`. Podcast HTML has no supported way to make text
  smaller, so "small" means short and last.
- **New `FeedConfig` fields with empty defaults:** `donate_url`, `credit`, `credit_url`. A
  paragraph is left out when its field is empty, so the test factories and any other config keep
  working.

## Assumptions
- The PayPal link text is «Поддержать канал через PayPal».
- Our own sentence «Лекции Геннадия Вальдберга с YouTube-канала …» is removed; the description is
  only the author's text.
- The author's email and Facebook lines stay, as plain text, because they are part of his
  description.

## Phases

### Phase 1 — Full description, PayPal link and credit
- **Goal:** the published feed shows the full text, a PayPal link and the credit link.
- **Changes:**
  - `config.toml` `[feed]`: replace `description` with the full text; add `donate_url`, `credit`,
    `credit_url`.
  - `sybarite_feed/config.py`: the three new `FeedConfig` fields, default `""`.
  - `sybarite_feed/rss.py`:
    - move the paragraph code from `episode_html` into a shared `_paragraphs_html(text)`;
    - new `channel_html(feed)`: the paragraphs, then
      `<p><a href="{donate_url}">Поддержать канал через PayPal</a></p>`, then
      `<p>Feed created by <a href="{credit_url}">{credit}</a></p>`;
    - `build_feed` writes `channel_html(feed)` into the channel `<description>`.
  - `tests/test_rss.py`: a test that the channel description has the paragraphs, the PayPal link
    and the credit link in that order, with HTML escaped; a test that the links are left out when
    the fields are empty. The existing `test_description_is_escaped_html_with_video_link` guards
    the `episode_html` refactor.
- **Verification:**
  - `uv run pytest`
  - `uv run python -c "from sybarite_feed.config import load_config; from sybarite_feed.rss import channel_html; print(channel_html(load_config().feed))"`,
    then read the HTML by eye.
  - After the change is on the default branch: `uv run --env-file .env python -m sybarite_feed run --limit 0`
    republishes `feed.xml`; open the podcast page in Apple Podcasts and check that both links
    work.
- **Done when:** the tests pass and the podcast page in an app shows the full text, a working
  PayPal link and the credit.
- **Commit:** `feat: show full channel description with PayPal link and feed credit`

## Open questions
| Question | What's unclear | Why it matters | Needed by |
|---|---|---|---|
| Link text for PayPal | «Поддержать канал через PayPal» is a placeholder; the author's own phrase or the bare URL are the other options | It's what listeners read | Phase 1, but easy to change after |
