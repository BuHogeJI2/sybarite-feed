import re
from pathlib import Path

# yt-dlp prints a rejected cookie line, value included, and the GitHub secret mask doesn't match its
# repr() form; so every line yt-dlp or http.cookiejar would reject must be caught here first
HEADER = re.compile(r"#( Netscape)? HTTP Cookie File")
HTTPONLY_PREFIX = "#HttpOnly_"
EXPIRES = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?)?")
FLAGS = ("TRUE", "FALSE")
# shorter values aren't secret, and masking them would hide common words in the log
MIN_MASKED_LENGTH = 8


class InvalidCookieFile(ValueError):
    pass


def cookie_values(path: str | Path) -> list[str]:
    """Checks a Netscape cookies.txt file and returns its cookie values.

    Raises InvalidCookieFile with a message that never contains the file's content.
    """
    values = []
    try:
        with open(path, encoding="utf-8") as file:
            if not HEADER.match(file.readline()):
                raise InvalidCookieFile("line 1: not a Netscape cookies.txt header")
            for number, line in enumerate(file, start=2):
                line = line.removeprefix(HTTPONLY_PREFIX).removesuffix("\n")
                if line.startswith("#") or not line.strip():
                    continue
                values.append(_cookie_value(number, line))
    except UnicodeDecodeError:
        raise InvalidCookieFile("the file is not UTF-8") from None
    return values


def _cookie_value(number: int, line: str) -> str:
    fields = line.split("\t")
    if len(fields) != 7:
        raise InvalidCookieFile(f"line {number}: expected 7 tab-separated fields, got {len(fields)}")
    domain, include_subdomains, _, https_only, expires, _, value = fields
    if include_subdomains not in FLAGS or https_only not in FLAGS:
        raise InvalidCookieFile(f"line {number}: flags must be TRUE or FALSE")
    if (include_subdomains == "TRUE") != domain.startswith("."):
        raise InvalidCookieFile(f"line {number}: the subdomain flag doesn't match the domain")
    if not EXPIRES.fullmatch(expires) or not _converts_like_cookiejar(expires):
        raise InvalidCookieFile(f"line {number}: invalid expiry")
    return value


def _converts_like_cookiejar(expires: str) -> bool:
    try:
        if expires:
            int(float(expires))
    except OverflowError:
        return False
    return True


def mask_commands(values: list[str]) -> list[str]:
    return [f"::add-mask::{_escape(value)}" for value in values if len(value) >= MIN_MASKED_LENGTH]


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
