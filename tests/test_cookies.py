import pytest
from yt_dlp.cookies import YoutubeDLCookieJar

from sybarite_feed.cookies import InvalidCookieFile, cookie_values, mask_commands

HEADER = "# Netscape HTTP Cookie File\n"
SECRET = "SECRETVALUE123"


def cookie_file(tmp_path, *lines: str):
    path = tmp_path / "cookies.txt"
    path.write_text(HEADER + "".join(f"{line}\n" for line in lines), encoding="utf-8")
    return path


def row(domain=".youtube.com", subdomains="TRUE", https="TRUE", expires="1790000000", value=SECRET):
    return "\t".join([domain, subdomains, "/", https, expires, "SID", value])


def test_returns_values_and_skips_comments(tmp_path):
    path = cookie_file(
        tmp_path,
        "# a comment",
        "",
        row(),
        f"#HttpOnly_{row(value='other')}",
        row(domain="www.youtube.com", subdomains="FALSE", expires=""),
    )
    assert cookie_values(path) == [SECRET, "other", SECRET]


def test_accepted_file_loads_silently_in_yt_dlp(tmp_path, capfd):
    path = cookie_file(tmp_path, row(), f"#HttpOnly_{row()}", row(expires="1790000000.5"), row(expires="0"))
    cookie_values(path)

    YoutubeDLCookieJar(str(path)).load()

    assert capfd.readouterr() == ("", "")


@pytest.mark.parametrize(
    "line",
    [
        row().replace("\t", " ", 1),
        row() + "\textra",
        row(expires="soon"),
        row(https="yes"),
        row(subdomains="FALSE"),
        row(domain="youtube.com"),
        f"#HttpOnly_{row(expires='soon')}",
        f" {row()}",
        row(expires="9" * 400),
    ],
)
def test_bad_line_names_the_line_but_not_the_value(tmp_path, line):
    path = cookie_file(tmp_path, row(), line)

    with pytest.raises(InvalidCookieFile) as error:
        cookie_values(path)

    assert str(error.value).startswith("line 3:")
    assert SECRET not in str(error.value)


def test_header_is_required(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text(row() + "\n", encoding="utf-8")
    with pytest.raises(InvalidCookieFile, match="line 1"):
        cookie_values(path)


@pytest.mark.parametrize("content", ["", "\n"])
def test_empty_file_is_invalid(tmp_path, content):
    path = tmp_path / "cookies.txt"
    path.write_text(content)
    with pytest.raises(InvalidCookieFile):
        cookie_values(path)


def test_mask_commands_skip_short_values_and_escape():
    assert mask_commands(["1", "abc%2Fdef=", SECRET]) == ["::add-mask::abc%252Fdef=", f"::add-mask::{SECRET}"]
