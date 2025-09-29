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
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--single-process",
                    "--no-zygote",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # Skip loading images for faster rendering
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-first-run",
                    "--disable-logging",
                    "--disable-gpu-logging",
                    "--disable-dev-tools"
                ]
            )
            print("Browser launched successfully!")
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
        page.set_content(html, wait_until="networkidle", timeout=10000)  # Wait for network to be idle
        print(f"Content set in {time.time() - content_start:.2f}s")
        
        pdf_start = time.time()
        pdf = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "10mm", "right": "5mm", "bottom": "15mm", "left": "5mm"},
            prefer_css_page_size=False,  # Faster without CSS page size
            display_header_footer=False,
            timeout=30000  # 30 second timeout for PDF generation
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
