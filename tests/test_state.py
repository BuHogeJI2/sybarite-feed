import json
from datetime import UTC, datetime

from factories import make_episode
from sybarite_feed.state import State, state_from_json, state_to_json


def test_round_trip():
    state = State(episodes={"a": make_episode("a")}, failures={"b": 2})
    assert state_from_json(state_to_json(state)) == state


def test_episodes_are_saved_newest_first():
    old = make_episode("old", published=datetime(2020, 1, 1, tzinfo=UTC))
    new = make_episode("new")
    saved = json.loads(state_to_json(State(episodes={"old": old, "new": new})))
    assert [episode["id"] for episode in saved["episodes"]] == ["new", "old"]


def test_cyrillic_is_saved_as_is():
    assert "Трусость" in state_to_json(State(episodes={"a": make_episode("a")}))
