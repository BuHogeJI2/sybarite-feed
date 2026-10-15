import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sybarite_feed.channel import ChannelVideo
from sybarite_feed.config import Config
from sybarite_feed.download import DownloadedAudio
from sybarite_feed.rss import build_feed
from sybarite_feed.select import select_batch
from sybarite_feed.state import State, state_from_json, state_to_json
from sybarite_feed.storage import Storage

STATE_KEY = "state.json"
FEED_KEY = "feed.xml"
MAX_CONSECUTIVE_FAILURES = 3

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
    stored = storage.get(STATE_KEY)
    state = state_from_json(stored.data.decode()) if stored else State()
    etag = stored.etag if stored else None

    videos = list_videos(config.channel.url)
    batch = select_batch(videos, state.episodes.keys(), state.failures, config.channel.min_duration, limit)
    log.info("channel has %d videos, %d in the feed, %d selected", len(videos), len(state.episodes), len(batch))

    result = RunResult()
    # failures since the last successful download; they count against a video only once a later
    # download in the same run succeeds, so expired cookies or a YouTube block don't burn attempts
    streak: list[str] = []
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
            streak.append(video.id)
            if len(streak) >= MAX_CONSECUTIVE_FAILURES:
                log.error("stopping: %d downloads failed in a row", len(streak))
                result.ok = False
                return result
            continue

        storage.upload_file(
            f"audio/{audio.episode.file_name}",
            audio.path,
            audio.episode.mime_type,
            cache_control="public, max-age=31536000, immutable",
        )
        audio.path.unlink()
        state.episodes[video.id] = audio.episode
        state.failures.pop(video.id, None)
        _count_failures(state, streak)
        streak = []
        etag = _save_state(storage, state, etag)
        _publish_feed(storage, state, config)
        result.added.append(video.id)
        log.info("added %s: %s", video.id, audio.episode.title)

    if result.added and streak:
        _count_failures(state, streak)
        _save_state(storage, state, etag)
    if not result.added:
        # keeps the feed current after a config change or a run that stopped before publishing
        _publish_feed(storage, state, config)
        result.ok = not streak
    return result


def _count_failures(state: State, video_ids: list[str]) -> None:
    for video_id in video_ids:
        state.failures[video_id] = state.failures.get(video_id, 0) + 1


def _save_state(storage: Storage, state: State, etag: str | None) -> str:
    return storage.put(
        STATE_KEY,
        state_to_json(state).encode(),
        "application/json",
        cache_control="no-store",
        if_match=etag,
        if_none_match=etag is None,
    )


def _publish_feed(storage: Storage, state: State, config: Config) -> None:
    feed = build_feed(state.episodes.values(), config.feed, config.storage.base_url)
    storage.put(FEED_KEY, feed, "application/rss+xml; charset=utf-8", cache_control="public, max-age=300")
