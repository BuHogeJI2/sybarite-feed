import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

from sybarite_feed.episode import Episode


@dataclass
class State:
    episodes: dict[str, Episode] = field(default_factory=dict)
    failures: dict[str, int] = field(default_factory=dict)


def state_to_json(state: State) -> str:
    episodes = sorted(state.episodes.values(), key=lambda episode: episode.published, reverse=True)
    data = {
        "episodes": [{**asdict(episode), "published": episode.published.isoformat()} for episode in episodes],
        "failures": state.failures,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def state_from_json(text: str) -> State:
    data = json.loads(text)
    episodes = [Episode(**{**raw, "published": datetime.fromisoformat(raw["published"])}) for raw in data["episodes"]]
    return State(episodes={episode.id: episode for episode in episodes}, failures=data["failures"])
