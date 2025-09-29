# organizer/pdf_service.py
import threading
from playwright.sync_api import sync_playwright

# Use thread-local storage to avoid conflicts with Django's async handling
_thread_local = threading.local()

def get_browser(headless=True):
    """Get a browser instance for the current thread"""
    if not hasattr(_thread_local, 'browser') or _thread_local.browser is None:
        _thread_local.playwright = sync_playwright().start()
        _thread_local.browser = _thread_local.playwright.chromium.launch(
            headless=headless, 
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
        )
    return _thread_local.browser

def html_to_pdf_bytes(html: str, base_url: str = None) -> bytes:
    """Generate PDF bytes from HTML content"""
    browser = get_browser()
    page = browser.new_page()
    
    try:
        # Set content directly - no external resources needed for our use case
        page.set_content(html, wait_until="load")
        
        pdf = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "10mm", "right": "5mm", "bottom": "15mm", "left": "5mm"},
        )
        return pdf
    finally:
        page.close()
