import re
from dataclasses import dataclass
from datetime import datetime

# characters XML 1.0 forbids; ElementTree writes them as is, and then the whole feed doesn't parse
XML_INVALID = re.compile(r"[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


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


def xml_safe(text: str) -> str:
    return XML_INVALID.sub("", text)
