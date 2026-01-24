#!/usr/bin/env python3
"""
Mediaspace Video Downloader
Downloads TS segments from Mediaspace and converts them to MP4
"""

import os
import sys
import re
import requests
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Optional
import tempfile
import shutil


class MediaspaceDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_m3u8_url(self, url: str, debug: bool = False) -> Optional[str]:
        """Extract M3U8 playlist URL from Mediaspace page"""
        try:
            if debug:
                print(f"Fetching page: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            if debug:
                print(f"Page loaded, size: {len(response.text)} bytes")
            
            # Look for M3U8 URLs in the page (various patterns)
            m3u8_patterns = [
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
                r'(https?://[^\s<>"]+\.m3u8[^\s<>"]*)',
                r'url["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    if debug:
                        print(f"Found {len(matches)} M3U8 URL(s) with pattern")
                    # Prefer URLs that look like actual playlists
                    for match in matches:
                        if 'playlist' in match.lower() or 'index' in match.lower():
                            if debug:
                                print(f"Selected playlist URL: {match}")
                            return match
                    if debug:
                        print(f"Selected first M3U8 URL: {matches[0]}")
                    return matches[0]
            
            # Check for video source tags
            video_src_pattern = r'<source[^>]+src=["\']([^"\']+)["\']'
            matches = re.findall(video_src_pattern, response.text, re.IGNORECASE)
            for match in matches:
                if '.m3u8' in match:
                    if debug:
                        print(f"Found M3U8 in video source: {match}")
                    return urljoin(url, match)
            
            # Try to find Kaltura entry ID and construct API URL
            if debug:
                print("Trying to extract Kaltura entry ID...")
            entry_id = self._extract_kaltura_entry_id(response.text, url)
            if entry_id:
                if debug:
                    print(f"Found entry ID: {entry_id}")
                m3u8_url = self._try_kaltura_api(entry_id, url)
                if m3u8_url:
                    if debug:
                        print(f"Constructed API URL: {m3u8_url}")
                    return m3u8_url
            else:
                if debug:
                    print("Could not extract entry ID from page")
            
            # Look for JSON data with video URLs
            json_patterns = [
                r'kalturaPlayerOptions\s*=\s*({[^}]+})',
                r'entryId["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'"entry_id"\s*:\s*"([^"]+)"',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    entry_id = matches[0] if isinstance(matches[0], str) else None
                    if entry_id and len(entry_id) > 5:  # Valid entry ID
                        if debug:
                            print(f"Found entry ID in JSON: {entry_id}")
                        m3u8_url = self._try_kaltura_api(entry_id, url)
                        if m3u8_url:
                            return m3u8_url
            
            if debug:
                print("No M3U8 URL found in page source")
                print("\nNote: M3U8 URLs are often loaded dynamically when video starts playing.")
                print("Try using capture_m3u8.py to capture the URL from network requests:")
                print(f"  python capture_m3u8.py '{url}'")
            
            return None
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None
    
    def _extract_kaltura_entry_id(self, html: str, url: str) -> Optional[str]:
        """Extract Kaltura entry ID from URL or HTML"""
        # Try to extract from URL first (common pattern: /media/ENTRY_ID)
        url_match = re.search(r'/media/[^/]+/([^/?]+)', url)
        if url_match:
            entry_id = url_match.group(1)
            # Clean up common URL encoding
            entry_id = entry_id.replace('+', ' ')
            return entry_id
        
        # Try to find in HTML
        patterns = [
            r'entryId["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"entry_id"\s*:\s*"([^"]+)"',
            r'entry_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'kentryid["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def _try_kaltura_api(self, entry_id: str, base_url: str) -> Optional[str]:
        """Try to construct Kaltura API URL to get M3U8"""
        # Common Kaltura API endpoints
        base_domain = urlparse(base_url).netloc
        
        # Try common Kaltura API patterns
        api_patterns = [
            f"https://{base_domain}/p/0/sp/0/playManifest/entryId/{entry_id}/format/applehttp/protocol/https/a.m3u8",
            f"https://{base_domain}/p/0/sp/0/playManifest/entryId/{entry_id}/format/url/protocol/https/a.m3u8",
            f"https://cdnapisec.kaltura.com/p/0/sp/0/playManifest/entryId/{entry_id}/format/applehttp/protocol/https/a.m3u8",
        ]
        
        for api_url in api_patterns:
            try:
                response = self.session.head(api_url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    # Verify it's actually an M3U8 file
                    content_type = response.headers.get('Content-Type', '')
                    if 'm3u8' in content_type or 'application/vnd.apple.mpegurl' in content_type:
                        return api_url
                    # Also check if the URL ends with .m3u8
                    if api_url.endswith('.m3u8'):
                        return api_url
            except:
                continue
        
        return None
    
    def parse_m3u8(self, m3u8_url: str) -> List[str]:
        """Parse M3U8 playlist and return list of TS segment URLs"""
        try:
            response = self.session.get(m3u8_url, timeout=10)
            response.raise_for_status()
            
            base_url = '/'.join(m3u8_url.split('/')[:-1]) + '/'
            playlist_text = response.text
            
            # Check if this is a master playlist (contains #EXT-X-STREAM-INF)
            if '#EXT-X-STREAM-INF' in playlist_text:
                print("Found master playlist, selecting best quality...")
                # Find all stream URLs with their quality info
                stream_info = []
                lines = playlist_text.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('#EXT-X-STREAM-INF'):
                        # Extract bandwidth and resolution if available
                        bandwidth = 0
                        resolution = None
                        if 'BANDWIDTH=' in line:
                            bw_match = re.search(r'BANDWIDTH=(\d+)', line)
                            if bw_match:
                                bandwidth = int(bw_match.group(1))
                        if 'RESOLUTION=' in line:
                            res_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                            if res_match:
                                resolution = res_match.group(1)
                        
                        # Next line should be the stream URL
                        if i + 1 < len(lines):
                            stream_url = lines[i + 1].strip()
                            if stream_url and not stream_url.startswith('#'):
                                # Skip subtitle tracks (they have TYPE=SUBTITLES in the line)
                                if 'TYPE=SUBTITLES' not in line and 'caption' not in stream_url.lower():
                                    if stream_url.startswith('http'):
                                        stream_info.append((bandwidth, resolution, stream_url))
                                    else:
                                        stream_info.append((bandwidth, resolution, urljoin(base_url, stream_url)))
                
                if stream_info:
                    # Sort by bandwidth (highest first) and select the best quality
                    stream_info.sort(key=lambda x: x[0], reverse=True)
                    best_bandwidth, best_resolution, best_url = stream_info[0]
                    print(f"Selected stream: {best_resolution or 'unknown'} @ {best_bandwidth} bps")
                    print(f"Stream URL: {best_url}")
                    return self.parse_m3u8(best_url)
            
            # Parse regular playlist for TS segments
            ts_segments = []
            lines = playlist_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle various segment URL patterns
                    # Check for .ts extension, segment/chunk in path, or segment number patterns
                    is_segment = (
                        line.endswith('.ts') or 
                        '/segment' in line.lower() or 
                        '/chunk' in line.lower() or
                        '/seg-' in line.lower() or
                        re.search(r'seg_\d+', line.lower()) or
                        re.search(r'chunk_\d+', line.lower())
                    )
                    
                    if is_segment:
                        # Handle relative and absolute URLs
                        if line.startswith('http'):
                            ts_segments.append(line)
                        else:
                            ts_segments.append(urljoin(base_url, line))
            
            return ts_segments
        except Exception as e:
            print(f"Error parsing M3U8: {e}")
            return []
    
    def download_segment(self, url: str, output_path: Path, segment_num: int, total: int) -> bool:
        """Download a single TS segment"""
        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded segment {segment_num}/{total}: {output_path.name}")
            return True
        except Exception as e:
            print(f"Error downloading segment {segment_num}: {e}")
            return False
    
    def download_all_segments(self, ts_urls: List[str], temp_dir: Path) -> List[Path]:
        """Download all TS segments to temporary directory"""
        downloaded_files = []
        
        print(f"\nDownloading {len(ts_urls)} segments...")
        for i, url in enumerate(ts_urls, 1):
            segment_name = f"segment_{i:05d}.ts"
            segment_path = temp_dir / segment_name
            downloaded_files.append(segment_path)
            
            if not self.download_segment(url, segment_path, i, len(ts_urls)):
                print(f"Warning: Failed to download segment {i}")
        
        return downloaded_files
    
    def concatenate_with_ffmpeg(self, segment_files: List[Path], output_path: Path) -> bool:
        """Concatenate TS segments using ffmpeg"""
        try:
            # Create a file list for ffmpeg concat
            concat_file = segment_files[0].parent / "concat_list.txt"
            with open(concat_file, 'w') as f:
                for seg_file in segment_files:
                    if seg_file.exists():
                        # Escape single quotes and use absolute path
                        abs_path = seg_file.resolve()
                        f.write(f"file '{abs_path}'\n")
            
            # Use ffmpeg to concatenate and convert
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            print(f"\nConcatenating segments and converting to MP4...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully created: {output_path}")
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg.")
            print("On macOS: brew install ffmpeg")
            print("On Ubuntu: sudo apt-get install ffmpeg")
            return False
        except Exception as e:
            print(f"Error concatenating files: {e}")
            return False
    
    def concatenate_simple(self, segment_files: List[Path], output_path: Path) -> bool:
        """Simple binary concatenation (fallback if ffmpeg fails)"""
        try:
            print(f"\nConcatenating segments (simple method)...")
            with open(output_path, 'wb') as outfile:
                for seg_file in segment_files:
                    if seg_file.exists():
                        with open(seg_file, 'rb') as infile:
                            shutil.copyfileobj(infile, outfile)
            
            print(f"Concatenated to: {output_path}")
            print("Note: This is a raw TS file. You may need to convert it with ffmpeg:")
            print(f"  ffmpeg -i {output_path} -c copy output.mp4")
            return True
        except Exception as e:
            print(f"Error concatenating files: {e}")
            return False
    
    def download_video(self, url: str, output_filename: Optional[str] = None, debug: bool = False) -> bool:
        """Main method to download video from Mediaspace URL"""
        print(f"Starting download from: {url}")
        
        # Step 1: Get M3U8 URL
        print("\nStep 1: Finding M3U8 playlist...")
        
        # Check if URL is already an M3U8 URL
        if url.endswith('.m3u8') or '.m3u8?' in url or '/a.m3u8' in url:
            print("URL is already an M3U8 playlist, using directly")
            m3u8_url = url
        else:
            m3u8_url = self.get_m3u8_url(url, debug=debug)
            if not m3u8_url:
                print("Error: Could not find M3U8 playlist URL")
                print("Please provide either:")
                print("  - A Mediaspace page URL")
                print("  - A direct M3U8 playlist URL")
                return False
        
        print(f"Found M3U8: {m3u8_url}")
        
        # Step 2: Parse M3U8 to get TS segments
        print("\nStep 2: Parsing playlist...")
        ts_urls = self.parse_m3u8(m3u8_url)
        
        if not ts_urls:
            print("Error: No TS segments found in playlist")
            return False
        
        print(f"Found {len(ts_urls)} segments")
        
        # Step 3: Download all segments
        temp_dir = Path(tempfile.mkdtemp(prefix="mediaspace_"))
        print(f"\nStep 3: Downloading segments to {temp_dir}...")
        
        try:
            segment_files = self.download_all_segments(ts_urls, temp_dir)
            
            # Step 4: Concatenate and convert
            if not output_filename:
                # Generate filename from URL
                parsed_url = urlparse(url)
                path_parts = [p for p in parsed_url.path.split('/') if p]
                if path_parts:
                    # For URLs like /media/L5+3000A/1_3e140s7n, use the last part
                    output_filename = path_parts[-1]
                    # Clean up the filename
                    output_filename = output_filename.replace('+', '_').replace(' ', '_')
                else:
                    output_filename = "video"
                if not output_filename.endswith('.mp4'):
                    output_filename += '.mp4'
            
            output_path = self.output_dir / output_filename
            
            print(f"\nStep 4: Stitching segments together...")
            success = self.concatenate_with_ffmpeg(segment_files, output_path)
            
            if not success:
                # Fallback to simple concatenation
                output_path_ts = output_path.with_suffix('.ts')
                success = self.concatenate_simple(segment_files, output_path_ts)
            
            return success
            
        finally:
            # Cleanup temporary files
            print(f"\nCleaning up temporary files...")
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return False


def main():
    if len(sys.argv) < 2:
        print("Mediaspace Video Downloader")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <mediaspace_url_or_m3u8_url> [output_filename] [--debug]")
        print("\nOptions:")
        print("  --debug    Show detailed debugging information")
        print("\nExample:")
        print(f"  python {sys.argv[0]} https://mediaspace.example.com/video/12345")
        print(f"  python {sys.argv[0]} https://mediaspace.example.com/playlist.m3u8 video.mp4")
        print(f"  python {sys.argv[0]} https://mediaspace.example.com/video/12345 --debug")
        print("\nNote: If M3U8 URL is not found automatically, use capture_m3u8.py:")
        print(f"  python capture_m3u8.py <mediaspace_url>")
        sys.exit(1)
    
    args = sys.argv[1:]
    url = args[0]
    output_filename = None
    debug = False
    
    for arg in args[1:]:
        if arg == '--debug':
            debug = True
        elif not arg.startswith('--'):
            output_filename = arg
    
    downloader = MediaspaceDownloader()
    success = downloader.download_video(url, output_filename, debug=debug)
    
    if success:
        print("\n✓ Download complete!")
        sys.exit(0)
    else:
        print("\n✗ Download failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
