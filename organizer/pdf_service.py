# organizer/pdf_service.py
import threading
from playwright.sync_api import sync_playwright

# Global browser instance for better performance
_global_lock = threading.Lock()
_global_browser = None
_global_playwright = None

def get_browser(headless=True):
    """Get a browser instance - create new browser for each request for better isolation"""
    try:
        print("Creating new browser instance...")
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=headless, 
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--single-process",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
                "--disable-javascript",
                "--disable-default-apps",
                "--disable-sync",
                "--disable-translate",
                "--hide-scrollbars",
                "--mute-audio",
                "--no-first-run"
            ]
        )
        print("Browser created successfully!")
        return browser, playwright
    except Exception as e:
        print(f"Browser creation failed: {e}")
        raise

def html_to_pdf_bytes(html: str, base_url: str = None) -> bytes:
    """Generate PDF bytes from HTML content - ultra-fast version"""
    import time
    start_time = time.time()
    
    browser, playwright = get_browser()
    print(f"Browser created in {time.time() - start_time:.2f}s")
    
    try:
        page = browser.new_page()
        
        # Set content with absolute minimal waiting
        content_start = time.time()
        page.set_content(html, wait_until="commit", timeout=1000)  # Only 1 second timeout
        print(f"Content set in {time.time() - content_start:.2f}s")
        
        # Generate PDF with absolute minimal options
        pdf_start = time.time()
        pdf = page.pdf(
            format="A4",
            timeout=5000  # Only 5 second timeout
        )
        print(f"PDF generated in {time.time() - pdf_start:.2f}s")
        print(f"Total time: {time.time() - start_time:.2f}s")
        return pdf
    finally:
        page.close()
        browser.close()
        playwright.stop()

# Browser cleanup is now handled per-request in html_to_pdf_bytes
