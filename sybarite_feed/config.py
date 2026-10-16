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
class FeedConfig:
    title: str
    author: str
    description: str
    link: str
    language: str
    category: str
    cover: str = "cover.jpg"
    subcategory: str = ""
    owner_name: str = ""
    owner_email: str = ""
    site_url: str = ""
    donate_url: str = ""
    credit: str = ""
    credit_url: str = ""


@dataclass(frozen=True)
class StorageConfig:
    base_url: str


@dataclass(frozen=True)
class Config:
    channel: ChannelConfig
    feed: FeedConfig
    storage: StorageConfig


def load_config(path: Path = Path("config.toml")) -> Config:
    with path.open("rb") as file:
        data = tomllib.load(file)
    return Config(
        channel=ChannelConfig(**data["channel"]),
        feed=FeedConfig(**data["feed"]),
        storage=StorageConfig(**data["storage"]),
    )
