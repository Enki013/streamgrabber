from __future__ import annotations

import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

IMDB_ID_RE = re.compile(r"tt\d{7,10}", re.I)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
STREAMIMDB_BASE = "https://streamimdb.ru/embed"


def extract_imdb_id(value: str) -> str | None:
    match = IMDB_ID_RE.search(value.strip())
    return match.group(0).lower() if match else None


def streamimdb_url(imdb_id: str, media_type: str = "movie") -> str:
    media = "tv" if media_type == "tv" else "movie"
    return f"{STREAMIMDB_BASE}/{media}/{imdb_id}"


def resolve_imdb_media_type(imdb_id: str) -> str:
    """Return StreamIMDB media type for an IMDb title id.

    playimdb.com used to redirect IMDb inputs to StreamIMDB, but that service is
    gone. IMDb's suggestion endpoint is lightweight and exposes qid values like
    `movie` and `tvSeries`, which is enough to choose /embed/movie or /embed/tv.
    If IMDb metadata is unavailable, fall back to movie so bare IDs still produce
    a valid deterministic StreamIMDB URL; users can always pass /embed/tv/...
    directly for TV.
    """
    url = f"https://v2.sg.media-imdb.com/suggestion/t/{imdb_id}.json"
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=15) as res:
        payload = json.loads(res.read().decode("utf-8", "replace"))

    for item in payload.get("d") or []:
        if str(item.get("id", "")).lower() != imdb_id.lower():
            continue
        qid = str(item.get("qid") or item.get("q") or "").lower()
        if "tv" in qid or "series" in qid:
            return "tv"
        return "movie"

    return "movie"


def normalize_input_url(value: str, media_type_resolver=resolve_imdb_media_type) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower()

    if host.endswith("streamimdb.ru"):
        return raw

    imdb_id = extract_imdb_id(raw)
    if not imdb_id:
        return raw

    if not parsed.scheme or host.endswith("imdb.com") or host.endswith("playimdb.com"):
        try:
            media_type = media_type_resolver(imdb_id)
        except Exception:
            media_type = "movie"
        return streamimdb_url(imdb_id, media_type)

    return raw
