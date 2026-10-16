import html
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from email.utils import format_datetime
from urllib.parse import quote

from sybarite_feed.config import FeedConfig
from sybarite_feed.episode import Episode

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM = "http://www.w3.org/2005/Atom"
COVER_KEY = "cover.jpg"
# the author separates sections with lines of ~130 dashes, often at the end of a text line;
# they took about a tenth of the feed
SEPARATOR = re.compile(r"[ \t]*-{5,}[ \t]*")
TRAILING_SPACES = re.compile(r"[ \t]+$", re.MULTILINE)

ET.register_namespace("itunes", ITUNES)
ET.register_namespace("atom", ATOM)


def build_feed(episodes: Iterable[Episode], feed: FeedConfig, base_url: str) -> bytes:
    base_url = base_url.rstrip("/")
    cover_url = f"{base_url}/{COVER_KEY}"

    rss = ET.Element("rss", version="2.0")
    channel = _sub(rss, "channel")
    _sub(channel, "title", feed.title)
    _sub(channel, "link", feed.link)
    _sub(channel, "description", channel_html(feed))
    _sub(channel, "language", feed.language)
    ET.SubElement(channel, f"{{{ATOM}}}link", href=f"{base_url}/feed.xml", rel="self", type="application/rss+xml")
    image = _sub(channel, "image")
    _sub(image, "url", cover_url)
    _sub(image, "title", feed.title)
    _sub(image, "link", feed.link)
    _sub(channel, _itunes("author"), feed.author)
    ET.SubElement(channel, _itunes("image"), href=cover_url)
    category = ET.SubElement(channel, _itunes("category"), text=feed.category)
    if feed.subcategory:
        ET.SubElement(category, _itunes("category"), text=feed.subcategory)
    _sub(channel, _itunes("explicit"), "false")
    _sub(channel, _itunes("type"), "episodic")
    if feed.owner_email:
        owner = _sub(channel, _itunes("owner"))
        _sub(owner, _itunes("name"), feed.owner_name or feed.author)
        _sub(owner, _itunes("email"), feed.owner_email)

    for episode in sorted(episodes, key=lambda episode: episode.published, reverse=True):
        item = _sub(channel, "item")
        _sub(item, "title", episode.title)
        _sub(item, "description", episode_html(episode))
        _sub(item, "link", episode.video_url)
        _sub(item, "guid", episode.id, isPermaLink="false")
        _sub(item, "pubDate", format_datetime(episode.published, usegmt=True))
        ET.SubElement(
            item,
            "enclosure",
            url=f"{base_url}/audio/{quote(episode.file_name)}",
            length=str(episode.size),
            type=episode.mime_type,
        )
        _sub(item, _itunes("duration"), str(episode.duration))

    ET.indent(rss)
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def channel_html(feed: FeedConfig) -> str:
    body = _paragraphs_html(feed.description)
    if feed.donate_url:
        donate_url = html.escape(feed.donate_url)
        # Apple Podcasts drops <a> tags in the show description and links only bare URLs
        body += f'<p>Поддержать канал через PayPal: <a href="{donate_url}">{donate_url}</a></p>'
    if feed.credit:
        credit = html.escape(feed.credit)
        if feed.credit_url:
            credit = f'<a href="{html.escape(feed.credit_url)}">{credit}</a>'
        body += f"<p>Feed created by {credit}</p>"
    return body


def episode_html(episode: Episode) -> str:
    body = _paragraphs_html(_tidy(episode.description))
    return f'{body}<p><a href="{html.escape(episode.video_url)}">Видео на YouTube</a></p>'


def _tidy(description: str) -> str:
    return TRAILING_SPACES.sub("", SEPARATOR.sub("\n\n", description))


def _paragraphs_html(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return "".join(f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>" for paragraph in paragraphs)


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attributes: str) -> ET.Element:
    element = ET.SubElement(parent, tag, attributes)
    element.text = text
    return element


def _itunes(tag: str) -> str:
    return f"{{{ITUNES}}}{tag}"
