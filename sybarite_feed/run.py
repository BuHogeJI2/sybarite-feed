import logging
import random
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sybarite_feed.channel import ChannelVideo
from sybarite_feed.config import Config
from sybarite_feed.download import DownloadedAudio
from sybarite_feed.episode import Episode
from sybarite_feed.rss import COVER_KEY, build_feed
from sybarite_feed.select import MAX_ATTEMPTS, select_batch
from sybarite_feed.state import State, state_from_json, state_to_json
from sybarite_feed.stats import STATS_KEY, build_stats
from sybarite_feed.storage import Storage

STATE_KEY = "state.json"
FEED_KEY = "feed.xml"
KNOWN_EPISODES_TO_TRY = 3

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    added: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    ok: bool = True


def random_pause() -> None:
    time.sleep(random.uniform(5, 15))


def run_update(
    storage: Storage,
    config: Config,
    limit: int,
    list_videos: Callable[[str], list[ChannelVideo]],
    download: Callable[[str], DownloadedAudio],
    pause: Callable[[], None] = random_pause,
) -> RunResult:
    state, etag = load_state(storage)
    storage.upload_file(COVER_KEY, Path(config.feed.cover), "image/jpeg", cache_control="public, max-age=86400")

    videos = list_videos(config.channel.url)
    done = state.episodes.keys() | state.removed.keys()
    batch = select_batch(videos, done, state.failures, config.channel.min_duration, limit)
    log.info("channel has %d videos, %d in the feed, %d selected", len(videos), len(state.episodes), len(batch))

    result = RunResult()
    for index, video in enumerate(batch):
        if index:
            pause()
        log.info("downloading %s (%d/%d)", video.id, index + 1, len(batch))
        try:
            audio = download(video.id)
        # yt-dlp and urllib raise many unrelated error types
        except Exception as error:
            log.warning("failed %s: %s", video.id, error)
            result.failed.append(video.id)
            if not _youtube_works(state, download, pause):
                log.error("stopping: published episodes don't download either, so YouTube access is broken")
                publish_feed(storage, state, config)
                publish_stats(storage, state, videos, config)
                result.ok = False
                return result
            attempts = state.failures.get(video.id, 0) + 1
            state.failures[video.id] = attempts
            if attempts >= MAX_ATTEMPTS:
                log.error("giving up on %s after %d failed attempts", video.id, attempts)
            etag = save_state(storage, state, etag)
            continue

        storage.upload_file(
            audio_key(audio.episode),
            audio.path,
            audio.episode.mime_type,
            cache_control="public, max-age=31536000, immutable",
        )
        audio.path.unlink()
        state.episodes[video.id] = audio.episode
        state.failures.pop(video.id, None)
        etag = save_state(storage, state, etag)
        publish_feed(storage, state, config)
        result.added.append(video.id)
        log.info("added %s: %s", video.id, audio.episode.title)

    if not result.added:
        # keeps the feed current after a config change or a run that stopped before publishing
        publish_feed(storage, state, config)
    publish_stats(storage, state, videos, config)
    return result


def _youtube_works(state: State, download: Callable[[str], DownloadedAudio], pause: Callable[[], None]) -> bool:
    # a failed video counts against its attempts only if a published episode still downloads; otherwise
    # expired cookies or a YouTube block would use up the attempts of every video in the batch. Several
    # are tried because a published video can be removed from YouTube later
    shortest = sorted(state.episodes.values(), key=lambda episode: episode.duration)
    for known in shortest[:KNOWN_EPISODES_TO_TRY]:
        pause()
        log.info("checking YouTube access with %s", known.id)
        try:
            audio = download(known.id)
        # yt-dlp and urllib raise many unrelated error types
        except Exception as error:
            log.warning("failed %s: %s", known.id, error)
            continue
        audio.path.unlink()
        return True
    return False


def audio_key(episode: Episode) -> str:
    return f"audio/{episode.file_name}"


def load_state(storage: Storage) -> tuple[State, str | None]:
    stored = storage.get(STATE_KEY)
    if not stored:
        return State(), None
    return state_from_json(stored.data.decode()), stored.etag


def save_state(storage: Storage, state: State, etag: str | None) -> str:
    return storage.put(
        STATE_KEY,
        state_to_json(state).encode(),
        "application/json",
        cache_control="no-store",
        if_match=etag,
        if_none_match=etag is None,
    )


def publish_feed(storage: Storage, state: State, config: Config) -> None:
    feed = build_feed(state.episodes.values(), config.feed, config.storage.base_url)
    # a feed that doesn't parse would replace the working one in every subscriber's app
    ET.fromstring(feed)
    storage.put(FEED_KEY, feed, "application/rss+xml; charset=utf-8", cache_control="public, max-age=300")


def publish_stats(storage: Storage, state: State, videos: list[ChannelVideo], config: Config) -> None:
    stats = build_stats(state, videos, config.channel.min_duration, datetime.now(UTC).replace(microsecond=0))
    storage.put(STATS_KEY, stats, "application/json; charset=utf-8", cache_control="public, max-age=300")
