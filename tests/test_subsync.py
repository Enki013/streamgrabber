from pathlib import Path

from streamgrabber.subsync import build_ffsubsync_command, shift_subtitle_file


def test_build_ffsubsync_command_includes_quality_guard_offset_and_duration():
    cmd = build_ffsubsync_command(
        "video.ts",
        "subtitle.vtt",
        "subtitle.synced.vtt",
        offset_seconds=-1.25,
        max_duration_seconds=120,
    )
    assert cmd == [
        "ffsubsync",
        "video.ts",
        "-i",
        "subtitle.vtt",
        "-o",
        "subtitle.synced.vtt",
        "--skip-sync-on-low-quality",
        "--apply-offset-seconds",
        "-1.25",
        "--max-duration-seconds",
        "120",
    ]


def test_shift_subtitle_file_moves_vtt_timestamps(tmp_path: Path):
    source = tmp_path / "in.vtt"
    target = tmp_path / "out.vtt"
    source.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nMerhaba\n",
        encoding="utf-8",
    )

    shift_subtitle_file(source, target, 1.5)

    assert "00:00:02.500 --> 00:00:04.000" in target.read_text(encoding="utf-8")


def test_shift_subtitle_file_clamps_negative_timestamps(tmp_path: Path):
    source = tmp_path / "in.srt"
    target = tmp_path / "out.srt"
    source.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nMerhaba\n",
        encoding="utf-8",
    )

    shift_subtitle_file(source, target, -2.0)

    assert "00:00:00,000 --> 00:00:00,000" in target.read_text(encoding="utf-8")
