import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChannelConfig:
    url: str
    audio_format: str
    min_duration: int
    batch_size: int


@dataclass(frozen=True)
class Config:
    channel: ChannelConfig


def load_config(path: Path = Path("config.toml")) -> Config:
    with path.open("rb") as file:
        data = tomllib.load(file)
    return Config(channel=ChannelConfig(**data["channel"]))
