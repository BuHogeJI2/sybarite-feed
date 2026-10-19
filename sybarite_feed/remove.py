import logging
import re
from collections.abc import Sequence
from datetime import date

from sybarite_feed.config import Config
from sybarite_feed.run import audio_key, load_state, publish_feed, save_state
from sybarite_feed.storage import Storage

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")

log = logging.getLogger(__name__)


def remove_videos(storage: Storage, config: Config, video_ids: Sequence[str], today: date) -> None:
    state, etag = load_state(storage)
    episodes = [state.episodes.pop(video_id) for video_id in video_ids if video_id in state.episodes]
    for video_id in video_ids:
        state.removed.setdefault(video_id, today.isoformat())
        state.failures.pop(video_id, None)

    # the audio goes last, so a failed step never leaves the feed pointing at a missing file
    save_state(storage, state, etag)
    publish_feed(storage, state, config)
    for episode in episodes:
        storage.delete(audio_key(episode))
        log.info("removed %s: %s", episode.id, episode.title)
    for video_id in set(video_ids) - {episode.id for episode in episodes}:
        log.info("%s was not in the feed; it won't be downloaded", video_id)
