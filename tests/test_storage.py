import pytest

from sybarite_feed.storage import ConflictError, LocalStorage


def test_get_missing_key(tmp_path):
    assert LocalStorage(tmp_path).get("state.json") is None


def test_create_only_when_missing(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.put("state.json", b"one", "application/json", if_none_match=True)
    with pytest.raises(ConflictError):
        storage.put("state.json", b"two", "application/json", if_none_match=True)


def test_update_only_with_current_etag(tmp_path):
    storage = LocalStorage(tmp_path)
    first = storage.put("state.json", b"one", "application/json")
    second = storage.put("state.json", b"two", "application/json", if_match=first)
    with pytest.raises(ConflictError):
        storage.put("state.json", b"three", "application/json", if_match=first)
    assert storage.get("state.json").etag == second
