import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from factories import make_config, make_episode
from sybarite_feed.channel import ChannelVideo
from sybarite_feed.download import DownloadedAudio
from sybarite_feed.rss import COVER_KEY
from sybarite_feed.run import FEED_KEY, STATE_KEY, run_update
from sybarite_feed.select import MAX_ATTEMPTS
from sybarite_feed.state import State, state_from_json, state_to_json
from sybarite_feed.storage import ConflictError, LocalStorage


class RecordingStorage(LocalStorage):
    def __init__(self, root: Path):
        super().__init__(root)
        self.writes: list[str] = []

    def put(self, key, data, content_type, **options):
        self.writes.append(key)
        return super().put(key, data, content_type, **options)

    def upload_file(self, key, path, content_type, **options):
        self.writes.append(key)
        super().upload_file(key, path, content_type, **options)


class FakeDownloader:
    def __init__(self, work_dir: Path, failing: set[str] = frozenset()):
        self.work_dir = work_dir
        self.failing = failing
        self.calls: list[str] = []

    def __call__(self, video_id: str) -> DownloadedAudio:
        self.calls.append(video_id)
        if video_id in self.failing:
            raise RuntimeError("Sign in to confirm you're not a bot")
        path = self.work_dir / f"{video_id}.m4a"
        path.write_bytes(b"audio")
        return DownloadedAudio(episode=make_episode(video_id), path=path)


@pytest.fixture
def storage(tmp_path):
    return RecordingStorage(tmp_path / "bucket")


@pytest.fixture
def work_dir(tmp_path):
    path = tmp_path / "work"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def cover(tmp_path):
    path = tmp_path / "cover.jpg"
    path.write_bytes(b"jpeg")
    return path


def channel(*video_ids: str):
    return lambda url: [ChannelVideo(id=video_id, duration=1800) for video_id in video_ids]


def run(storage, downloader, *video_ids, limit=10):
    cover = storage.root.parent / "cover.jpg"
    return run_update(storage, make_config(cover=str(cover)), limit, channel(*video_ids), downloader, pause=lambda: None)


def saved_state(storage) -> State:
    return state_from_json(storage.get(STATE_KEY).data.decode())


def feed_guids(storage) -> list[str]:
    return [guid.text for guid in ET.fromstring(storage.get(FEED_KEY).data).iter("guid")]


def test_adds_new_videos_and_publishes_feed(storage, work_dir):
    result = run(storage, FakeDownloader(work_dir), "a", "b")

    assert result.added == ["a", "b"]
    assert result.ok
    assert set(saved_state(storage).episodes) == {"a", "b"}
    assert feed_guids(storage) == ["a", "b"]
    assert storage.get("audio/a.m4a").data == b"audio"
    assert storage.get(COVER_KEY).data == b"jpeg"
    assert list(work_dir.iterdir()) == []


def test_writes_cover_then_audio_state_and_feed(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "a", "b")
    assert storage.writes == [COVER_KEY, "audio/a.m4a", STATE_KEY, FEED_KEY, "audio/b.m4a", STATE_KEY, FEED_KEY]


def test_second_run_skips_done_videos(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "a")
    downloader = FakeDownloader(work_dir)

    result = run(storage, downloader, "b", "a")

    assert downloader.calls == ["b"]
    assert set(saved_state(storage).episodes) == {"a", "b"}
    assert result.added == ["b"]


def test_limit_zero_only_republishes_feed(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "a")
    state_before = storage.get(STATE_KEY)
    storage.writes.clear()

    result = run(storage, FakeDownloader(work_dir), "a", "b", limit=0)

    assert result.ok and result.added == []
    assert storage.writes == [COVER_KEY, FEED_KEY]
    assert storage.get(STATE_KEY) == state_before


def test_failures_count_when_a_published_episode_downloads(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")
    downloader = FakeDownloader(work_dir, failing={"a", "c"})

    result = run(storage, downloader, "a", "b", "c")

    assert result.ok
    assert result.added == ["b"]
    assert result.failed == ["a", "c"]
    assert downloader.calls == ["a", "x", "b", "c", "x"]
    assert saved_state(storage).failures == {"a": 1, "c": 1}
    assert list(work_dir.iterdir()) == []


def test_success_clears_old_failures(storage, work_dir):
    storage.put(STATE_KEY, state_to_json(State(failures={"a": 2})).encode(), "application/json")
    run(storage, FakeDownloader(work_dir), "a")
    assert saved_state(storage).failures == {}


def test_failure_stops_the_first_run(storage, work_dir):
    result = run(storage, FakeDownloader(work_dir, failing={"a"}), "a")

    assert not result.ok
    assert storage.get(STATE_KEY) is None
    assert feed_guids(storage) == []


def test_bad_videos_do_not_block_the_next_ones(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")

    result = run(storage, FakeDownloader(work_dir, failing={"a", "b", "c"}), "a", "b", "c", "d")

    assert result.ok
    assert result.added == ["d"]
    assert saved_state(storage).failures == {"a": 1, "b": 1, "c": 1}


def test_stops_without_counting_when_a_published_episode_fails_too(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")
    storage.writes.clear()
    downloader = FakeDownloader(work_dir, failing={"a", "b", "x"})

    result = run(storage, downloader, "a", "b")

    assert not result.ok
    assert downloader.calls == ["a", "x"]
    assert saved_state(storage).failures == {}
    assert storage.writes == [COVER_KEY, FEED_KEY]


def test_tries_the_next_episode_when_the_shortest_was_removed(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")
    state = saved_state(storage)
    state.episodes["removed"] = make_episode("removed", duration=200)
    storage.put(STATE_KEY, state_to_json(state).encode(), "application/json")
    downloader = FakeDownloader(work_dir, failing={"a", "removed"})

    result = run(storage, downloader, "a", "b")

    assert result.added == ["b"]
    assert downloader.calls == ["a", "removed", "x", "b"]
    assert saved_state(storage).failures == {"a": 1}


def test_checks_access_with_the_shortest_episode(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")
    state = saved_state(storage)
    state.episodes["short"] = make_episode("short", duration=200)
    storage.put(STATE_KEY, state_to_json(state).encode(), "application/json")
    downloader = FakeDownloader(work_dir, failing={"a"})

    run(storage, downloader, "a")

    assert downloader.calls == ["a", "short"]


def test_video_is_skipped_after_max_attempts(storage, work_dir):
    storage.put(STATE_KEY, state_to_json(State(failures={"a": MAX_ATTEMPTS})).encode(), "application/json")
    downloader = FakeDownloader(work_dir)
    run(storage, downloader, "a", "b")
    assert downloader.calls == ["b"]


class ConcurrentWriteStorage(RecordingStorage):
    """Another run saves state.json right after this run has read it."""

    def get(self, key):
        stored = super().get(key)
        if key == STATE_KEY and not getattr(self, "interfered", False):
            self.interfered = True
            super().put(STATE_KEY, state_to_json(State(failures={"other": 1})).encode(), "application/json")
        return stored


def test_conflict_stops_the_run(tmp_path, work_dir):
    storage = ConcurrentWriteStorage(tmp_path / "bucket")
    downloader = FakeDownloader(work_dir)

    with pytest.raises(ConflictError):
        run(storage, downloader, "a", "b")

    assert downloader.calls == ["a"]
    assert saved_state(storage).failures == {"other": 1}
