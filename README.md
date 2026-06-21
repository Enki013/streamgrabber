# streamgrabber

`streamgrabber` is a CLI tool that takes a web/embed video URL, captures HLS/DASH/subtitle streams, downloads the selected quality with the right browser headers, and muxes the result to MKV.

It is designed for Stream Detector-style workflows where the page URL may stay the same while the player internally changes episodes/sources.

## Features

- Captures `.m3u8`, `.mpd`, `.vtt`, `.srt` requests from dynamic web/player pages.
- Preserves important request headers such as `User-Agent` and `Referer`.
- Uses `streamlink` by default for HLS downloads.
- Supports `yt-dlp` as an alternate downloader.
- Uses `ffmpeg` to mux output to `.mkv`.
- Automatically selects **best quality** if you do not pass `--quality`.
- Automatically generates the output filename if you do not pass `--output`.
- For supported TV players, can list/download a specific episode or an entire season.
- Handles fixed-URL players where episode changes happen through an internal API rather than the browser URL.
- Accepts direct StreamIMDB embeds, IMDb title URLs, or bare IMDb IDs such as `tt0096895`.
- Can search, download, convert, and mux matching subtitles such as Turkish (`--subtitle-lang tr`).

## Requirements

- Python 3.11+
- Playwright Chromium
- `streamlink`
- `yt-dlp` optional but recommended
- `ffmpeg` / `ffprobe`
- `ffsubsync` for automatic subtitle synchronization

Check the local setup:

```bash
streamgrabber doctor
```

Expected checks:

```text
ffmpeg              OK
ffprobe             OK
streamlink          OK
yt-dlp              OK
ffsubsync           OK
playwright chromium OK
```

If Playwright Chromium is missing:

```bash
cd streamgrabber
source .venv/bin/activate
python -m playwright install chromium
```

## Command name

Use the primary command:

```bash
streamgrabber
```

Installations from this repository expose `streamgrabber`. If your shell still runs an older Node prototype, remove or overwrite that old executable from your `PATH`.

## Basic usage

### Supported input forms

You can pass a direct embed URL:

```bash
streamgrabber 'https://streamimdb.ru/embed/movie/tt0096895'
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476'
```

You can also pass an IMDb title URL:

```bash
streamgrabber 'https://www.imdb.com/title/tt0096895'
```

Or just the IMDb ID:

```bash
streamgrabber tt0096895
```

For IMDb inputs, the tool resolves to the matching StreamIMDB embed automatically. For example:

```text
https://www.imdb.com/title/tt0096895
-> https://streamimdb.ru/embed/movie/tt0096895
```

### IMDb movie example

List streams for Batman 1989 from IMDb:

```bash
streamgrabber 'https://www.imdb.com/title/tt0096895' --list
```

Download it with defaults:

```bash
streamgrabber 'https://www.imdb.com/title/tt0096895'
```

Defaults still apply:

- quality: `best`
- output filename: automatic

Example automatic output:

```text
Batman 1989.mkv
```

### List detected streams

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --list
```

This prints the captured HLS URL, available quality variants, detected subtitles, source name, and planned output path.

### Download without specifying quality or filename

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476'
```

Defaults:

- quality: `best`
- output: automatically generated from the detected source/title
- container: `.mkv`

Example automatic output name:

```text
Better Call Saul 2015 1-1.mkv
```

For TV episode API mode, automatic names use clean season/episode format:

```text
Better Call Saul 2015 S01E02.mkv
```

### Download best quality explicitly

This is equivalent to omitting `--quality`:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --quality best
```

### Download a specific quality

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --quality 720
```

or:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --quality 360
```

### Manually choose output filename

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --quality 720 --output 'Better Call Saul S01E01.mkv'
```

Short options also work:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' -q 720 -o 'Better Call Saul S01E01.mkv'
```

### Short test download

Useful before downloading a full episode:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --quality 360 --duration 00:00:10 --output sample.mkv
```

### Print commands without downloading

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --print-command
```

or:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --commands
```

## TV season / episode mode

Some players keep the browser URL fixed while the user changes episode inside the player. For example:

```text
https://streamimdb.ru/embed/tv/tt3032476
```

The URL remains the same, but the player internally calls an API with `season` and `episode` parameters. `streamgrabber` supports this.

### List all available seasons and episodes

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --episodes
```

Example result:

```json
{
  "title": "Better Call Saul 2015",
  "episodes": {
    "1": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    "2": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    "6": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
  }
}
```

### List one season

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --list
```

Example:

```json
{
  "title": "Better Call Saul 2015",
  "season": 1,
  "episodes": [1,2,3,4,5,6,7,8,9,10]
}
```

### Download one episode

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --episode 2
```

Default output:

```text
Better Call Saul 2015 S01E02.mkv
```

### Download one episode with quality

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --episode 2 --quality 720
```

### Download an entire season

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes
```

Each episode download is retried on transient CDN/timeout failures. On retry, the tool asks the player API for a fresh signed stream URL before calling `streamlink` again.

Useful retry controls:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --download-retries 5
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --stop-on-error
```

By default, `--all-episodes` continues to the next episode after retries are exhausted and reports failed episode numbers at the end. Re-run the same command later to retry missing/failed files.

This downloads every episode in S01 sequentially, generating filenames like:

```text
Better Call Saul 2015 S01E01.mkv
Better Call Saul 2015 S01E02.mkv
Better Call Saul 2015 S01E03.mkv
...
Better Call Saul 2015 S01E10.mkv
```

### Download an entire season at 720p

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --quality 720
```

### Download an entire season with Turkish subtitles

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --quality 720 --subtitle-lang tr
```

For each episode, the tool checks player-provided default subtitles first. If none match the requested language, it searches OpenSubtitles, prefers subtitle releases that match the actual video release/source (for example `BluRay x264` over a high-download `WEBRip` subtitle), automatically syncs the subtitle to the downloaded video audio with `ffsubsync`, converts SRT to WebVTT when needed, and muxes it into the MKV.

### Download an entire season into a directory

```bash
mkdir -p downloads/better-call-saul-s01

streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --all-episodes --quality best --output downloads/better-call-saul-s01
```

When `--output` is a directory path in season mode, every episode is saved there with an automatic filename.

## Subtitles

Use `--subtitle-lang` / `--sub-lang` to download and mux a matching subtitle.

Turkish movie example:

```bash
streamgrabber 'https://www.imdb.com/title/tt0096895' --subtitle-lang tr
```

Turkish TV episode example:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --episode 2 --subtitle-lang tr
```

Subtitle sync is enabled by default. Useful controls:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --episode 2 --subtitle-lang tr --no-sync-subtitles
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --season 1 --episode 2 --subtitle-lang tr --subtitle-offset -1.5
```

- `--no-sync-subtitles` disables `ffsubsync` and muxes the selected subtitle as-is.
- `--subtitle-offset SECONDS` applies an extra fixed offset; negative values make subtitles earlier, positive values make them later.
- `--subtitle-sync-max-duration SECONDS` limits ffsubsync analysis for short tests/debugging.

Accepted Turkish values:

```text
tr
tur
turkish
türkçe
```

How subtitle matching works:

1. Extracts the IMDb ID from the input.
2. Fetches the StreamIMDB/VaPlayer metadata for the selected movie or episode.
3. Reads the actual upstream video release filename from `data.file_name`.
4. Checks `default_subs` from the player API first and uses the requested language if available.
5. If there is no matching default subtitle, searches the OpenSubtitles REST endpoint.
6. For TV episodes, searches with `season` and `episode`.
7. Scores candidates against the video release name, prioritizing sync-critical signals:
   - source/release type: `BluRay`, `WEBRip`, `WEB-DL`, `HDTV`
   - season/episode: `S01E02`
   - codec: `x264`, `x265`
   - resolution: `1080p`, `720p`
   - title/year/release-group matches
8. Uses download count only as a small tiebreaker/fallback, not as the main selector.
9. Downloads the selected subtitle (`.gz` from OpenSubtitles when needed).
10. Decodes the subtitle with the advertised encoding, e.g. `UTF-8` or `CP1254` for Turkish.
11. Converts SRT to WebVTT.
12. Runs `ffsubsync` against the downloaded video/audio to correct fixed offsets and framerate drift.
13. Applies any extra `--subtitle-offset` requested by the user.
14. Muxes the synced subtitle into the final `.mkv` as a subtitle stream.

Verify subtitle muxing with:

```bash
ffprobe -v error -select_streams s -show_entries stream=index,codec_name,codec_type -of json 'output.mkv'
```

Expected subtitle stream:

```json
{
  "codec_name": "webvtt",
  "codec_type": "subtitle"
}
```

## Downloader options

Default downloader:

```text
streamlink
```

Use `yt-dlp` instead:

```bash
streamgrabber 'https://streamimdb.ru/embed/tv/tt3032476' --downloader yt-dlp --output video.mkv
```

For most captured HLS streams, `streamlink` is the recommended default.

## Browser behavior

The tool starts with a headless Playwright browser.

If headless mode does not capture a stream, it automatically retries with an automated visible browser window.

Disable the fallback:

```bash
streamgrabber 'URL' --no-fallback
```

Force visible browser mode:

```bash
streamgrabber 'URL' --headed --list
```

## Output naming

If you do not pass `--output`, `streamgrabber` tries to generate a useful `.mkv` filename automatically.

Normal capture mode:

1. Finds the iframe/frame that emitted the HLS/DASH request.
2. Reads visible source/player text from that frame.
3. Filters noise like `Player`, `S01`, `E01`, `S01E01`, timestamps, ad labels, and control labels.
4. Uses the best source name it finds.
5. Falls back to useful title text if needed.

TV episode API mode:

- Uses the show title from the API.
- Adds `SxxExx` automatically.

Example:

```text
Better Call Saul 2015 S01E02.mkv
```

## Verified sample

The URL below was verified during development:

```text
https://streamimdb.ru/embed/tv/tt3032476
```

Verified behavior:

- HLS master playlist captured
- Variants found: 360p and 720p
- Best quality is selected by default
- S01 episode list detected
- S01E02 short sample downloaded and muxed
- Turkish subtitle search/download/mux verified with `--subtitle-lang tr`
- Subtitle release matching verified: BluRay video prefers BluRay subtitle over high-download WEBRip/NF subtitle
- Automatic subtitle sync path verified with `ffsubsync`
- `ffprobe` confirmed video/audio/subtitle streams

Sample `ffprobe` result from a short S01E02 test:

```text
Video: 640x360
Audio: AAC
Subtitle: WebVTT
Duration: ~5s
Container: MKV
```

## Development

Run tests:

```bash
cd streamgrabber
source .venv/bin/activate
pytest -q
```

Expected at the time of writing:

```text
39 passed
```

## Notes

- Signed `.m3u8` URLs can expire, so the tool fetches fresh episode stream URLs immediately before downloading.
- DRM-protected streams are not supported.
- Use this tool only for content you are authorized to access and download.
