from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from yt_dlp import YoutubeDL

from sybarite_feed.channel import watch_url
from sybarite_feed.episode import Episode
from sybarite_feed.metadata import original_title

MIME_TYPES = {"m4a": "audio/x-m4a", "mp3": "audio/mpeg"}


@dataclass(frozen=True)
class DownloadedAudio:
    episode: Episode
    path: Path


def download_audio(video_id: str, out_dir: Path, audio_format: str, cookie_file: str | None = None) -> DownloadedAudio:
    title = original_title(video_id)
    options = {
        "format": audio_format,
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        # the default English request returns machine-translated descriptions
        "extractor_args": {"youtube": {"lang": ["ru"]}},
        "quiet": True,
        "noprogress": True,
    }
    if cookie_file:
        options["cookiefile"] = cookie_file
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(watch_url(video_id), download=True)

    path = Path(info["requested_downloads"][0]["filepath"])
    episode = Episode(
        id=video_id,
        title=title,
        description=info.get("description") or "",
        published=published_at(info),
        duration=int(info["duration"]),
        file_name=path.name,
        size=path.stat().st_size,
        mime_type=MIME_TYPES[path.suffix.removeprefix(".")],
        video_url=watch_url(video_id),
    )
    return DownloadedAudio(episode=episode, path=path)


def published_at(info: dict) -> datetime:
    if info.get("timestamp"):
        return datetime.fromtimestamp(info["timestamp"], UTC)
    return datetime.strptime(info["upload_date"], "%Y%m%d").replace(tzinfo=UTC)
