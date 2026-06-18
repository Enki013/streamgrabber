from __future__ import annotations

import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://streamimdb.ru/embed/tv/tt3032476"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        rows = []
        for i, frame in enumerate(page.frames):
            try:
                title = await frame.evaluate("document.title || ''")
            except Exception as e:
                title = f"ERR {e}"
            try:
                url = frame.url
                text = await frame.evaluate("document.body ? document.body.innerText : ''")
                links = await frame.evaluate("""
                Array.from(document.querySelectorAll('a,button,[role=button],select,option,[data-episode],[data-id],[data-season],[data-src]')).slice(0,200).map((el,idx)=>({
                  idx,
                  tag: el.tagName,
                  text: (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().slice(0,120),
                  href: el.href || el.getAttribute('href') || '',
                  cls: el.className || '',
                  id: el.id || '',
                  data: Object.fromEntries(Array.from(el.attributes).filter(a=>a.name.startsWith('data-') || ['role','aria-label','title'].includes(a.name)).map(a=>[a.name,a.value]))
                }))
                """)
                rows.append({"frame": i, "url": url, "title": title, "text": text[:3000], "controls": links})
            except Exception as e:
                rows.append({"frame": i, "url": frame.url, "title": title, "error": str(e)})
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        await browser.close()

asyncio.run(main())
