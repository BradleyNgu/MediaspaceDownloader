# Mediaspace Video Downloader

A Python tool to download videos from Mediaspace by downloading and stitching together TS (Transport Stream) segments.

## How It Works

Mediaspace typically serves videos using HLS (HTTP Live Streaming), which breaks videos into small TS segments. This tool:

1. Finds or accepts the M3U8 playlist URL
2. Parses the playlist to get all TS segment URLs
3. Downloads all segments
4. Concatenates them together
5. Converts to MP4 format using ffmpeg

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop on Windows and macOS, or Docker Engine on Linux)
- [Docker Compose](https://docs.docker.com/compose/) v2 (included with Docker Desktop)

Python, ffmpeg, Playwright, and Python dependencies are installed **inside the image** when you build; you do not install them on the host.

## Build

Build the image from the repository root. This is the supported way to produce a runnable environment.

**Docker CLI:**

```bash
docker build -t mediaspace-downloader .
```

**Docker Compose (same build, uses `docker-compose.yml`):**

```bash
docker compose build
```

The Dockerfile installs ffmpeg, Python dependencies from `requirements.txt`, and Playwright Chromium with system dependencies.

## How to Run

Replace `mediaspace-downloader` with your image tag if you used a different name.

### Web app (Flask UI, default container command)

**Compose (builds if needed, maps port 5000, persists downloads in a named volume):**

```bash
docker compose up
```

Open `http://127.0.0.1:5000`.

**Plain Docker:**

```bash
docker run --rm -p 5000:5000 -v mediaspace_downloads:/app/downloads mediaspace-downloader
```

Some hosts set `PORT` at runtime; the image respects `PORT` and defaults to `5000`.

### CLI downloader

Mount a host directory into `/app/downloads` so MP4s appear on your machine.

**Linux / macOS (bash):**

```bash
mkdir -p downloads
docker run --rm -v "$(pwd)/downloads:/app/downloads" mediaspace-downloader \
  python mediaspace_downloader.py "https://mediaspace.example.com/video/12345"
```

**Windows (PowerShell):**

```powershell
New-Item -ItemType Directory -Force downloads | Out-Null
docker run --rm -v "${PWD}/downloads:/app/downloads" mediaspace-downloader `
  python mediaspace_downloader.py "https://mediaspace.example.com/video/12345"
```

Examples:

```bash
# Direct M3U8 URL
docker run --rm -v "$(pwd)/downloads:/app/downloads" mediaspace-downloader \
  python mediaspace_downloader.py "https://mediaspace.example.com/playlist.m3u8"

# Custom output filename
docker run --rm -v "$(pwd)/downloads:/app/downloads" mediaspace-downloader \
  python mediaspace_downloader.py "https://mediaspace.example.com/video/12345" my_video.mp4

# Debug
docker run --rm -v "$(pwd)/downloads:/app/downloads" mediaspace-downloader \
  python mediaspace_downloader.py "https://mediaspace.example.com/video/12345" --debug
```

### Browser M3U8 capture helper

The capture script is intended to drive a browser. Inside a typical Linux container there is no graphical display, so automatic capture may not work the same way as on a desktop. If it fails, use the manual DevTools method below and pass the copied M3U8 URL to the CLI.

```bash
docker run --rm -it mediaspace-downloader python capture_m3u8.py "https://mediaspace.example.com/..."
```

To save `captured_m3u8_url.txt` on the host, add a bind mount for `/app` or the working directory you use for output.

### Output

- With **bind mount** examples above, files land in `./downloads` on the host.
- With **`docker compose up`** as written, files go into the Compose `downloads` named volume. List it with `docker volume ls` and inspect the mountpoint with `docker volume inspect <volume_name>` (the name is prefixed with your project directory).

## How to Find M3U8 URLs

### Automatic method (browser capture)

Use the capture container command above when you have a suitable environment (for example, a local display or extra Docker setup for headed browsers). Otherwise prefer the manual method.

### Manual method

1. Open the Mediaspace video page in your browser
2. Open Developer Tools (F12 or Cmd+Option+I)
3. Go to the Network tab
4. Filter by "m3u8" or "media"
5. **Start playing the video** (this triggers the M3U8 request)
6. Look for requests ending in `.m3u8`
7. Right-click the request > Copy > Copy URL
8. Run the CLI with that URL (see **CLI downloader**), for example:

**Linux / macOS:**

```bash
docker run --rm -v "$(pwd)/downloads:/app/downloads" mediaspace-downloader \
  python mediaspace_downloader.py "<copied_m3u8_url>"
```

**Windows (PowerShell):**

```powershell
docker run --rm -v "${PWD}/downloads:/app/downloads" mediaspace-downloader `
  python mediaspace_downloader.py "<copied_m3u8_url>"
```

## Notes

- This is an experimental tool for educational purposes
- Make sure you have permission to download the content
- Some videos may be protected or require authentication
- The tool uses a temporary directory during download and cleans it up automatically

## Troubleshooting

**Rebuild after dependency changes:**

```bash
docker build --no-cache -t mediaspace-downloader .
```

**"ffmpeg not found" inside the container:**  
Rebuild the image; ffmpeg is installed in the Dockerfile.

**"No TS segments found":**

- The URL might not be a valid M3U8 playlist
- Try opening the M3U8 URL in a browser to verify it's accessible
- Some playlists may require authentication headers

**Download fails:**

- Check your internet connection
- Verify the URL is accessible
- Some servers may block automated downloads (try adding delays or using a VPN)
