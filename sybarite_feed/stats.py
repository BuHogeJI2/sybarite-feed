import json
from collections.abc import Sequence
from datetime import datetime

from sybarite_feed.channel import ChannelVideo
from sybarite_feed.state import State

STATS_KEY = "stats.json"
LATEST_COUNT = 3


def build_stats(state: State, videos: Sequence[ChannelVideo], min_duration: int, checked_at: datetime) -> bytes:
    eligible = {
        video.id
        for video in videos
        if video.duration is not None and video.duration >= min_duration and video.id not in state.removed
    }
    episodes = sorted(state.episodes.values(), key=lambda episode: episode.published, reverse=True)
    data = {
        "checked_at": checked_at.isoformat(),
        "episodes": len(episodes),
        # episodes later deleted from YouTube stay in the feed, so they count towards the total too
        "total": len(eligible | state.episodes.keys()),
        "duration": sum(episode.duration for episode in episodes),
        "first_published": episodes[-1].published.isoformat() if episodes else None,
        "latest": [
            {"title": episode.title, "published": episode.published.isoformat(), "url": episode.video_url}
            for episode in episodes[:LATEST_COUNT]
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode()
