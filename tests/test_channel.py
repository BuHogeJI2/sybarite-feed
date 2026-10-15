from sybarite_feed.channel import ChannelVideo, videos_from_listing


def test_videos_from_listing():
    listing = {"entries": [{"id": "a", "duration": 1346.0}, {"id": "b", "duration": None}, {"id": "c"}]}
    assert videos_from_listing(listing) == [
        ChannelVideo(id="a", duration=1346),
        ChannelVideo(id="b", duration=None),
        ChannelVideo(id="c", duration=None),
    ]
