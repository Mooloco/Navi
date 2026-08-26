"""headless 浏览器模拟:像真实浏览器一样解析并下载 favicon。

覆盖正则抓取搞不定的场景:JS 渲染页面、复杂跳转、防爬防护(LuCI 403 等)。
安装: pip install playwright && playwright install chromium --with-deps
未安装时自动降级(_HAS_PLAYWRIGHT=False),不影响服务启动。
"""

try:
    from playwright.async_api import async_playwright, Browser

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    Browser = None  # type: ignore

_pw = None
_browser: Browser | None = None

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


async def startup() -> None:
    global _pw, _browser
    if not _HAS_PLAYWRIGHT or _browser is not None:
        return
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )


async def shutdown() -> None:
    global _pw, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _pw is not None:
        await _pw.stop()
        _pw = None


async def get_favicon_bytes(url: str) -> tuple[bytes, str] | None:
    """打开页面 → 取 DOM 声明的 favicon → 浏览器网络栈下载。

    返回 (图片字节, 扩展名);任何环节失败返回 None。
    """
    if not _HAS_PLAYWRIGHT or _browser is None:
        return None
    page = None
    try:
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
