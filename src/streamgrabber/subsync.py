from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

TIMESTAMP_RE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})")


def find_ffsubsync() -> str | None:
    """Find ffsubsync even when the venv's bin directory is not on PATH."""
    path = shutil.which("ffsubsync")
    if path:
        return path
    sibling = Path(sys.executable).with_name("ffsubsync")
    if sibling.exists() and sibling.is_file():
        return str(sibling)
    return None


def build_ffsubsync_command(
    video: str | Path,
    subtitle: str | Path,
    output: str | Path,
    *,
    offset_seconds: float = 0.0,
    max_duration_seconds: int | None = None,
    skip_on_low_quality: bool = True,
    executable: str = "ffsubsync",
) -> list[str]:
    cmd = [
        executable,
        str(video),
        "-i",
        str(subtitle),
        "-o",
        str(output),
    ]
    if skip_on_low_quality:
        cmd.append("--skip-sync-on-low-quality")
    if offset_seconds:
        cmd.extend(["--apply-offset-seconds", str(offset_seconds)])
    if max_duration_seconds:
        cmd.extend(["--max-duration-seconds", str(max_duration_seconds)])
    return cmd


def _timestamp_to_ms(match: re.Match[str]) -> int:
    return (
        int(match.group("h")) * 3_600_000
        + int(match.group("m")) * 60_000
        + int(match.group("s")) * 1_000
        + int(match.group("ms"))
    )


def _ms_to_timestamp(ms: int, *, comma: bool = False) -> str:
    ms = max(0, ms)
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    sep = "," if comma else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{millis:03d}"


def shift_subtitle_file(input_path: str | Path, output_path: str | Path, offset_seconds: float) -> Path:
    """Apply a simple fixed offset to SRT/VTT timestamp strings."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    offset_ms = round(offset_seconds * 1000)
    text = input_path.read_text(encoding="utf-8", errors="replace")

    def repl(match: re.Match[str]) -> str:
        original = match.group(0)
        comma = "," in original
        return _ms_to_timestamp(_timestamp_to_ms(match) + offset_ms, comma=comma)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(TIMESTAMP_RE.sub(repl, text), encoding="utf-8")
    return output_path


def sync_subtitle_to_video(
    video: str | Path,
    subtitle: str | Path,
    output: str | Path,
    *,
    offset_seconds: float = 0.0,
    max_duration_seconds: int | None = None,
) -> Path:
    """Synchronize a subtitle file to a video/audio reference using ffsubsync."""
    executable = find_ffsubsync()
    if not executable:
        raise FileNotFoundError("ffsubsync is not installed or not on PATH")
    cmd = build_ffsubsync_command(
        video,
        subtitle,
        output,
        offset_seconds=offset_seconds,
        max_duration_seconds=max_duration_seconds,
        executable=executable,
    )
    subprocess.run(cmd, check=True)
    return Path(output)


def prepare_subtitle_for_mux(
    video: str | Path,
    subtitle: str | Path,
    output: str | Path,
    *,
    sync: bool = True,
    offset_seconds: float = 0.0,
    max_duration_seconds: int | None = None,
) -> Path:
    """Return a subtitle path ready to mux, syncing or offset-shifting when requested."""
    if sync:
        return sync_subtitle_to_video(
            video,
            subtitle,
            output,
            offset_seconds=offset_seconds,
            max_duration_seconds=max_duration_seconds,
        )
    if offset_seconds:
        return shift_subtitle_file(subtitle, output, offset_seconds)
    return Path(subtitle)
