# fetch_kml.py
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

CONCURRENT = 3
INTER_MAP_DELAY = 1.0

def sanitize_filename_from_url(url):
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_")

async def download_for_page(browser, url, out_dir):
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=60000)
        # Find "Export to KML" button or link
        selectors = [
            "text=Export to KML",
            "text=Export KML",
            "text=Download KML",
            "button:has-text('Export')",
            "button:has-text('KML')",
            "a:has-text('KML')"
        ]
        found = None
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                found = el
                break

        if not found:
            print(f"[WARN] Export button not found on {url}")
            return None

        async with page.expect_download(timeout=60000) as download_info:
            await found.click()
        download = await download_info.value
        filename = sanitize_filename_from_url(url) + "_" + (download.suggested_filename or "omanreal.kml")
        out_path = os.path.join(out_dir, filename)
        await download.save_as(out_path)
        print(f"Saved KML: {out_path}")
        return out_path

    except Exception as e:
        print(f"[ERROR] {url} -> {e}")
        return None
    finally:
        await page.close()

async def fetch_all(urls, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sem = asyncio.Semaphore(CONCURRENT)

        async def sem_task(url):
            async with sem:
                result = await download_for_page(browser, url, out_dir)
                await asyncio.sleep(INTER_MAP_DELAY)
                return result

        tasks = [asyncio.create_task(sem_task(url)) for url in urls]
        results = await asyncio.gather(*tasks)
        await browser.close()
    return results

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python fetch_kml.py maps.txt ./kmls/")
        return
    urls_file = sys.argv[1]
    out_dir = sys.argv[2]
    with open(urls_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    asyncio.run(fetch_all(urls, out_dir))

if __name__ == "__main__":
    main()
