#!/usr/bin/env python3
"""
Mediaspace Downloader — Web Frontend
Flask app wrapping the CLI downloader with real-time progress via SSE.
"""

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

from mediaspace_downloader import MediaspaceDownloader
from capture_m3u8 import capture_m3u8_url, PLAYWRIGHT_AVAILABLE, SELENIUM_AVAILABLE

app = Flask(__name__)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Active jobs: job_id -> {queue, status, filename, ...}
jobs: dict = {}


class ProgressDownloader(MediaspaceDownloader):
    """Subclass that pushes progress events into a queue."""

    def __init__(self, progress_queue: queue.Queue, output_dir: str = "downloads"):
        super().__init__(output_dir)
        self.q = progress_queue

    def _emit(self, event: str, data: dict):
        self.q.put({"event": event, "data": data})

    def download_segment(self, url, output_path, segment_num, total):
        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self._emit(
                "progress",
                {
                    "segment": segment_num,
                    "total": total,
                    "percent": round(segment_num / total * 100),
                    "message": f"Downloaded segment {segment_num}/{total}",
                },
            )
            return True
        except Exception as e:
            self._emit("error", {"message": f"Segment {segment_num} failed: {e}"})
            return False


def _run_download(job_id: str, url: str, filename: Optional[str]):
    """Background worker that drives the download and pushes SSE events."""
    q = jobs[job_id]["queue"]

    def emit(event, data):
        q.put({"event": event, "data": data})

    try:
        dl = ProgressDownloader(q)

        emit("status", {"message": "Resolving M3U8 playlist…", "phase": "resolve"})

        def browser_log(msg):
            emit("status", {"message": msg, "phase": "browser"})

        if url.endswith(".m3u8") or ".m3u8?" in url or "/a.m3u8" in url:
            m3u8_url = url
        else:
            # Try simple HTML scraping first (fast)
            m3u8_url = dl.get_m3u8_url(url, debug=False)

            # Fall back to browser automation (headless) with live status
            if not m3u8_url and (PLAYWRIGHT_AVAILABLE or SELENIUM_AVAILABLE):
                emit("status", {"message": "Launching headless browser to capture M3U8…", "phase": "browser"})
                m3u8_url = capture_m3u8_url(url, wait_time=20, headless=True,
                                            on_status=browser_log)

            if not m3u8_url:
                emit("error", {"message": "Could not find an M3U8 playlist for this URL."})
                return

        emit("status", {"message": "Parsing playlist…", "phase": "parse"})
        ts_urls = dl.parse_m3u8(m3u8_url)
        if not ts_urls:
            emit("error", {"message": "No video segments found in the playlist."})
            return

        emit(
            "status",
            {"message": f"Found {len(ts_urls)} segments. Downloading…", "phase": "download"},
        )

        tmp = Path(tempfile.mkdtemp(prefix="msdl_"))
        try:
            segment_files = dl.download_all_segments(ts_urls, tmp)

            if not filename:
                from urllib.parse import urlparse

                parts = [p for p in urlparse(url).path.split("/") if p]
                filename = (parts[-1] if parts else "video").replace("+", "_").replace(" ", "_")
            if not filename.endswith(".mp4"):
                filename += ".mp4"

            safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
            output_path = DOWNLOAD_DIR / safe_name

            emit("status", {"message": "Stitching segments with ffmpeg…", "phase": "stitch"})
            success = dl.concatenate_with_ffmpeg(segment_files, output_path)

            if not success:
                output_path = output_path.with_suffix(".ts")
                safe_name = output_path.name
                success = dl.concatenate_simple(segment_files, output_path)

            if success:
                jobs[job_id]["filename"] = safe_name
                emit(
                    "complete",
                    {"message": "Download complete!", "filename": safe_name},
                )
            else:
                emit("error", {"message": "Failed to stitch video segments."})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:
        emit("error", {"message": str(exc)})


# ── Routes ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def start_download():
    body = request.get_json(force=True)
    url = (body.get("url") or "").strip()
    filename = (body.get("filename") or "").strip() or None

    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = uuid.uuid4().hex
    jobs[job_id] = {"queue": queue.Queue(), "status": "running", "filename": None}

    t = threading.Thread(target=_run_download, args=(job_id, url, filename), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Unknown job"}), 404

    def stream():
        q = jobs[job_id]["queue"]
        while True:
            try:
                msg = q.get(timeout=60)
            except queue.Empty:
                yield "event: ping\ndata: {}\n\n"
                continue
            yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
            if msg["event"] in ("complete", "error"):
                break

    return Response(stream(), mimetype="text/event-stream")


@app.route("/api/file/<filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
