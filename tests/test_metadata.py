import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sybarite_feed.metadata import OEMBED_URL, original_title

RECORDED = json.loads((Path(__file__).parent / "data" / "oembed_2NgIPVQbK8g.json").read_text())


def test_original_title_comes_from_oembed():
    requested = []

    def fetch(url: str) -> dict:
        requested.append(url)
        return RECORDED

    assert original_title("2NgIPVQbK8g", fetch) == "Трусость или мудрость? №184"
    url = urlparse(requested[0])
    assert f"{url.scheme}://{url.netloc}{url.path}" == OEMBED_URL
    assert parse_qs(url.query) == {"format": ["json"], "url": ["https://www.youtube.com/watch?v=2NgIPVQbK8g"]}
