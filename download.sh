#!/bin/bash
# Mediaspace Video Downloader - Interactive Shell Script

echo "============================================================"
echo "Mediaspace Video Downloader"
echo "============================================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: ffmpeg is not installed or not in PATH"
    echo "The downloader requires ffmpeg to convert videos."
    echo "Install it with: brew install ffmpeg"
    echo ""
    read -p "Continue anyway? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[yY] ]]; then
        exit 1
    fi
fi

# Get URL from user
read -p "Enter Mediaspace URL or M3U8 link: " url
if [ -z "$url" ]; then
    echo "Error: URL cannot be empty"
    exit 1
fi

# Get optional output filename
read -p "Enter output filename (press Enter for auto-generated): " output_filename

# Get optional debug mode
read -p "Enable debug mode? (y/N): " debug_input
debug=""
if [[ "$debug_input" =~ ^[yY] ]]; then
    debug="--debug"
fi

echo ""
echo "Starting download..."
echo ""

# Run the downloader
if [ -z "$output_filename" ]; then
    python3 mediaspace_downloader.py "$url" $debug
else
    python3 mediaspace_downloader.py "$url" "$output_filename" $debug
fi

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✓ Download completed successfully!"
else
    echo ""
    echo "✗ Download failed!"
    exit $exit_code
fi
