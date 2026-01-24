#!/bin/bash
# Quick test script for Carleton Mediaspace download

URL="https://mediaspace.carleton.ca/media/L5+3000A/1_3e140s7n"

echo "Testing Mediaspace downloader with Carleton URL..."
echo "URL: $URL"
echo ""

python3 mediaspace_downloader.py "$URL" "L5_3000A_video.mp4"
