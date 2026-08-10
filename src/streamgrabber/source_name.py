from __future__ import annotations

import re

WEAK_TITLES = {"player", "embed", "video", "vidapi", ""}
NOISE_PATTERNS = [
    re.compile(r"^s\d{1,2}$", re.I),
    re.compile(r"^e\d{1,3}$", re.I),
    re.compile(r"^s\d{1,2}e\d{1,3}$", re.I),
    re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$"),
    re.compile(r"^(play|pause|mute|settings|subtitles|fullscreen|cast)$", re.I),
    re.compile(r"^(next|previous)(:.*)?$", re.I),
]
EPISODE_HINT = re.compile(r"(s\d{1,2}\s*e\d{1,3}|\d{4}\s+\d{1,2}-\d{1,3}|\b\d{1,2}x\d{1,3}\b)", re.I)


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def text_candidates(visible_text: str) -> list[str]:
    candidates: list[str] = []
    for raw in visible_text.splitlines():
        line = _clean_line(raw)
        if len(line) < 4 or len(line) > 140:
            continue
        if line.lower() in WEAK_TITLES:
            continue
        if any(pattern.search(line) for pattern in NOISE_PATTERNS):
            continue
        if re.search(r"[A-Za-zÀ-ÿ]", line):
            candidates.append(line)
    return candidates


def choose_source_name(titles: list[str], visible_text: str = "") -> str:
    candidates = text_candidates(visible_text)
    hinted = [candidate for candidate in candidates if EPISODE_HINT.search(candidate)]
    if hinted:
        return hinted[0]
    if candidates:
        return candidates[0]

    useful_titles = [
        _clean_line(title)
        for title in titles
        if _clean_line(title).lower() not in WEAK_TITLES
    ]
    return useful_titles[0] if useful_titles else ""
