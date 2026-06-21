from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable

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


def run_command_with_retries(
    command_factory: Callable[[int], list[str]],
    *,
    attempts: int = 3,
    retry_delay_seconds: float = 2.0,
    before_retry: Callable[[int, BaseException], None] | None = None,
) -> None:
    """Run a command with retries. command_factory receives the 1-based attempt number."""
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            subprocess.run(command_factory(attempt), check=True)
            return
        except subprocess.CalledProcessError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            if before_retry:
                before_retry(attempt, exc)
            time.sleep(retry_delay_seconds * attempt)
    if last_exc:  # pragma: no cover - defensive only
        raise last_exc


def ensure_parent(path: str | Path) -> None:
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
