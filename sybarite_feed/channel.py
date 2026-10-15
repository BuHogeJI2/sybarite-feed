from dataclasses import dataclass

from yt_dlp import YoutubeDL


@dataclass(frozen=True)
class ChannelVideo:
    id: str
    duration: int | None


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def list_videos(channel_url: str) -> list[ChannelVideo]:
    with YoutubeDL({"extract_flat": "in_playlist", "quiet": True}) as ydl:
        listing = ydl.extract_info(channel_url, download=False)
    return videos_from_listing(listing)


def videos_from_listing(listing: dict) -> list[ChannelVideo]:
    return [
        ChannelVideo(id=entry["id"], duration=int(entry["duration"]) if entry.get("duration") else None)
        for entry in listing["entries"]
    ]
