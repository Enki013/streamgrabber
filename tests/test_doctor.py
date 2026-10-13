import pytest

from streamgrabber.doctor import (
    MissingDependencyError,
    check_binary,
    check_url_like,
    ensure_binary_available,
    get_install_instruction,
    get_platform_doctor_tip,
)


def test_check_url_like_accepts_http_urls():
    assert check_url_like("https://example.com/video") is True
    assert check_url_like("http://example.com/video") is True


def test_check_url_like_rejects_doctor_command_word():
    assert check_url_like("doctor") is False


def test_check_binary_reports_missing_binary():
    result = check_binary("definitely-not-a-real-streamgrabber-binary")
    assert result.name == "definitely-not-a-real-streamgrabber-binary"
    assert result.ok is False
    assert result.path is None


def test_get_install_instruction_windows():
    assert "winget" in get_install_instruction("streamlink", system="win32")
    assert "winget" in get_install_instruction("ffmpeg", system="win32")
    assert "winget" in get_install_instruction("yt-dlp", system="win32")


def test_get_install_instruction_darwin():
    assert "brew install streamlink" in get_install_instruction("streamlink", system="darwin")
    assert "brew install ffmpeg" in get_install_instruction("ffmpeg", system="darwin")


def test_get_platform_doctor_tip():
    assert "winget" in get_platform_doctor_tip("win32")
    assert "brew" in get_platform_doctor_tip("darwin")
    assert "apt" in get_platform_doctor_tip("linux")


def test_ensure_binary_available_raises_missing_dependency_error():
    with pytest.raises(MissingDependencyError) as exc_info:
        ensure_binary_available("nonexistent_binary_xyz_123")
    assert "nonexistent_binary_xyz_123" in str(exc_info.value)
    assert issubclass(MissingDependencyError, FileNotFoundError)
