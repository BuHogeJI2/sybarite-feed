import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from factories import make_config, make_episode
from sybarite_feed.channel import ChannelVideo
from sybarite_feed.download import DownloadedAudio
from sybarite_feed.run import FEED_KEY, MAX_CONSECUTIVE_FAILURES, STATE_KEY, run_update
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


def channel(*video_ids: str):
    return lambda url: [ChannelVideo(id=video_id, duration=1800) for video_id in video_ids]


def run(storage, downloader, *video_ids, limit=10):
    return run_update(storage, make_config(), limit, channel(*video_ids), downloader, pause=lambda: None)


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
    assert list(work_dir.iterdir()) == []


def test_writes_audio_then_state_then_feed(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "a", "b")
    assert storage.writes == ["audio/a.m4a", STATE_KEY, FEED_KEY, "audio/b.m4a", STATE_KEY, FEED_KEY]


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
    assert storage.writes == [FEED_KEY]
    assert storage.get(STATE_KEY) == state_before


def test_failure_counts_when_other_downloads_work(storage, work_dir):
    result = run(storage, FakeDownloader(work_dir, failing={"a", "c"}), "a", "b", "c")

    assert result.ok
    assert result.added == ["b"]
    assert result.failed == ["a", "c"]
    assert saved_state(storage).failures == {"a": 1, "c": 1}


def test_success_clears_old_failures(storage, work_dir):
    storage.put(STATE_KEY, state_to_json(State(failures={"a": 2})).encode(), "application/json")
    run(storage, FakeDownloader(work_dir), "a")
    assert saved_state(storage).failures == {}


def test_failures_do_not_count_when_nothing_works(storage, work_dir):
    result = run(storage, FakeDownloader(work_dir, failing={"a"}), "a")

    assert not result.ok
    assert storage.get(STATE_KEY) is None
    assert feed_guids(storage) == []


def test_stops_after_consecutive_failures_without_counting(storage, work_dir):
    run(storage, FakeDownloader(work_dir), "x")
    video_ids = [f"v{n}" for n in range(MAX_CONSECUTIVE_FAILURES + 2)]
    downloader = FakeDownloader(work_dir, failing=set(video_ids))

    result = run(storage, downloader, *video_ids)

    assert not result.ok
    assert downloader.calls == video_ids[:MAX_CONSECUTIVE_FAILURES]
    assert saved_state(storage).failures == {}


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
