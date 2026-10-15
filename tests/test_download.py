from datetime import UTC, datetime

from sybarite_feed.download import published_at


def test_published_at_prefers_timestamp():
    info = {"timestamp": 1759831200, "upload_date": "20251001"}
    assert published_at(info) == datetime(2025, 10, 7, 10, 0, tzinfo=UTC)


def test_published_at_falls_back_to_upload_date():
    assert published_at({"upload_date": "20251001"}) == datetime(2025, 10, 1, tzinfo=UTC)
