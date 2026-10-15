from datetime import UTC, datetime

from sybarite_feed.config import ChannelConfig, Config, FeedConfig, StorageConfig
from sybarite_feed.episode import Episode


def make_episode(video_id: str = "2NgIPVQbK8g", **overrides) -> Episode:
    fields = {
        "id": video_id,
        "title": "Трусость или мудрость? №184",
        "description": "Первый абзац.\nВторая строка.\n\nСократ & Платон <3",
        "published": datetime(2026, 10, 1, 12, 30, 5, tzinfo=UTC),
        "duration": 1696,
        "file_name": f"{video_id}.m4a",
        "size": 27436185,
        "mime_type": "audio/x-m4a",
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
    }
    return Episode(**{**fields, **overrides})


def make_feed_config(**overrides) -> FeedConfig:
    fields = {
        "title": "Записки воинствующего сибарита",
        "author": "Геннадий Вальдберг",
        "description": "Лекции",
        "link": "https://www.youtube.com/@GenadiValdberg",
        "language": "ru",
        "category": "Society & Culture",
        "subcategory": "Philosophy",
    }
    return FeedConfig(**{**fields, **overrides})


def make_config(cover: str = "cover.jpg", **channel_overrides) -> Config:
    channel = {
        "url": "https://www.youtube.com/@GenadiValdberg/videos",
        "audio_format": "bestaudio[ext=m4a]",
        "min_duration": 120,
        "batch_size": 50,
    }
    return Config(
        channel=ChannelConfig(**{**channel, **channel_overrides}),
        feed=make_feed_config(cover=cover),
        storage=StorageConfig(base_url="https://feed.example.com"),
    )
