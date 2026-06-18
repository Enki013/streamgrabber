from __future__ import annotations

import re
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

IMDB_ID_RE = re.compile(r"tt\d{7,10}", re.I)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"


def extract_imdb_id(value: str) -> str | None:
    match = IMDB_ID_RE.search(value.strip())
    return match.group(0).lower() if match else None


def playimdb_url(imdb_id: str) -> str:
    return f"https://www.playimdb.com/title/{imdb_id}"


def resolve_redirect_url(url: str) -> str:
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    opener = build_opener(HTTPRedirectHandler)
    with opener.open(req, timeout=30) as res:
        return res.url


def normalize_input_url(value: str, redirect_resolver=resolve_redirect_url) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower()

    if host.endswith("streamimdb.ru"):
        return raw

    imdb_id = extract_imdb_id(raw)
    if not imdb_id:
        return raw

    if not parsed.scheme or host.endswith("imdb.com") or host.endswith("playimdb.com"):
        return redirect_resolver(playimdb_url(imdb_id))

    return raw
