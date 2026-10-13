from __future__ import annotations

import shutil
import sys


def get_install_instruction(binary: str, system: str | None = None) -> str:
    """Return platform-specific installation instruction for a binary."""
    plat = system or sys.platform
    is_win = plat.startswith("win")
    is_mac = plat == "darwin"

    if binary == "streamlink":
        if is_win:
            return "winget install Streamlink.Streamlink  (or: pip install streamlink)"
        elif is_mac:
            return "brew install streamlink"
        else:
            return "sudo apt install streamlink  (or: pip install streamlink)"
    elif binary in {"ffmpeg", "ffprobe"}:
        if is_win:
            return "winget install Gyan.FFmpeg  (or download from https://www.gyan.dev/ffmpeg/builds/)"
        elif is_mac:
            return "brew install ffmpeg"
        else:
            return "sudo apt install ffmpeg"
    elif binary == "yt-dlp":
        if is_win:
            return "winget install yt-dlp  (or: pip install yt-dlp)"
        elif is_mac:
            return "brew install yt-dlp"
        else:
            return "sudo apt install yt-dlp  (or: pip install yt-dlp)"
    elif binary == "ffsubsync":
        return "python -m pip install ffsubsync"
    elif binary in {"playwright", "playwright chromium"}:
        return "python -m playwright install chromium"
    return f"Install '{binary}' and ensure it is available in your PATH."


def get_platform_doctor_tip(system: str | None = None) -> str:
    """Return general doctor installation tip for the current platform."""
    plat = system or sys.platform
    if plat.startswith("win"):
        return (
            "install missing dependencies on Windows:\n"
            "  winget install Streamlink.Streamlink Gyan.FFmpeg yt-dlp\n"
            "  python -m pip install ffsubsync\n"
            "  python -m playwright install chromium"
        )
    elif plat == "darwin":
        return (
            "install missing dependencies on macOS:\n"
            "  brew install ffmpeg streamlink yt-dlp\n"
            "  python -m pip install ffsubsync\n"
            "  python -m playwright install chromium"
        )
    else:
        return (
            "install missing dependencies on Linux:\n"
            "  sudo apt install ffmpeg streamlink yt-dlp\n"
            "  python -m pip install ffsubsync\n"
            "  python -m playwright install chromium"
        )


class MissingDependencyError(FileNotFoundError):
    """Raised when an external tool or CLI executable is not found in PATH."""

    def __init__(self, binary: str, message: str | None = None):
        self.binary = binary
        install_cmd = get_install_instruction(binary)
        msg = message or (
            f"'{binary}' is required but was not found in your PATH.\n"
            f"To install:\n  {install_cmd}\n\n"
            f"Run 'streamgrabber doctor' to verify all requirements."
        )
        super().__init__(msg)


def ensure_binary_available(name: str) -> str:
    """Ensure a binary is available in PATH, or raise MissingDependencyError."""
    path = shutil.which(name)
    if not path:
        raise MissingDependencyError(name)
    return path
