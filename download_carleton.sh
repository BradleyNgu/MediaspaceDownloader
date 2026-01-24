#!/bin/bash
# Complete workflow script for downloading Carleton Mediaspace videos

URL="https://mediaspace.carleton.ca/media/L5+3000A/1_3e140s7n"
OUTPUT_FILE="L5_3000A_video.mp4"

echo "=========================================="
echo "Carleton Mediaspace Video Downloader"
echo "=========================================="
echo ""
echo "Step 1: Capturing M3U8 URL from network requests..."
echo ""

# Try to capture M3U8 URL automatically
python3 capture_m3u8.py "$URL" 2>/dev/null

if [ -f "captured_m3u8_url.txt" ]; then
    M3U8_URL=$(cat captured_m3u8_url.txt)
    echo ""
    echo "Step 2: Downloading video using captured M3U8 URL..."
    echo ""
    python3 mediaspace_downloader.py "$M3U8_URL" "$OUTPUT_FILE"
else
    echo ""
    echo "Automatic capture failed. Trying direct download..."
    echo "If this fails, manually capture the M3U8 URL:"
    echo "  1. Open the video page in browser"
    echo "  2. Open DevTools (F12) > Network tab"
    echo "  3. Filter by 'm3u8'"
    echo "  4. Start playing the video"
    echo "  5. Copy the .m3u8 URL and run:"
    echo "     python3 mediaspace_downloader.py <m3u8_url> $OUTPUT_FILE"
    echo ""
    python3 mediaspace_downloader.py "$URL" "$OUTPUT_FILE" --debug
fi
