# fetch_kml.py
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

CONCURRENT_DOWNLOADS = 2
INTER_DELAY = 1.5  # seconds delay between downloads

def sanitize_filename(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_")

async def download_kml(page, url, outdir):
    await page.goto(url, timeout=60000)
    print(f"Visiting {url}")

    # Try direct KML link first
    anchors = await page.query_selector_all("a")
    kml_url = None
    for a in anchors:
        href = await a.get_attribute("href")
        if href and href.lower().endswith(".kml"):
            kml_url = href
            break

    if kml_url:
        print(f"Found direct KML link: {kml_url}")
        # Fetch via browser context to keep cookies/session
        content = await page.evaluate("(url) => fetch(url).then(r => r.text())", kml_url)
        filename = sanitize_filename(url) + ".kml"
        fullpath = os.path.join(outdir, filename)
        with open(fullpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved KML to {fullpath}")
        return fullpath

    # Else, click "Export to KML" button and wait for download
    selectors = [
        "text=Export to KML",
        "text=Export KML",
        "text=Download KML",
        "button:has-text('Export')",
        "button:has-text('KML')",
        "a:has-text('KML')"
    ]
    button = None
    for sel in selectors:
        button = await page.query_selector(sel)
        if button:
            break

    if not button:
        print(f"[WARN] No export button found on {url}")
        return None

    async with page.expect_download(timeout=60000) as download_info:
        await button.click()
    download = await download_info.value
    suggested_name = download.suggested_filename or "omanreal_export.kml"
    filename = sanitize_filename(url) + "_" + suggested_name
    fullpath = os.path.join(outdir, filename)
    await download.save_as(fullpath)
    print(f"Downloaded KML to {fullpath}")
    return fullpath

async def run(urls_file, outdir):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    sem = asyncio.Semaphore(CONCURRENT_DOWNLOADS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        async def worker(url):
            async with sem:
                page = await browser.new_page()
                try:
                    res = await download_kml(page, url, outdir)
                    await asyncio.sleep(INTER_DELAY)
                    return res
                finally:
                    await page.close()

        tasks = [worker(url) for url in urls]
        results = await asyncio.gather(*tasks)
        await browser.close()

    print("All downloads done:")
    for r in results:
        if r:
            print(" -", r)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python fetch_kml.py maps.txt kml_out_dir")
        sys.exit(1)
    asyncio.run(run(sys.argv[1], sys.argv[2]))
