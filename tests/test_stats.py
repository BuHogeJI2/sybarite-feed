import json
from datetime import UTC, datetime

from factories import make_episode
from sybarite_feed.channel import ChannelVideo
from sybarite_feed.state import State
from sybarite_feed.stats import build_stats

CHECKED_AT = datetime(2026, 11, 3, 3, 14, tzinfo=UTC)


def stats(state: State, *videos: ChannelVideo) -> dict:
    return json.loads(build_stats(state, videos, 120, CHECKED_AT))


def episode(video_id: str, year: int, duration: int = 1800):
    return make_episode(video_id, published=datetime(year, 1, 1, tzinfo=UTC), duration=duration)


def test_counts_episodes_hours_and_first_date():
    state = State(episodes={"a": episode("a", 2016, 1000), "b": episode("b", 2015, 2000)})
    data = stats(state, ChannelVideo("a", 1000), ChannelVideo("b", 2000))
    assert data["episodes"] == 2
    assert data["total"] == 2
    assert data["duration"] == 3000
    assert data["first_published"] == "2015-01-01T00:00:00+00:00"
    assert data["checked_at"] == "2026-11-03T03:14:00+00:00"


def test_total_skips_short_unpublished_and_removed_videos():
    state = State(removed={"removed": "2026-10-19"})
    videos = [ChannelVideo("long", 1800), ChannelVideo("short", 60), ChannelVideo("premiere", None)]
    assert stats(state, *videos, ChannelVideo("removed", 1800))["total"] == 1


def test_episodes_gone_from_youtube_count_towards_total():
    state = State(episodes={"gone": episode("gone", 2020)})
    assert stats(state, ChannelVideo("new", 1800))["total"] == 2


def test_latest_are_the_three_newest():
    years = {"a": 2020, "b": 2023, "c": 2021, "d": 2022}
    state = State(episodes={video_id: episode(video_id, year) for video_id, year in years.items()})
    latest = stats(state)["latest"]
    assert [item["url"][-1] for item in latest] == ["b", "d", "c"]
    assert latest[0] == {
        "title": "Трусость или мудрость? №184",
        "published": "2023-01-01T00:00:00+00:00",
        "url": "https://www.youtube.com/watch?v=b",
    }


def test_empty_state():
    data = stats(State())
    assert data["episodes"] == 0
    assert data["first_published"] is None
    assert data["latest"] == []
