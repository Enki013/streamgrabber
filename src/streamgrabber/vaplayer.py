from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .naming import sanitize_filename

STREAMDATA_API = "https://streamdata.vaplayer.ru/api.php"
DEFAULT_REFERER = "https://nextgencloudfabric.com/"


@dataclass(frozen=True)
class EpisodeInfo:
    season: int
    episode: int
    title: str
    file_name: str
    stream_urls: list[str]
    eps: dict[str, list[str]]
    default_subs: list[dict]


def parse_media_id_from_url(url: str) -> tuple[str, str]:
    path = urlparse(url).path
    match = re.search(r"/embed/(tv|movie)/([^/?#]+)", path)
    if not match:
        raise ValueError(f"Cannot parse media id from URL: {url}")
    return match.group(1), match.group(2)


def build_streamdata_url(media_id: str, media_type: str, season: int | None = None, episode: int | None = None) -> str:
    id_param = "imdb" if media_id.startswith("tt") else "tmdb"
    url = f"{STREAMDATA_API}?{id_param}={media_id}&type={media_type}"
    if media_type == "tv" and season is not None and episode is not None:
        url += f"&season={season}&episode={episode}"
    return url


def fetch_streamdata(media_id: str, media_type: str, season: int | None = None, episode: int | None = None) -> dict:
    url = build_streamdata_url(media_id, media_type, season, episode)
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Referer": DEFAULT_REFERER,
            "Origin": DEFAULT_REFERER.rstrip("/"),
        },
    )
    with urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8", "replace"))


def episode_output_name(title: str, season: int, episode: int, file_name: str = "") -> str:
    # Prefer clean show title + explicit SxxExx. The upstream file_name is often noisy release text.
    base = sanitize_filename(title or "streamgrabber-output")
    return f"{base} S{season:02d}E{episode:02d}.mkv"


def movie_output_name(title: str, file_name: str = "") -> str:
    # Prefer API title; upstream file_name is often noisy release text and may include directories.
    base = sanitize_filename(title or Path(file_name).stem or "streamgrabber-output")
    return f"{base}.mkv"


def episode_info(media_id: str, media_type: str, season: int | None = None, episode: int | None = None) -> EpisodeInfo:
    payload = fetch_streamdata(media_id, media_type, season, episode)
    data = payload.get("data") or {}
    return EpisodeInfo(
        season=int(data.get("season") or season or 1),
        episode=int(data.get("episode") or episode or 1),
        title=str(data.get("title") or ""),
        file_name=str(data.get("file_name") or ""),
        stream_urls=list(data.get("stream_urls") or []),
        eps={str(k): [str(x) for x in v] for k, v in (data.get("eps") or {}).items()},
        default_subs=list(payload.get("default_subs") or []),
    )


def episodes_for_season(info: EpisodeInfo, season: int) -> list[int]:
    return [int(ep) for ep in info.eps.get(str(season), [])]
