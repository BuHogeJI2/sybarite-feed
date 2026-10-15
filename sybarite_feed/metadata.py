import json
from collections.abc import Callable
from urllib.parse import urlencode
from urllib.request import urlopen

from sybarite_feed.channel import watch_url

OEMBED_URL = "https://www.youtube.com/oembed"


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


# YouTube translates titles into the language of the request; oEmbed always returns the original
def original_title(video_id: str, fetch: Callable[[str], dict] = fetch_json) -> str:
    query = urlencode({"format": "json", "url": watch_url(video_id)})
    return fetch(f"{OEMBED_URL}?{query}")["title"]
