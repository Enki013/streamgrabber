from __future__ import annotations

import subprocess
from pathlib import Path


def build_ffmpeg_mux_command(video: str, subtitle: str | None, output: str) -> list[str]:
    if subtitle:
        return [
            "ffmpeg",
            "-y",
            "-i",
            video,
            "-i",
            subtitle,
            "-c",
            "copy",
            "-c:s",
            "webvtt",
            output,
        ]
    return ["ffmpeg", "-y", "-i", video, "-c", "copy", output]


def mux(video: str, subtitle: str | None, output: str) -> None:
    Path(output).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_ffmpeg_mux_command(video, subtitle, output), check=True)
