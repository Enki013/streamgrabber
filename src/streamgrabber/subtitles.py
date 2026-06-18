from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
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

QUALITY_PATTERNS: dict[str, re.Pattern[str]] = {
    "2160p": re.compile(r"2160p|4k|uhd", re.I),
    "1080p": re.compile(r"1080p|1080i", re.I),
    "720p": re.compile(r"720p", re.I),
    "480p": re.compile(r"480p", re.I),
    "HDRip": re.compile(r"hdrip", re.I),
    "BDRip": re.compile(r"bdrip|brrip", re.I),
    "DVDRip": re.compile(r"dvdrip", re.I),
    "WEBRip": re.compile(r"webrip", re.I),
    "WEB-DL": re.compile(r"web-?dl", re.I),
    "HDTV": re.compile(r"hdtv", re.I),
    "BluRay": re.compile(r"blu-?ray|bdremux", re.I),
    "CAM": re.compile(r"cam|camrip|hdcam", re.I),
    "TS": re.compile(r"\bts\b|telesync|hdts", re.I),
    "SCR": re.compile(r"scr|screener|dvdscr", re.I),
}
CODEC_PATTERNS: dict[str, re.Pattern[str]] = {
    "x264": re.compile(r"x264|h\.?264", re.I),
    "x265": re.compile(r"x265|h\.?265|hevc", re.I),
    "XviD": re.compile(r"xvid", re.I),
    "DivX": re.compile(r"divx", re.I),
    "AV1": re.compile(r"\bav1\b", re.I),
}
AUDIO_PATTERNS: dict[str, re.Pattern[str]] = {
    "DTS": re.compile(r"\bdts\b", re.I),
    "AC3": re.compile(r"ac3|dd5\.?1", re.I),
    "AAC": re.compile(r"\baac\b", re.I),
    "FLAC": re.compile(r"flac", re.I),
    "Atmos": re.compile(r"atmos", re.I),
    "TrueHD": re.compile(r"truehd", re.I),
}
HD_QUALITY_TIERS = {"BluRay", "BDRip", "WEB-DL", "WEBRip", "HDRip", "HDTV"}
RAW_QUALITY_TIERS = {"CAM", "TS", "SCR"}
RELEASE_GROUP_PATTERN = re.compile(r"[-\[]([A-Za-z0-9]+)(?:\])?$")
YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
SEASON_EPISODE_PATTERN = re.compile(r"S(\d{1,2})E(\d{1,2})", re.I)


@dataclass(frozen=True)
class ParsedRelease:
    original: str
    title: str = ""
    year: int | None = None
    quality: str | None = None
    resolution: str | None = None
    codec: str | None = None
    audio: str | None = None
    release_group: str | None = None
    season: int | None = None
    episode: int | None = None


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


def parse_release(filename: str) -> ParsedRelease | None:
    """Parse release metadata using the same PTT heuristics as StreamIMDB's player JS."""
    if not filename:
        return None

    clean = re.sub(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|srt|sub|ass|vtt)$", "", filename, flags=re.I)

    year_match = YEAR_PATTERN.search(clean)
    year = int(year_match.group(0)) if year_match else None

    se_match = SEASON_EPISODE_PATTERN.search(clean)
    season = int(se_match.group(1)) if se_match else None
    episode = int(se_match.group(2)) if se_match else None

    quality = None
    resolution = None
    for name, pattern in QUALITY_PATTERNS.items():
        if pattern.search(clean):
            if name in {"2160p", "1080p", "720p", "480p"}:
                if resolution is None:
                    resolution = name
            elif quality is None:
                # For muxed downloads we care about subtitle sync more than reproducing
                # StreamIMDB's display-only parser quirk. Keep scanning after a resolution
                # token so a BluRay video does not tie with WEBRip solely by downloads.
                quality = name

    codec = next((name for name, pattern in CODEC_PATTERNS.items() if pattern.search(clean)), None)
    audio = next((name for name, pattern in AUDIO_PATTERNS.items() if pattern.search(clean)), None)

    group_match = RELEASE_GROUP_PATTERN.search(clean)
    release_group = group_match.group(1) if group_match else None

    title_end = len(clean)
    if year_match:
        title_end = min(title_end, year_match.start())
    for pattern in QUALITY_PATTERNS.values():
        match = pattern.search(clean)
        if match:
            title_end = min(title_end, match.start())

    title = re.sub(r"\s+", " ", re.sub(r"[._-]", " ", clean[:title_end])).strip().lower()
    return ParsedRelease(
        original=filename,
        title=title,
        year=year,
        quality=quality,
        resolution=resolution,
        codec=codec,
        audio=audio,
        release_group=release_group,
        season=season,
        episode=episode,
    )


def streamimdb_match_score(video_info: ParsedRelease | None, subtitle_filename: str) -> int:
    """Score a subtitle filename like StreamIMDB's PTT.matchScore."""
    if not video_info or not subtitle_filename:
        return 0
    sub_info = parse_release(subtitle_filename)
    if not sub_info:
        return 0

    score = 0.0

    vq = video_info.quality
    sq = sub_info.quality
    if vq and sq:
        if vq == sq:
            score += 25
        elif vq in HD_QUALITY_TIERS and sq in HD_QUALITY_TIERS:
            score += 8
        elif vq in HD_QUALITY_TIERS and sq in RAW_QUALITY_TIERS:
            score -= 50
        elif vq in RAW_QUALITY_TIERS and sq in HD_QUALITY_TIERS:
            score -= 20
    elif vq and vq in HD_QUALITY_TIERS and not sq:
        score += 3

    if video_info.resolution and sub_info.resolution:
        if video_info.resolution == sub_info.resolution:
            score += 10

    if video_info.title and sub_info.title:
        video_words = [w for w in video_info.title.split() if len(w) > 2]
        subtitle_words = {w for w in sub_info.title.split() if len(w) > 2}
        if video_words:
            matched = sum(1 for w in video_words if w in subtitle_words)
            score += (matched / len(video_words)) * 35

    if video_info.year and sub_info.year:
        if video_info.year == sub_info.year:
            score += 15
        else:
            score -= 12

    if video_info.season is not None and video_info.episode is not None:
        if sub_info.season == video_info.season and sub_info.episode == video_info.episode:
            score += 25
        elif sub_info.season is not None or sub_info.episode is not None:
            score -= 35

    if video_info.release_group and sub_info.release_group:
        if video_info.release_group.lower() == sub_info.release_group.lower():
            score += 20

    if video_info.codec and sub_info.codec and video_info.codec == sub_info.codec:
        score += 5

    return round(score)


def _download_tiebreaker(sub: dict) -> int:
    try:
        downloads = int(sub.get("SubDownloadsCnt") or 0)
    except Exception:
        downloads = 0
    if downloads > 10000:
        return 3
    if downloads > 1000:
        return 2
    if downloads > 100:
        return 1
    return 0


def _downloads(sub: dict) -> int:
    try:
        return int(sub.get("SubDownloadsCnt") or 0)
    except Exception:
        return 0


def choose_best_subtitle(
    subtitles: list[dict],
    *,
    title: str = "",
    file_name: str = "",
    season: int | None = None,
    episode: int | None = None,
) -> dict | None:
    """
    Choose the subtitle the way StreamIMDB auto-selects it.

    The player parses the exact upstream video release name (`response.data.file_name`) and
    uses PTT.matchScore against OpenSubtitles filenames. When no strong release match scores
    at least 50, it falls back to the highest download count. `season`/`episode` are injected
    into the parsed video info because StreamIMDB sets CONFIG.season/episode after fetching
    the selected episode.
    """
    if not subtitles:
        return None

    video_info = parse_release(file_name or title)
    if video_info and season is not None and episode is not None:
        video_info = ParsedRelease(
            original=video_info.original,
            title=video_info.title,
            year=video_info.year,
            quality=video_info.quality,
            resolution=video_info.resolution,
            codec=video_info.codec,
            audio=video_info.audio,
            release_group=video_info.release_group,
            season=season if video_info.season is None else video_info.season,
            episode=episode if video_info.episode is None else video_info.episode,
        )

    scored: list[tuple[int, int, int, dict]] = []
    if video_info:
        for index, sub in enumerate(subtitles):
            filename = sub.get("SubFileName") or sub.get("MovieReleaseName") or ""
            score = streamimdb_match_score(video_info, filename) + _download_tiebreaker(sub)
            scored.append((score, -index, index, sub))

        best_score, _, _, best_sub = max(scored, key=lambda item: (item[0], item[1]))
        # StreamIMDB's auto path requires a strong score (>=50) before auto-loading.
        if best_score >= 50:
            return best_sub

    # Exact StreamIMDB fallback: no strong PTT match => most downloaded subtitle.
    return max(enumerate(subtitles), key=lambda item: (_downloads(item[1]), -item[0]))[1]


def choose_default_subtitle(default_subs: list[dict], language: str) -> dict | None:
    """Choose VaPlayer default subtitle matching the requested language, if present."""
    if not default_subs:
        return None
    lang3 = language_to_opensubtitles_id(language)
    lang2 = {"tur": "tr", "eng": "en"}.get(lang3, language.lower()[:2])
    for sub in default_subs:
        code = str(sub.get("code") or sub.get("lang") or "").strip().lower()
        if code in {lang2, lang3}:
            return sub
    return None


def download_default_subtitle_as_vtt(subtitle: dict, output: str | Path) -> Path:
    """Download a VaPlayer default subtitle URL and store it as UTF-8 WebVTT."""
    link = subtitle.get("url")
    if not link:
        raise ValueError("Default subtitle has no url")
    req = Request(str(link), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as res:
        raw = res.read()
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = raw.decode("utf-8", "replace")
    vtt = srt_to_vtt(text)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(vtt, encoding="utf-8")
    return path


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
