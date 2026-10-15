import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from factories import make_episode, make_feed_config
from sybarite_feed.rss import ATOM, ITUNES, build_feed

NS = {"itunes": ITUNES, "atom": ATOM}
BASE_URL = "https://feed.example.com/"


def parse(xml: bytes) -> ET.Element:
    return ET.fromstring(xml).find("channel")


def test_channel_has_directory_tags():
    channel = parse(build_feed([], make_feed_config(), BASE_URL))
    assert channel.findtext("title") == "Записки воинствующего сибарита"
    assert channel.findtext("language") == "ru"
    assert channel.find("atom:link", NS).get("href") == "https://feed.example.com/feed.xml"
    assert channel.find("itunes:image", NS).get("href") == "https://feed.example.com/cover.jpg"
    assert channel.findtext("image/url") == "https://feed.example.com/cover.jpg"
    assert channel.findtext("itunes:author", namespaces=NS) == "Геннадий Вальдберг"
    assert channel.findtext("itunes:explicit", namespaces=NS) == "false"
    category = channel.find("itunes:category", NS)
    assert category.get("text") == "Society & Culture"
    assert category.find("itunes:category", NS).get("text") == "Philosophy"


def test_owner_only_when_email_is_set():
    assert parse(build_feed([], make_feed_config(), BASE_URL)).find("itunes:owner", NS) is None
    channel = parse(build_feed([], make_feed_config(owner_email="me@example.com"), BASE_URL))
    assert channel.findtext("itunes:owner/itunes:name", namespaces=NS) == "Геннадий Вальдберг"
    assert channel.findtext("itunes:owner/itunes:email", namespaces=NS) == "me@example.com"


def test_channel_description_ends_with_donate_and_credit_links():
    feed = make_feed_config(
        description="О канале.\n\nПочта & сайт",
        donate_url="https://www.paypal.com/donate?hosted_button_id=X&a=1",
        credit="BuHogeJI",
        credit_url="https://github.com/BuHogeJI2/sybarite-feed",
    )
    assert parse(build_feed([], feed, BASE_URL)).findtext("description") == (
        "<p>О канале.</p>"
        "<p>Почта &amp; сайт</p>"
        "<p>Поддержать канал через PayPal: "
        '<a href="https://www.paypal.com/donate?hosted_button_id=X&amp;a=1">'
        "https://www.paypal.com/donate?hosted_button_id=X&amp;a=1</a></p>"
        '<p>Feed created by <a href="https://github.com/BuHogeJI2/sybarite-feed">BuHogeJI</a></p>'
    )


def test_channel_description_without_links():
    assert parse(build_feed([], make_feed_config(), BASE_URL)).findtext("description") == "<p>Лекции</p>"


def test_episode_item():
    item = parse(build_feed([make_episode()], make_feed_config(), BASE_URL)).find("item")
    assert item.findtext("title") == "Трусость или мудрость? №184"
    assert item.find("guid").text == "2NgIPVQbK8g"
    assert item.find("guid").get("isPermaLink") == "false"
    assert item.findtext("pubDate") == "Thu, 01 Oct 2026 12:30:05 GMT"
    assert item.findtext("itunes:duration", namespaces=NS) == "1696"
    enclosure = item.find("enclosure")
    assert enclosure.attrib == {
        "url": "https://feed.example.com/audio/2NgIPVQbK8g.m4a",
        "length": "27436185",
        "type": "audio/x-m4a",
    }


def test_description_is_escaped_html_with_video_link():
    item = parse(build_feed([make_episode()], make_feed_config(), BASE_URL)).find("item")
    assert item.findtext("description") == (
        "<p>Первый абзац.<br>Вторая строка.</p>"
        "<p>Сократ &amp; Платон &lt;3</p>"
        '<p><a href="https://www.youtube.com/watch?v=2NgIPVQbK8g">Видео на YouTube</a></p>'
    )


def test_items_are_newest_first():
    old = make_episode("old", published=datetime(2020, 1, 1, tzinfo=UTC))
    new = make_episode("new")
    channel = parse(build_feed([old, new], make_feed_config(), BASE_URL))
    assert [item.findtext("guid") for item in channel.findall("item")] == ["new", "old"]
