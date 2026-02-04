def fetch_dynamic_html(url, wait=3, timeout=30):
    """Fetches fully rendered HTML using Playwright (Apple Silicon–friendly)."""
    logging.info(f"Rendering page: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            
            # Set timeout and user-agent header
            page.set_default_timeout(timeout * 1000)
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36"
            })
            
            page.goto(url, wait_until="load")
            time.sleep(wait)  # Give JS some time to load
            
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logging.error(f"Failed to render {url}: {e}")
        return None