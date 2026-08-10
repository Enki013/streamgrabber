from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

import typer
from rich.console import Console
from rich.table import Table

from .detector import capture_streams
from .doctor import check_url_like, run_doctor_checks
from .downloader import build_streamlink_command, build_ytdlp_command, ensure_parent, run_command, run_command_with_retries
from .manifest import choose_variant, parse_master_playlist
from .models import Capture, DEFAULT_USER_AGENT
from .muxer import mux
from .naming import output_path_from_title
from .resolver import normalize_input_url
from .subtitles import (
    choose_best_subtitle,
    choose_default_subtitle,
    download_default_subtitle_as_vtt,
    download_subtitle_as_vtt,
    language_to_opensubtitles_id,
    search_subtitles,
)
from .subsync import prepare_subtitle_for_mux
from .vaplayer import episode_info, episode_output_name, episodes_for_season, movie_output_name, parse_media_id_from_url

app = typer.Typer(help="Capture web streams and download them with preserved browser headers.")
console = Console()


def fetch_text(url: str, *, user_agent: str, referer: str | None) -> str:
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", "replace")


def fetch_file(url: str, output: Path, *, user_agent: str, referer: str | None) -> None:
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer
    req = Request(url, headers=headers)
    with urlopen(req, timeout=60) as res:
        output.write_bytes(res.read())


def quality_for_streamlink(requested: str, selected_height: int | None) -> str:
    if requested in ("best", "auto", ""):
        return "best"
    if requested == "worst":
        return "worst"
    if selected_height:
        return f"{selected_height}p"
    return requested


def select_hls(captures: list[Capture]) -> Capture | None:
    return next((c for c in captures if c.kind == "hls"), None)


def print_summary(summary: dict) -> None:
    console.print_json(json.dumps(summary, ensure_ascii=False))


@app.command()
def main(
    url: str = typer.Argument(..., help="Page URL to inspect"),
    list_only: bool = typer.Option(False, "--list", help="List detected streams and exit"),
    print_command: bool = typer.Option(False, "--print-command", "--commands", help="Print download/mux commands and exit"),
    quality: str = typer.Option("best", "--quality", "-q", help="best, worst, 720, 360, etc."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output MKV path"),
    downloader: str = typer.Option("streamlink", "--downloader", help="streamlink or yt-dlp"),
    duration: str | None = typer.Option(None, "--duration", help="Limit segmented download duration, e.g. 00:00:30"),
    headed: bool = typer.Option(False, "--headed", help="Show browser window instead of headless"),
    no_fallback: bool = typer.Option(False, "--no-fallback", help="Do not retry with a visible automated browser if headless capture is blocked"),
    episodes: bool = typer.Option(False, "--episodes", help="List available seasons/episodes when supported"),
    season: int | None = typer.Option(None, "--season", help="TV season number for supported players"),
    episode: int | None = typer.Option(None, "--episode", help="TV episode number for supported players"),
    all_episodes: bool = typer.Option(False, "--all-episodes", help="Download all episodes in --season when supported"),
    subtitle_lang: str | None = typer.Option(None, "--subtitle-lang", "--sub-lang", help="Download and mux best matching subtitle language, e.g. tr/tur/turkish"),
    sync_subtitles: bool = typer.Option(True, "--sync-subtitles/--no-sync-subtitles", help="Auto-sync downloaded subtitles to the video audio with ffsubsync"),
    subtitle_offset: float = typer.Option(0.0, "--subtitle-offset", help="Apply an extra fixed subtitle offset in seconds after/while syncing; negative = earlier"),
    subtitle_sync_max_duration: int | None = typer.Option(None, "--subtitle-sync-max-duration", help="Limit ffsubsync analysis duration in seconds for faster tests"),
    download_retries: int = typer.Option(3, "--download-retries", min=1, help="Retry each episode download on transient stream/CDN failures"),
    stop_on_error: bool = typer.Option(False, "--stop-on-error/--continue-on-error", help="In --all-episodes mode, stop immediately when an episode fails"),
    timeout: int = typer.Option(15000, "--timeout", help="Capture timeout in ms"),
) -> None:
    """Give a page URL; automatically capture HLS/VTT, select quality, download, and mux."""
    if url == "doctor":
        run_doctor()
        return
    original_url = url
    try:
        url = normalize_input_url(url)
    except Exception as exc:
        console.print(f"[red]Could not resolve input URL:[/red] {original_url}")
        console.print(str(exc))
        raise typer.Exit(1)
    if not check_url_like(url):
        console.print(f"[red]Invalid URL:[/red] {url}")
        console.print("Usage examples:")
        console.print("  streamgrabber 'https://example.com/embed/video'")
        console.print("  streamgrabber 'https://www.imdb.com/title/tt0096895'")
        console.print("  streamgrabber tt0096895")
        console.print("  streamgrabber doctor")
        raise typer.Exit(2)
    if url != original_url:
        console.print(f"[cyan]Resolved:[/cyan] {original_url} -> {url}")
    if episodes or season is not None or episode is not None or all_episodes or "/embed/movie/" in url:
        run_vaplayer_mode(url, episodes, season, episode, all_episodes, quality, output, duration, print_command, list_only, subtitle_lang, sync_subtitles, subtitle_offset, subtitle_sync_max_duration, download_retries, stop_on_error)
        return
    asyncio.run(_main(url, list_only, print_command, quality, output, downloader, duration, headed, no_fallback, timeout))


def run_vaplayer_mode(
    url: str,
    episodes: bool,
    season: int | None,
    episode: int | None,
    all_episodes: bool,
    quality: str,
    output: Path | None,
    duration: str | None,
    print_command: bool,
    list_only: bool,
    subtitle_lang: str | None,
    sync_subtitles: bool,
    subtitle_offset: float,
    subtitle_sync_max_duration: int | None,
    download_retries: int,
    stop_on_error: bool,
) -> None:
    media_type, media_id = parse_media_id_from_url(url)
    base = episode_info(media_id, media_type)
    if episodes:
        print_summary({"media_id": media_id, "media_type": media_type, "title": base.title, "episodes": base.eps})
        return

    if media_type == "movie":
        out = output or Path.cwd() / movie_output_name(base.title, base.file_name)
        if list_only:
            print_summary({
                "title": base.title,
                "media_id": media_id,
                "media_type": media_type,
                "stream_urls": base.stream_urls,
                "output": str(out),
            })
            return
        download_episode_stream(base.stream_urls[0], out, quality, duration, print_command, subtitle_lang=subtitle_lang, imdb_id=media_id, media_type=media_type, title=base.title, file_name=base.file_name, default_subs=base.default_subs, sync_subtitles=sync_subtitles, subtitle_offset=subtitle_offset, subtitle_sync_max_duration=subtitle_sync_max_duration, download_retries=download_retries)
        return

    if media_type != "tv":
        console.print("[red]Season/episode options require a TV embed URL.[/red]")
        raise typer.Exit(2)

    if all_episodes:
        if season is None:
            console.print("[red]--all-episodes requires --season N[/red]")
            raise typer.Exit(2)
        eps = episodes_for_season(base, season)
        if list_only:
            print_summary({"title": base.title, "season": season, "episodes": eps})
            return
        target_dir = output if output and output.suffix == "" else Path.cwd()
        failures: list[tuple[int, str]] = []
        for ep in eps:
            info = episode_info(media_id, media_type, season, ep)
            out = target_dir / episode_output_name(info.title, season, ep, info.file_name)
            try:
                download_episode_stream(
                    info.stream_urls[0],
                    out,
                    quality,
                    duration,
                    print_command,
                    subtitle_lang=subtitle_lang,
                    imdb_id=media_id,
                    media_type=media_type,
                    season=season,
                    episode=ep,
                    title=info.title,
                    file_name=info.file_name,
                    default_subs=info.default_subs,
                    sync_subtitles=sync_subtitles,
                    subtitle_offset=subtitle_offset,
                    subtitle_sync_max_duration=subtitle_sync_max_duration,
                    download_retries=download_retries,
                    stream_url_refresh=lambda ep=ep: episode_info(media_id, media_type, season, ep).stream_urls[0],
                )
            except Exception as exc:
                failures.append((ep, str(exc)))
                console.print(f"[red]Episode S{season:02d}E{ep:02d} failed after retries:[/red] {exc}")
                if stop_on_error:
                    raise typer.Exit(1)
                console.print("[yellow]Continuing with next episode. Re-run the same command later to retry failed/missing episodes.[/yellow]")
        if failures:
            console.print(f"[yellow]Season completed with {len(failures)} failed episode(s):[/yellow] " + ", ".join(f"E{ep:02d}" for ep, _ in failures))
            raise typer.Exit(1)
        return

    if season is None or episode is None:
        console.print("[red]Use --episodes, or provide both --season N --episode N.[/red]")
        raise typer.Exit(2)
    info = episode_info(media_id, media_type, season, episode)
    out = output or Path.cwd() / episode_output_name(info.title, season, episode, info.file_name)
    if list_only:
        print_summary({
            "title": info.title,
            "season": season,
            "episode": episode,
            "stream_urls": info.stream_urls,
            "output": str(out),
        })
        return
    download_episode_stream(info.stream_urls[0], out, quality, duration, print_command, subtitle_lang=subtitle_lang, imdb_id=media_id, media_type=media_type, season=season, episode=episode, title=info.title, file_name=info.file_name, default_subs=info.default_subs, sync_subtitles=sync_subtitles, subtitle_offset=subtitle_offset, subtitle_sync_max_duration=subtitle_sync_max_duration, download_retries=download_retries, stream_url_refresh=lambda: episode_info(media_id, media_type, season, episode).stream_urls[0])


def download_episode_stream(
    url: str,
    output: Path,
    quality: str,
    duration: str | None,
    print_command: bool,
    *,
    subtitle_lang: str | None = None,
    imdb_id: str | None = None,
    media_type: str | None = None,
    season: int | None = None,
    episode: int | None = None,
    title: str = "",
    file_name: str = "",
    default_subs: list[dict] | None = None,
    sync_subtitles: bool = True,
    subtitle_offset: float = 0.0,
    subtitle_sync_max_duration: int | None = None,
    download_retries: int = 3,
    stream_url_refresh: Callable[[], str] | None = None,
) -> None:
    with tempfile.TemporaryDirectory(prefix="streamgrabber-") as tmp:
        video_ts = Path(tmp) / "video.ts"
        subtitle_vtt = Path(tmp) / "subtitle.vtt"
        synced_subtitle_vtt = Path(tmp) / "subtitle.synced.vtt"
        streamlink_quality = "best" if quality in ("best", "auto", "") else ("worst" if quality == "worst" else f"{quality.rstrip('p')}p")
        current_url = url

        def make_streamlink_command(attempt: int) -> list[str]:
            nonlocal current_url
            if attempt > 1 and stream_url_refresh:
                current_url = stream_url_refresh()
            return build_streamlink_command(
                url=current_url,
                quality=streamlink_quality,
                output=str(video_ts),
                user_agent=DEFAULT_USER_AGENT,
                referer="https://nextgencloudfabric.com/",
                duration=duration,
            )

        sl_cmd = make_streamlink_command(1)
        if print_command:
            console.print(" ".join(shlex_quote(x) for x in sl_cmd))
            if subtitle_lang and imdb_id:
                console.print(f"# subtitle search: imdb={imdb_id} lang={language_to_opensubtitles_id(subtitle_lang)} season={season or ''} episode={episode or ''}")
                console.print(" ".join(shlex_quote(x) for x in ["ffmpeg", "-y", "-i", str(video_ts), "-i", str(subtitle_vtt), "-c", "copy", "-c:s", "webvtt", str(output)]))
            else:
                console.print(" ".join(shlex_quote(x) for x in ["ffmpeg", "-y", "-i", str(video_ts), "-c", "copy", str(output)]))
            return
        ensure_parent(output)
        console.print(f"[green]Downloading {streamlink_quality}[/green] -> {output.name}")

        def before_retry(attempt: int, exc: BaseException) -> None:
            if video_ts.exists():
                video_ts.unlink()
            console.print(f"[yellow]Download failed on attempt {attempt}/{download_retries}; retrying with a fresh stream URL...[/yellow]")

        run_command_with_retries(
            make_streamlink_command,
            attempts=download_retries,
            retry_delay_seconds=2,
            before_retry=before_retry,
        )
        subtitle_path: Path | None = None
        if subtitle_lang and imdb_id:
            default_sub = choose_default_subtitle(default_subs or [], subtitle_lang)
            if default_sub:
                console.print(f"[green]Downloading default subtitle[/green] {default_sub.get('lang') or default_sub.get('code')}")
                subtitle_path = download_default_subtitle_as_vtt(default_sub, subtitle_vtt)
            else:
                console.print(f"[green]Searching subtitles[/green] lang={language_to_opensubtitles_id(subtitle_lang)}")
                candidates = search_subtitles(
                    imdb_id,
                    subtitle_lang,
                    season=season if media_type == "tv" else None,
                    episode=episode if media_type == "tv" else None,
                )
                selected = choose_best_subtitle(
                    candidates,
                    title=title,
                    file_name=file_name,
                    season=season if media_type == "tv" else None,
                    episode=episode if media_type == "tv" else None,
                )
                if selected:
                    console.print(f"[green]Downloading subtitle[/green] {selected.get('SubFileName') or selected.get('MovieReleaseName')}")
                    subtitle_path = download_subtitle_as_vtt(selected, subtitle_vtt)
                else:
                    console.print(f"[yellow]No subtitle found for language:[/yellow] {subtitle_lang}")
            if subtitle_path:
                try:
                    if sync_subtitles:
                        console.print("[green]Syncing subtitles[/green] with video audio via ffsubsync")
                    elif subtitle_offset:
                        console.print(f"[green]Applying subtitle offset[/green] {subtitle_offset:+.3f}s")
                    subtitle_path = prepare_subtitle_for_mux(
                        video_ts,
                        subtitle_path,
                        synced_subtitle_vtt,
                        sync=sync_subtitles,
                        offset_seconds=subtitle_offset,
                        max_duration_seconds=subtitle_sync_max_duration,
                    )
                except Exception as exc:
                    console.print(f"[yellow]Subtitle sync failed; using unsynced subtitle:[/yellow] {exc}")
        mux(str(video_ts), str(subtitle_path) if subtitle_path else None, str(output))
        console.print(f"[bold green]Saved:[/bold green] {output}")


def run_doctor() -> None:
    table = Table(title="streamgrabber doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Path / Version")
    ok = True

    for result in run_doctor_checks():
        ok = ok and result.ok
        status = "[green]OK[/green]" if result.ok else "[red]MISSING[/red]"
        detail = result.path or result.detail or ""
        if result.version:
            detail = f"{detail}\n{result.version}"
        table.add_row(result.name, status, detail)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        table.add_row("playwright chromium", "[green]OK[/green]", "launch succeeded")
    except Exception as exc:
        ok = False
        table.add_row("playwright chromium", "[red]MISSING/ERROR[/red]", str(exc).splitlines()[0])

    console.print(table)
    if not ok:
        console.print(
            "[yellow]Tip:[/yellow] install missing dependencies, e.g. "
            "`brew install ffmpeg streamlink yt-dlp`, "
            "`python -m pip install ffsubsync`, and "
            "`python -m playwright install chromium`."
        )
        raise typer.Exit(1)


async def _main(
    url: str,
    list_only: bool,
    print_command: bool,
    quality: str,
    output: Path | None,
    downloader: str,
    duration: str | None,
    headed: bool,
    no_fallback: bool,
    timeout: int,
) -> None:
    console.print("[cyan]Capturing stream URLs with Playwright...[/cyan]")
    captures = await capture_streams(url, timeout_ms=timeout, headless=not headed, user_agent=DEFAULT_USER_AGENT)
    hls = select_hls(captures)
    if not hls and not headed and not no_fallback:
        console.print("[yellow]Headless capture did not find a stream; retrying with an automated browser window...[/yellow]")
        captures = await capture_streams(url, timeout_ms=timeout, headless=False, user_agent=DEFAULT_USER_AGENT)
        hls = select_hls(captures)
    if not hls:
        console.print("[red]No HLS/m3u8 stream captured.[/red]")
        raise typer.Exit(1)

    user_agent = hls.user_agent
    referer = hls.referer
    manifest_text = fetch_text(hls.url, user_agent=user_agent, referer=referer)
    variants = parse_master_playlist(manifest_text, hls.url)
    selected = choose_variant(variants, quality)
    subtitles = [c for c in captures if c.kind in {"vtt", "srt"}]
    subtitle = subtitles[0] if subtitles else None
    page_title = hls.page_title or ""
    out = output or output_path_from_title(page_title, Path.cwd())

    summary = {
        "page_url": url,
        "hls": hls.url,
        "referer": referer,
        "user_agent": user_agent,
        "variants": [v.__dict__ for v in variants],
        "selected": selected.__dict__ if selected else None,
        "subtitles": [s.url for s in subtitles],
        "page_title": page_title,
        "output": str(out),
    }

    if list_only:
        print_summary(summary)
        return

    streamlink_quality = quality_for_streamlink(quality, selected.height if selected else None)
    if downloader == "yt-dlp":
        cmd = build_ytdlp_command(url=hls.url, output=str(out), user_agent=user_agent, referer=referer)
        if print_command:
            console.print(" ".join(shlex_quote(x) for x in cmd))
            return
        ensure_parent(out)
        run_command(cmd)
        return

    with tempfile.TemporaryDirectory(prefix="streamgrabber-") as tmp:
        tmpdir = Path(tmp)
        video_ts = tmpdir / "video.ts"
        sub_path = tmpdir / ("subtitle.vtt" if subtitle and subtitle.kind == "vtt" else "subtitle.srt") if subtitle else None
        sl_cmd = build_streamlink_command(
            url=hls.url,
            quality=streamlink_quality,
            output=str(video_ts),
            user_agent=user_agent,
            referer=referer,
            duration=duration,
        )
        if print_command:
            console.print(" ".join(shlex_quote(x) for x in sl_cmd))
            if subtitle:
                console.print(f"# subtitle: {subtitle.url}")
            console.print(" ".join(shlex_quote(x) for x in ["ffmpeg", "-y", "-i", str(video_ts), "...", str(out)]))
            return
        ensure_parent(out)
        console.print(f"[green]Downloading {streamlink_quality} with streamlink[/green]")
        run_command(sl_cmd)
        if subtitle and sub_path:
            console.print("[green]Downloading subtitle[/green]")
            fetch_file(subtitle.url, sub_path, user_agent=user_agent, referer=subtitle.referer or referer)
        console.print("[green]Muxing MKV with ffmpeg[/green]")
        mux(str(video_ts), str(sub_path) if sub_path else None, str(out))
        console.print(f"[bold green]Saved:[/bold green] {out}")


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


if __name__ == "__main__":
    app()
