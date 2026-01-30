#!/usr/bin/env python3
"""
Browser-based M3U8 URL Capture Tool
Uses browser automation to capture M3U8 URLs from network requests
"""

import sys
import time
from pathlib import Path
from typing import Optional

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def capture_with_playwright(url: str, wait_time: int = 10) -> Optional[str]:
    """Capture M3U8 URL using Playwright (preferred method)"""
    m3u8_urls = []
    
    with sync_playwright() as p:
        print("Launching browser with Playwright...")
        browser = p.chromium.launch(headless=False)  # Show browser so user can see it
        context = browser.new_context()
        page = context.new_page()
        
        # Listen for network requests
        def handle_response(response):
            url_str = response.url
            if '.m3u8' in url_str:
                m3u8_urls.append(url_str)
                print(f"Found M3U8 URL: {url_str}")
        
        page.on("response", handle_response)
        
        print(f"Loading page: {url}")
        page.goto(url, wait_until="networkidle")
        
        # Try to find and click play button
        try:
            print("Looking for play button...")
            # Common play button selectors
            play_selectors = [
                'button[aria-label*="Play"]',
                'button[aria-label*="play"]',
                '.play-button',
                '.vjs-big-play-button',
                'button.vjs-play-control',
                '[class*="play"]',
            ]
            
            for selector in play_selectors:
                try:
                    play_button = page.query_selector(selector)
                    if play_button:
                        print(f"Found play button with selector: {selector}")
                        play_button.click()
                        print("Clicked play button")
                        break
                except:
                    continue
            
            # Also try clicking on video element itself
            try:
                video = page.query_selector('video')
                if video:
                    video.click()
                    print("Clicked video element")
            except:
                pass
                
        except Exception as e:
            print(f"Could not find/click play button: {e}")
            print("Waiting for network requests anyway...")
        
        # Wait for M3U8 URLs to appear
        print(f"Waiting up to {wait_time} seconds for M3U8 URLs...")
        start_time = time.time()
        while time.time() - start_time < wait_time:
            if m3u8_urls:
                break
            time.sleep(0.5)
        
        # Keep browser open a bit longer to capture more requests
        time.sleep(3)
        browser.close()
    
    if m3u8_urls:
        # Return the first M3U8 URL (usually the master playlist)
        return m3u8_urls[0]
    return None


def capture_with_selenium(url: str, wait_time: int = 10) -> Optional[str]:
    """Capture M3U8 URL using Selenium (fallback method)"""
    m3u8_urls = []
    
    chrome_options = Options()
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--v=1')
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    print("Launching browser with Selenium...")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"Loading page: {url}")
        driver.get(url)
        
        # Wait a bit for page to load
        time.sleep(2)
        
        # Try to find and click play button
        try:
            play_selectors = [
                'button[aria-label*="Play"]',
                'button[aria-label*="play"]',
                '.play-button',
                '.vjs-big-play-button',
            ]
            
            for selector in play_selectors:
                try:
                    play_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if play_button:
                        play_button.click()
                        print("Clicked play button")
                        break
                except:
                    continue
        except Exception as e:
            print(f"Could not find/click play button: {e}")
        
        # Get performance logs to find M3U8 URLs
        print(f"Capturing network requests for {wait_time} seconds...")
        start_time = time.time()
        while time.time() - start_time < wait_time:
            logs = driver.get_log('performance')
            for log in logs:
                message = log.get('message', '')
                if '.m3u8' in message:
                    # Extract URL from log message
                    import json
                    try:
                        log_data = json.loads(message)
                        if 'message' in log_data:
                            method = log_data['message'].get('method', '')
                            params = log_data['message'].get('params', {})
                            if method == 'Network.responseReceived':
                                response_url = params.get('response', {}).get('url', '')
                                if '.m3u8' in response_url and response_url not in m3u8_urls:
                                    m3u8_urls.append(response_url)
                                    print(f"Found M3U8 URL: {response_url}")
                            elif 'request' in params:
                                request_url = params['request'].get('url', '')
                                if '.m3u8' in request_url and request_url not in m3u8_urls:
                                    m3u8_urls.append(request_url)
                                    print(f"Found M3U8 URL: {request_url}")
                    except:
                        pass
            time.sleep(0.5)
        
    finally:
        driver.quit()
    
    if m3u8_urls:
        return m3u8_urls[0]
    return None


def capture_m3u8_url(url: str, wait_time: int = 15, debug: bool = False) -> Optional[str]:
    """
    Capture M3U8 URL from a Mediaspace page using browser automation.
    This function can be imported and used programmatically.
    
    Args:
        url: The Mediaspace page URL
        wait_time: How long to wait for M3U8 URLs to appear (seconds)
        debug: Enable debug output
    
    Returns:
        The M3U8 URL if found, None otherwise
    """
    m3u8_url = None
    
    # Try Playwright first (better for network capture)
    if PLAYWRIGHT_AVAILABLE:
        if debug:
            print("Using Playwright to capture M3U8 URL...")
        try:
            m3u8_url = capture_with_playwright(url, wait_time)
            if m3u8_url:
                return m3u8_url
        except Exception as e:
            if debug:
                print(f"Playwright failed: {e}")
            m3u8_url = None
    
    # Fallback to Selenium
    if not m3u8_url and SELENIUM_AVAILABLE:
        if debug:
            print("Trying Selenium...")
        try:
            m3u8_url = capture_with_selenium(url, wait_time)
            if m3u8_url:
                return m3u8_url
        except Exception as e:
            if debug:
                print(f"Selenium failed: {e}")
            m3u8_url = None
    
    if not m3u8_url:
        if debug:
            if not PLAYWRIGHT_AVAILABLE and not SELENIUM_AVAILABLE:
                print("Browser automation not available.")
                print("Install browser automation libraries:")
                print("  pip install playwright selenium")
                print("  playwright install chromium")
    
    return m3u8_url


def main():
    if len(sys.argv) < 2:
        print("M3U8 URL Capture Tool")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <mediaspace_url>")
        print("\nThis tool will:")
        print("  1. Open the page in a browser")
        print("  2. Try to start video playback")
        print("  3. Capture M3U8 URLs from network requests")
        print("  4. Output the M3U8 URL for use with mediaspace_downloader.py")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("=" * 60)
    print("M3U8 URL Capture Tool")
    print("=" * 60)
    print(f"URL: {url}\n")
    
    m3u8_url = capture_m3u8_url(url, wait_time=15, debug=True)
    
    if not m3u8_url:
        print("\n" + "=" * 60)
        print("Could not automatically capture M3U8 URL")
        print("=" * 60)
        print("\nManual method:")
        print("1. Open the video page in your browser")
        print("2. Open Developer Tools (F12 or Cmd+Option+I)")
        print("3. Go to the Network tab")
        print("4. Filter by 'm3u8' or 'media'")
        print("5. Start playing the video")
        print("6. Look for requests ending in .m3u8")
        print("7. Right-click the request > Copy > Copy URL")
        print("8. Use that URL with: python mediaspace_downloader.py <m3u8_url>")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("SUCCESS! Found M3U8 URL:")
    print("=" * 60)
    print(m3u8_url)
    print("\nYou can now use this URL with mediaspace_downloader.py:")
    print(f"  python mediaspace_downloader.py '{m3u8_url}'")
    
    # Save to file for convenience
    output_file = Path("captured_m3u8_url.txt")
    output_file.write_text(m3u8_url)
    print(f"\nM3U8 URL also saved to: {output_file}")


if __name__ == "__main__":
    main()
