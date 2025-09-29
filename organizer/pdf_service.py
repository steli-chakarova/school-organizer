# organizer/pdf_service.py
from playwright.sync_api import sync_playwright

def html_to_pdf_bytes(html: str, base_url: str = None) -> bytes:
    """Generate PDF bytes from HTML content - simple and fast"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        
        try:
            page.set_content(html, wait_until="domcontentloaded")
            pdf = page.pdf(format="A4", print_background=True)
            return pdf
        finally:
            browser.close()
