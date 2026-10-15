from sybarite_feed.episode import xml_safe


def test_xml_safe_drops_forbidden_characters_only():
    assert xml_safe("a\x01b\x0bc￾\ud800") == "abc"
    assert xml_safe("Строка\tс\nпереводом\r 😀 «»") == "Строка\tс\nпереводом\r 😀 «»"
