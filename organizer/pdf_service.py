# organizer/pdf_service.py
from playwright.sync_api import sync_playwright

def get_browser(headless=True):
    """Create a fresh browser instance for each request to avoid async conflicts"""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=headless, 
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]
    )
    return browser, playwright

def html_to_pdf_bytes(html: str, base_url: str = None) -> bytes:
    """Generate PDF bytes from HTML content"""
    browser, playwright = get_browser()
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
        browser.close()
        playwright.stop()
