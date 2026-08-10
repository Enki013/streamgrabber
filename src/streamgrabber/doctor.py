from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from urllib.parse import urlparse

from .subsync import find_ffsubsync


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    path: str | None = None
    version: str | None = None
    detail: str | None = None


def check_url_like(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_binary(name: str, version_args: list[str] | None = None) -> CheckResult:
    path = shutil.which(name)
    if not path:
        return CheckResult(name=name, ok=False, detail="not found in PATH")
    version = None
    if version_args is not None:
        try:
            proc = subprocess.run(
                [path, *version_args],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            version = (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr).strip() else None
        except Exception as exc:  # pragma: no cover - defensive only
            return CheckResult(name=name, ok=False, path=path, detail=str(exc))
    return CheckResult(name=name, ok=True, path=path, version=version)


def check_ffsubsync() -> CheckResult:
    path = find_ffsubsync()
    if not path:
        return CheckResult(name="ffsubsync", ok=False, detail="not found in PATH or active venv")
    try:
        proc = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr).strip() else None
        return CheckResult(name="ffsubsync", ok=True, path=path, version=version)
    except Exception as exc:  # pragma: no cover - defensive only
        return CheckResult(name="ffsubsync", ok=False, path=path, detail=str(exc))


def run_doctor_checks() -> list[CheckResult]:
    return [
        check_binary("ffmpeg", ["-version"]),
        check_binary("ffprobe", ["-version"]),
        check_binary("streamlink", ["--version"]),
        check_binary("yt-dlp", ["--version"]),
        check_ffsubsync(),
    ]
