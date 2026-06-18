from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

OPEN_SUBTITLES_SEARCH = "https://rest.opensubtitles.org/search"
OPEN_SUBTITLES_UA = "trailers.to-UA"

LANG_MAP = {
    "tr": "tur",
    "tur": "tur",
    "turkish": "tur",
    "türkçe": "tur",
    "turkce": "tur",
    "en": "eng",
    "eng": "eng",
    "english": "eng",
}


def language_to_opensubtitles_id(language: str) -> str:
    key = (language or "").strip().lower()
    return LANG_MAP.get(key, key)


def _numeric_imdb_id(imdb_id: str) -> str:
    return re.sub(r"^tt", "", imdb_id.strip(), flags=re.I)


def build_opensubtitles_search_url(
    imdb_id: str,
    language: str,
    *,
    season: int | None = None,
    episode: int | None = None,
) -> str:
    lang = language_to_opensubtitles_id(language)
    numeric = _numeric_imdb_id(imdb_id)
    if season is not None and episode is not None:
        return f"{OPEN_SUBTITLES_SEARCH}/episode-{episode}/imdbid-{numeric}/season-{season}/sublanguageid-{lang}"
    return f"{OPEN_SUBTITLES_SEARCH}/imdbid-{numeric}/sublanguageid-{lang}"


def search_subtitles(
    imdb_id: str,
    language: str,
    *,
    season: int | None = None,
    episode: int | None = None,
) -> list[dict]:
    url = build_opensubtitles_search_url(imdb_id, language, season=season, episode=episode)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "X-User-Agent": OPEN_SUBTITLES_UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode("utf-8", "replace"))
    return data if isinstance(data, list) else []


def srt_to_vtt(srt: str) -> str:
    if srt.lstrip("\ufeff\r\n ").startswith("WEBVTT"):
        return srt
    lines = srt.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = ["WEBVTT", ""]
    for line in lines:
        if re.fullmatch(r"\s*\d+\s*", line):
            continue
        if "-->" in line:
            line = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", line)
        out.append(line)
    return "\n".join(out).strip() + "\n"


def _score_subtitle(sub: dict, *, title: str = "", season: int | None = None, episode: int | None = None) -> tuple[int, int]:
    name = f"{sub.get('SubFileName', '')} {sub.get('MovieReleaseName', '')}".lower()
    score = 0
    if season is not None and episode is not None:
        patterns = [
            f"s{season:02d}e{episode:02d}",
            f"s{season}e{episode}",
            f"{season}x{episode:02d}",
            f"{season}x{episode}",
        ]
        if any(p in name for p in patterns):
            score += 100
        elif re.search(r"s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3}", name):
            score -= 100
    for token in re.findall(r"[a-z0-9]+", title.lower()):
        if len(token) >= 4 and token in name:
            score += 5
    try:
        downloads = int(sub.get("SubDownloadsCnt") or 0)
    except Exception:
        downloads = 0
    return score, downloads


def choose_best_subtitle(
    subtitles: list[dict],
    *,
    title: str = "",
    season: int | None = None,
    episode: int | None = None,
) -> dict | None:
    if not subtitles:
        return None
    return max(subtitles, key=lambda s: _score_subtitle(s, title=title, season=season, episode=episode))


def download_subtitle_as_vtt(subtitle: dict, output: str | Path) -> Path:
    link = subtitle.get("SubDownloadLink")
    if not link:
        raise ValueError("Subtitle has no SubDownloadLink")
    req = Request(link, headers={"User-Agent": "Mozilla/5.0", "X-User-Agent": OPEN_SUBTITLES_UA})
    with urlopen(req, timeout=60) as res:
        raw = res.read()
    try:
        text_bytes = gzip.decompress(raw)
    except gzip.BadGzipFile:
        text_bytes = raw
    encoding = subtitle.get("SubEncoding") or "utf-8"
    try:
        text = text_bytes.decode(encoding, "replace")
    except LookupError:
        text = text_bytes.decode("utf-8", "replace")
    vtt = srt_to_vtt(text)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(vtt, encoding="utf-8")
    return path
