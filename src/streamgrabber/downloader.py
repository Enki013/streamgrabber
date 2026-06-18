from __future__ import annotations

import subprocess
from pathlib import Path

from .models import DEFAULT_USER_AGENT


def build_ytdlp_command(
    *,
    url: str,
    output: str,
    user_agent: str = DEFAULT_USER_AGENT,
    referer: str | None = None,
    subtitle: str | None = None,
) -> list[str]:
    cmd = [
        "yt-dlp",
        "--no-part",
        "--restrict-filenames",
        "--user-agent",
        user_agent,
        "--merge-output-format",
        "mkv",
        "-o",
        output,
    ]
    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]
    if subtitle:
        cmd += ["--add-header", f"X-Streamgrabber-Subtitle:{subtitle}"]
    cmd.append(url)
    return cmd


def build_streamlink_command(
    *,
    url: str,
    quality: str = "best",
    output: str,
    user_agent: str = DEFAULT_USER_AGENT,
    referer: str | None = None,
    duration: str | None = None,
) -> list[str]:
    cmd = ["streamlink", "--http-header", f"User-Agent={user_agent}"]
    if referer:
        cmd += ["--http-header", f"Referer={referer}"]
    if duration:
        cmd += ["--stream-segmented-duration", duration]
    cmd += ["-o", output, url, quality]
    return cmd


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ensure_parent(path: str | Path) -> None:
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
