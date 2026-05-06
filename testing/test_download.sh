#!/bin/bash
# Quick test script for Mediaspace downloader
set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ $# -lt 1 ]; then
    echo "Usage: ./test_download.sh <MEDIASPACE_OR_M3U8_URL> [OUTPUT_FILE]"
    echo "Example: ./test_download.sh \"https://mediaspace.example.edu/media/abc123\" \"lecture.mp4\""
    exit 1
fi

URL="$1"
OUTPUT_FILE="${2:-test_output.mp4}"

echo "Testing Mediaspace downloader..."
echo "URL: $URL"
echo "Output: $OUTPUT_FILE"
echo ""

"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" mediaspace_downloader.py "$URL" "$OUTPUT_FILE" --debug
