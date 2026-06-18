# streamgrabber

Give a page URL and let the tool capture HLS/VTT requests, choose a quality, download with preserved browser headers, and mux to MKV.

## Requirements

- Python 3.11+
- Playwright Chromium (`python -m playwright install chromium`)
- `streamlink`
- `yt-dlp` (optional downloader mode)
- `ffmpeg` / `ffprobe`

On this Mac these were installed and verified.

## Commands

List streams:

```bash
streamgrabber-py 'https://streamimdb.ru/embed/tv/tt3032476' --list
```

Download best quality:

```bash
streamgrabber-py 'https://streamimdb.ru/embed/tv/tt3032476' \
  --quality best \
  --output video.mkv
```

Download 720p:

```bash
streamgrabber-py 'https://streamimdb.ru/embed/tv/tt3032476' \
  --quality 720 \
  --output video.mkv
```

Print commands without downloading:

```bash
streamgrabber-py 'https://streamimdb.ru/embed/tv/tt3032476' --print-command
```

Short test download:

```bash
streamgrabber-py 'https://streamimdb.ru/embed/tv/tt3032476' \
  --quality 360 \
  --duration 00:00:10 \
  --output sample.mkv
```

## Behavior

- Uses Playwright to load the page and detect `.m3u8`, `.mpd`, `.vtt`, `.srt` network requests.
- Preserves captured `User-Agent` and `Referer`.
- Parses HLS master playlists and selects best or requested height.
- Uses `streamlink` by default; `--downloader yt-dlp` is available.
- Downloads subtitle files when detected and muxes them into MKV with `ffmpeg`.
- Starts headless; if headless detection is blocked, retries with an automated visible browser window unless `--no-fallback` is passed.

## Verified sample

The URL `https://streamimdb.ru/embed/tv/tt3032476` was verified:

- HLS master playlist captured
- Variants found: 360p and 720p
- Short 360p sample downloaded and muxed to `sample.mkv`
