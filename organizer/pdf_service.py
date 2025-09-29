# organizer/pdf_service.py
import threading
from playwright.sync_api import sync_playwright

# Global browser instance for better performance
_global_lock = threading.Lock()
_global_browser = None
_global_playwright = None

def get_browser(headless=True):
    """Get a browser instance - use global singleton for better performance"""
    global _global_browser, _global_playwright
    
    with _global_lock:
        if _global_browser is None:
            try:
                print("Initializing Playwright...")
                _global_playwright = sync_playwright().start()
                print("Launching browser...")
                _global_browser = _global_playwright.chromium.launch(
                    headless=headless, 
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--single-process",
                    "--no-zygote",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # Skip loading images for faster rendering
                    "--disable-javascript",  # Skip JS execution for faster rendering
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-first-run",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
                )
                print("Browser launched successfully!")
            except Exception as e:
                print(f"Browser initialization failed: {e}")
                # Clean up on failure
                if _global_playwright:
                    _global_playwright.stop()
                raise
    return _global_browser

def html_to_pdf_bytes(html: str, base_url: str = None) -> bytes:
    """Generate PDF bytes from HTML content"""
    import time
    start_time = time.time()
    
    browser = get_browser()
    print(f"Browser obtained in {time.time() - start_time:.2f}s")
    
    page_start = time.time()
    page = browser.new_page()
    
    try:
        # Set content directly - no external resources needed for our use case
        content_start = time.time()
        page.set_content(html, wait_until="commit", timeout=3000)  # Fastest - just wait for initial commit
        print(f"Content set in {time.time() - content_start:.2f}s")
        
        # Small delay to ensure content is fully rendered
        import time
        time.sleep(0.5)
        
        pdf_start = time.time()
        pdf = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "10mm", "right": "5mm", "bottom": "15mm", "left": "5mm"},
            timeout=8000  # 8 second timeout for PDF generation
        )
        print(f"PDF generated in {time.time() - pdf_start:.2f}s")
        print(f"Total time: {time.time() - start_time:.2f}s")
        return pdf
    finally:
        page.close()

def cleanup_browser():
    """Clean up browser resources"""
    global _global_browser, _global_playwright
    
    with _global_lock:
        if _global_browser:
            _global_browser.close()
            _global_browser = None
        if _global_playwright:
            _global_playwright.stop()
            _global_playwright = None
