from sybarite_feed.channel import ChannelVideo
from sybarite_feed.select import MAX_ATTEMPTS, select_batch


def video(video_id: str, duration: int | None = 1800) -> ChannelVideo:
    return ChannelVideo(id=video_id, duration=duration)


def ids(videos: list[ChannelVideo]) -> list[str]:
    return [v.id for v in videos]


def test_keeps_channel_order_and_limit():
    videos = [video("a"), video("b"), video("c")]
    assert ids(select_batch(videos, set(), {}, min_duration=120, limit=2)) == ["a", "b"]


def test_zero_limit_selects_nothing():
    assert select_batch([video("a")], set(), {}, min_duration=120, limit=0) == []


def test_skips_done_videos():
    videos = [video("a"), video("b")]
    assert ids(select_batch(videos, {"a"}, {}, min_duration=120, limit=10)) == ["b"]


def test_retries_failed_videos_until_max_attempts():
    videos = [video("a"), video("b")]
    failures = {"a": MAX_ATTEMPTS, "b": MAX_ATTEMPTS - 1}
    assert ids(select_batch(videos, set(), failures, min_duration=120, limit=10)) == ["b"]


def test_skips_short_and_unpublished_videos():
    videos = [video("short", 60), video("premiere", None), video("edge", 120)]
    assert ids(select_batch(videos, set(), {}, min_duration=120, limit=10)) == ["edge"]


def test_skipped_videos_do_not_count_towards_limit():
    videos = [video("done"), video("short", 10), video("a"), video("b")]
    assert ids(select_batch(videos, {"done"}, {}, min_duration=120, limit=2)) == ["a", "b"]
