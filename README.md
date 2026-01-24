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

- Python 3.7+
- ffmpeg (for video conversion)

### Installing ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
```bash
choco install ffmpeg
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install browser for Playwright (for automatic M3U8 capture):
```bash
playwright install chromium
```

Note: If you only want to use direct M3U8 URLs, you can skip the Playwright installation.

## Usage

### Basic Usage

```bash
python mediaspace_downloader.py <URL>
```

Where `<URL>` can be:
- A Mediaspace page URL (the tool will automatically find the M3U8 playlist)
- A direct M3U8 playlist URL

### Examples

```bash
# Download from Mediaspace page
python mediaspace_downloader.py https://mediaspace.example.com/video/12345

# Download from M3U8 URL directly
python mediaspace_downloader.py https://mediaspace.example.com/playlist.m3u8

# Specify output filename
python mediaspace_downloader.py https://mediaspace.example.com/video/12345 my_video.mp4

# Enable debug mode for troubleshooting
python mediaspace_downloader.py https://mediaspace.example.com/video/12345 --debug
```

### Output

Downloaded videos are saved in the `downloads/` directory by default.

## How to Find M3U8 URLs

### Automatic Method (Recommended)

If the M3U8 URL is loaded dynamically when the video starts playing, use the browser capture tool:

```bash
# Install browser automation dependencies (first time only)
pip install playwright selenium
playwright install chromium  # Install browser for Playwright

# Capture M3U8 URL automatically
python capture_m3u8.py https://mediaspace.REST_OF_URL...
```

This will:
1. Open the page in a browser
2. Try to start video playback
3. Capture M3U8 URLs from network requests
4. Save the URL for use with the downloader

### Manual Method

If automatic capture doesn't work:

1. Open the Mediaspace video page in your browser
2. Open Developer Tools (F12 or Cmd+Option+I)
3. Go to the Network tab
4. Filter by "m3u8" or "media"
5. **Start playing the video** (this triggers the M3U8 request)
6. Look for requests ending in `.m3u8`
7. Right-click the request > Copy > Copy URL
8. Use that URL with the downloader:
   ```bash
   python mediaspace_downloader.py <copied_m3u8_url>
   ```

## Notes

- This is an experimental tool for educational purposes
- Make sure you have permission to download the content
- Some videos may be protected or require authentication
- The tool uses a temporary directory during download and cleans it up automatically

## Troubleshooting

**"ffmpeg not found" error:**
- Install ffmpeg using the instructions above

**"No TS segments found":**
- The URL might not be a valid M3U8 playlist
- Try opening the M3U8 URL in a browser to verify it's accessible
- Some playlists may require authentication headers

**Download fails:**
- Check your internet connection
- Verify the URL is accessible
- Some servers may block automated downloads (try adding delays or using a VPN)
