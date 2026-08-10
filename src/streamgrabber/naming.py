from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN = r'[/\\?%*:|"<>]'


def sanitize_filename(title: str, fallback: str = "streamgrabber-output") -> str:
    cleaned = title or ""
    cleaned = re.sub(r"[/\\]", "_", cleaned)
    cleaned = re.sub(r"[?%*:|\"<>]", " ", cleaned)
    cleaned = cleaned.replace("'", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._\t\n\r")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or fallback


def output_path_from_title(title: str, directory: str | Path = ".", extension: str = ".mkv") -> Path:
    if not extension.startswith("."):
        extension = f".{extension}"
    return Path(directory) / f"{sanitize_filename(title)}{extension}"
