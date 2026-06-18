from streamgrabber.manifest import parse_master_playlist, choose_variant
from streamgrabber.downloader import build_ytdlp_command, build_streamlink_command
from streamgrabber.muxer import build_ffmpeg_mux_command


def test_parse_master_playlist_extracts_variants():
    text = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=760650,RESOLUTION=640x360
low/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2548703,RESOLUTION=1280x720
https://cdn.example/high/index.m3u8
"""
    variants = parse_master_playlist(text, "https://cdn.example/master.m3u8")
    assert [(v.height, v.resolution, v.bandwidth, v.url) for v in variants] == [
        (360, "640x360", 760650, "https://cdn.example/low/index.m3u8"),
        (720, "1280x720", 2548703, "https://cdn.example/high/index.m3u8"),
    ]


def test_choose_variant_best_or_requested_height():
    variants = parse_master_playlist(
        """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1,RESOLUTION=640x360
360.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2,RESOLUTION=1280x720
720.m3u8
""",
        "https://cdn.example/master.m3u8",
    )
    assert choose_variant(variants, "best").height == 720
    assert choose_variant(variants, "360").height == 360
    assert choose_variant(variants, "480").height == 360


def test_ytdlp_command_preserves_headers_and_merges_to_mkv():
    cmd = build_ytdlp_command(
        url="https://cdn.example/master.m3u8",
        output="out.mkv",
        user_agent="UA X",
        referer="https://site.example/",
    )
    joined = " ".join(cmd)
    assert cmd[0] == "yt-dlp"
    assert "--user-agent" in cmd
    assert "UA X" in cmd
    assert "--add-header" in cmd
    assert "Referer:https://site.example/" in cmd
    assert "--merge-output-format" in cmd
    assert "mkv" in cmd
    assert "https://cdn.example/master.m3u8" in joined


def test_streamlink_command_preserves_headers_and_duration():
    cmd = build_streamlink_command(
        url="https://cdn.example/master.m3u8",
        quality="720p",
        output="video.ts",
        user_agent="UA X",
        referer="https://site.example/",
        duration="00:00:10",
    )
    assert cmd == [
        "streamlink",
        "--http-header",
        "User-Agent=UA X",
        "--http-header",
        "Referer=https://site.example/",
        "--stream-segmented-duration",
        "00:00:10",
        "-o",
        "video.ts",
        "https://cdn.example/master.m3u8",
        "720p",
    ]


def test_ffmpeg_mux_embeds_webvtt_when_subtitle_exists():
    assert build_ffmpeg_mux_command("video.ts", "sub.vtt", "out.mkv") == [
        "ffmpeg",
        "-y",
        "-i",
        "video.ts",
        "-i",
        "sub.vtt",
        "-c",
        "copy",
        "-c:s",
        "webvtt",
        "out.mkv",
    ]
