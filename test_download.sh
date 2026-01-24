#!/bin/bash
# Quick test script for Carleton Mediaspace download

URL="YOUR_URL_HERE"

echo "Testing Mediaspace downloader with URL..."
echo "URL: $URL"
echo ""

python3 mediaspace_downloader.py "$URL" "YOUR_FILENAME.mp4"
