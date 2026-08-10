from __future__ import annotations

import asyncio
import re

from playwright.async_api import async_playwright, Request, Response, Page, Browser, Frame

from .models import Capture
from .source_name import choose_source_name

MEDIA_RE = re.compile(r"\.(m3u8|mpd|vtt|srt)(?:\?|$)", re.I)
WEAK_TITLES = {"player", "embed", "video", ""}


def classify_url(url: str, content_type: str = "") -> str | None:
    lower = url.lower()
    ct = content_type.lower()
    if ".vtt" in lower or "text/vtt" in ct:
        return "vtt"
    if ".srt" in lower or "subrip" in ct:
        return "srt"
    if ".mpd" in lower or "dash+xml" in ct:
        return "dash"
    if ".m3u8" in lower or "mpegurl" in ct:
        return "hls"
    return None


async def _click_play_candidates(scope: Page | Frame) -> None:
    selectors = [
        "button:has-text('Play')",
        "[aria-label*='Play' i]",
        "video",
        "button",
    ]
    for selector in selectors:
        try:
            loc = scope.locator(selector).first
            if await loc.count():
                await loc.click(timeout=1000, force=True)
        except Exception:
            pass


async def _frame_source_name(frame: Frame) -> str:
    titles: list[str] = []
    visible_text = ""
    try:
        title = await frame.evaluate("document.title || ''")
        if title:
            titles.append(str(title))
    except Exception:
        pass
    try:
        visible_text = str(await frame.evaluate("document.body ? document.body.innerText : ''") or "")
    except Exception:
        pass
    return choose_source_name(titles=titles, visible_text=visible_text)


async def _best_source_name(page: Page) -> str:
    titles: list[str] = []
    visible_texts: list[str] = []
    for frame in page.frames:
        try:
            title = await frame.evaluate("document.title || ''")
            text = str(title).strip()
            if text:
                titles.append(text)
        except Exception:
            pass
        try:
            body_text = await frame.evaluate("document.body ? document.body.innerText : ''")
            if body_text:
                visible_texts.append(str(body_text))
        except Exception:
            pass
    try:
        title = (await page.title()).strip()
        if title:
            titles.append(title)
    except Exception:
        pass

    return choose_source_name(titles=titles, visible_text="\n".join(visible_texts))


async def _source_name_for_url(page: Page, source_url: str | None) -> str:
    if not source_url:
        return ""
    for frame in page.frames:
        if frame.url == source_url:
            return await _frame_source_name(frame)
    return ""


async def capture_streams(
    url: str,
    *,
    timeout_ms: int = 15000,
    headless: bool = True,
    user_agent: str | None = None,
) -> list[Capture]:
    found: dict[str, Capture] = {}
    request_headers: dict[str, dict[str, str]] = {}
    page_title: str | None = None

    def remember_request(request: Request) -> None:
        request_headers[request.url] = dict(request.headers)
        kind = classify_url(request.url)
        if kind:
            found[request.url] = Capture(
                url=request.url,
                kind=kind,
                headers=dict(request.headers),
                source_url=request.frame.url if request.frame else url,
                page_title=page_title,
            )

    async def remember_response(response: Response) -> None:
        headers = dict(response.headers)
        content_type = headers.get("content-type", "")
        kind = classify_url(response.url, content_type)
        if kind:
            found[response.url] = Capture(
                url=response.url,
                kind=kind,
                headers=request_headers.get(response.url, {}),
                response_headers=headers,
                source_url=response.request.frame.url if response.request.frame else url,
                page_title=page_title,
            )

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=user_agent) if user_agent else await browser.new_context()
        page = await context.new_page()
        context.on("request", remember_request)
        context.on("response", lambda response: asyncio.create_task(remember_response(response)))
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page_title = await _best_source_name(page)
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
        while asyncio.get_event_loop().time() < deadline:
            for frame in page.frames:
                try:
                    await _click_play_candidates(frame)
                except Exception:
                    pass
            await _click_play_candidates(page)
            page_title = await _best_source_name(page) or page_title
            if any(c.kind in {"hls", "dash"} for c in found.values()):
                await page.wait_for_timeout(2500)
                break
            await page.wait_for_timeout(750)
        page_title = await _best_source_name(page) or page_title
        for capture in found.values():
            source_name = await _source_name_for_url(page, capture.source_url)
            if source_name:
                capture.page_title = source_name
            elif not capture.page_title or capture.page_title.lower() in WEAK_TITLES:
                capture.page_title = page_title
        await browser.close()
    return list(found.values())
