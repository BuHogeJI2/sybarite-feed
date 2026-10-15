from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Episode:
    id: str
    title: str
    description: str
    published: datetime
    duration: int
    file_name: str
    size: int
    mime_type: str
    video_url: str
