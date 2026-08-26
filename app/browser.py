"""headless 浏览器模拟:像真实浏览器一样解析并下载 favicon。

按需启动:有抓取任务才拉起 Chromium,闲置 30 秒自动关闭,
避免常驻内存占用。未安装 Playwright 时自动降级(_HAS_PLAYWRIGHT=False)。
安装: pip install playwright && playwright install chromium --with-deps
"""

try:
    from playwright.async_api import async_playwright, Browser

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    Browser = None  # type: ignore

import asyncio
import os
import time

_pw = None
_browser = None  # type: ignore[assignment]
_last_used = 0.0
_watchdog_task = None  # type: ignore[assignment]

IDLE_TIMEOUT = 30  # 闲置多少秒后自动关闭浏览器
# 远程 CDP 端点(容器部署时指向浏览器容器);为空则本地拉起 Chromium
CDP_ENDPOINT = os.environ.get("NAVI_BROWSER_CDP") or None

# 浏览器标准 favicon 选择:优先普通 icon,apple-touch-icon 垫底
FAVICON_JS = """() => {
  const links = [...document.querySelectorAll('link[rel*="icon" i]')];
  const normal = links.filter(l => !/apple/i.test(l.rel));
  const pick = (normal.length ? normal : links)[0];
  return pick ? pick.href : null;
}"""

_CTYPE_EXT = {
    "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
    "image/png": "png",
    "image/svg+xml": "svg",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
}


def _ext_from_ctype(ctype: str) -> str | None:
    return _CTYPE_EXT.get(ctype.lower().split(";")[0].strip())


async def _ensure_browser() -> None:
    """懒启动:首次抓取时才连接/拉起浏览器。

    设置了 NAVI_BROWSER_CDP 时连接远程浏览器容器(Docker 部署);
    否则本地拉起 Chromium(裸机部署)。
    """
    global _pw, _browser
    if _browser is not None:
        return
    _pw = await async_playwright().start()
    if CDP_ENDPOINT:
        _browser = await _pw.chromium.connect_over_cdp(CDP_ENDPOINT)
    else:
        _browser = await _pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )


async def _close_browser() -> None:
    global _pw, _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _pw is not None:
        try:
            await _pw.stop()
        except Exception:
            pass
        _pw = None


async def _watchdog() -> None:
    """闲置超时回收:每 5 秒检查一次,超时自动关浏览器。"""
    while True:
        await asyncio.sleep(5)
        if _browser is not None and time.monotonic() - _last_used > IDLE_TIMEOUT:
            await _close_browser()


async def startup() -> None:
    """服务启动时只挂 watchdog,不拉起浏览器。"""
    global _watchdog_task
    if not _HAS_PLAYWRIGHT or _watchdog_task is not None:
        return
    _watchdog_task = asyncio.create_task(_watchdog())


async def shutdown() -> None:
    global _watchdog_task
    if _watchdog_task is not None:
        _watchdog_task.cancel()
        try:
            await _watchdog_task
        except asyncio.CancelledError:
            pass
        _watchdog_task = None
    await _close_browser()


async def get_favicon_bytes(url: str) -> tuple[bytes, str] | None:
    """打开页面 → 取 DOM 声明的 favicon → 浏览器网络栈下载。

    返回 (图片字节, 扩展名);任何环节失败返回 None。
    浏览器按需启动,每次使用后刷新闲置计时。
    """
    if not _HAS_PLAYWRIGHT:
        return None
    global _last_used
    page = None
    try:
        await _ensure_browser()
        _last_used = time.monotonic()
        page = await _browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=8000)
        await page.wait_for_timeout(1200)  # 给 JS 渲染留时间
        href = await page.evaluate(FAVICON_JS)
        if not href:
            return None
        resp = await page.request.get(href, timeout=8000)
        if resp.status != 200:
            return None
        ctype = resp.headers.get("content-type", "")
        if not ctype.startswith("image/"):
            return None
        ext = _ext_from_ctype(ctype) or "ico"
        return await resp.body(), ext
    except Exception:
        return None
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass
        _last_used = time.monotonic()
