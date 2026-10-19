import xml.etree.ElementTree as ET
from datetime import date

import pytest

from factories import make_config, make_episode
from sybarite_feed.remove import remove_videos
from sybarite_feed.run import FEED_KEY, STATE_KEY
from sybarite_feed.state import State, state_from_json, state_to_json
from sybarite_feed.storage import ConflictError, LocalStorage

TODAY = date(2026, 10, 19)


class RecordingStorage(LocalStorage):
    def __init__(self, root):
        super().__init__(root)
        self.writes: list[str] = []

    def put(self, key, data, content_type, **options):
        self.writes.append(key)
        return super().put(key, data, content_type, **options)

    def delete(self, key):
        self.writes.append(f"delete {key}")
        super().delete(key)


@pytest.fixture
def storage(tmp_path):
    storage = RecordingStorage(tmp_path / "bucket")
    state = State(episodes={"a": make_episode("a"), "b": make_episode("b")}, failures={"c": 1})
    storage.put(STATE_KEY, state_to_json(state).encode(), "application/json")
    for video_id in ("a", "b"):
        storage.put(f"audio/{video_id}.m4a", b"audio", "audio/x-m4a")
    storage.writes.clear()
    return storage


def saved_state(storage) -> State:
    return state_from_json(storage.get(STATE_KEY).data.decode())


def feed_guids(storage) -> list[str]:
    return [guid.text for guid in ET.fromstring(storage.get(FEED_KEY).data).iter("guid")]


def test_removes_episode_from_state_feed_and_bucket(storage):
    remove_videos(storage, make_config(), ["a"], TODAY)

    state = saved_state(storage)
    assert list(state.episodes) == ["b"]
    assert state.removed == {"a": "2026-10-19"}
    assert feed_guids(storage) == ["b"]
    assert storage.get("audio/a.m4a") is None
    assert storage.get("audio/b.m4a") is not None


def test_deletes_audio_only_after_the_feed_is_published(storage):
    remove_videos(storage, make_config(), ["a"], TODAY)
    assert storage.writes == [STATE_KEY, FEED_KEY, "delete audio/a.m4a"]


def test_video_not_in_the_feed_is_only_blocked(storage):
    remove_videos(storage, make_config(), ["c"], TODAY)

    state = saved_state(storage)
    assert list(state.episodes) == ["a", "b"]
    assert state.removed == {"c": "2026-10-19"}
    assert state.failures == {}
    assert storage.writes == [STATE_KEY, FEED_KEY]


def test_removing_again_keeps_the_first_date(storage):
    remove_videos(storage, make_config(), ["a"], TODAY)
    remove_videos(storage, make_config(), ["a"], date(2027, 1, 1))
    assert saved_state(storage).removed == {"a": "2026-10-19"}


class ConcurrentWriteStorage(RecordingStorage):
    def get(self, key):
        stored = super().get(key)
        if key == STATE_KEY and not getattr(self, "interfered", False):
            self.interfered = True
            super().put(STATE_KEY, state_to_json(State(failures={"other": 1})).encode(), "application/json")
            self.writes.clear()
        return stored


def test_conflict_changes_nothing(storage):
    racing = ConcurrentWriteStorage(storage.root)

    with pytest.raises(ConflictError):
        remove_videos(racing, make_config(), ["a"], TODAY)

    assert racing.writes == [STATE_KEY]
    assert saved_state(racing).failures == {"other": 1}
    assert racing.get("audio/a.m4a") is not None
