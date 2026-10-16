"""headless 浏览器模拟:像真实浏览器一样解析并下载 favicon(可选组件)。

默认关闭。Navi 的图标抓取主力是 httpx 静态解析(见 app/favicon.py),
它能覆盖绝大多数站点;真正的浏览器只在少数「图标由 JS 动态写入」的
SPA 上才有额外价值,而代价是数百 MB 常驻内存。因此这里改成显式开关:

    NAVI_BROWSER=off    默认。不加载 Playwright,favicon 只走 httpx 静态抓取
    NAVI_BROWSER=local  在本进程内拉起 Chromium(Playwright 拥有进程,close() 能真正回收)
    NAVI_BROWSER=cdp    连接外部浏览器容器(ws://...);注意 close() 只是断开连接

未安装 Playwright 时自动降级(_HAS_PLAYWRIGHT=False),任何模式都退化为 off。
安装(仅 local / cdp 模式需要):
    pip install playwright && playwright install chromium --with-deps
"""
from __future__ import annotations

import asyncio
import os
import time

try:
    from playwright.async_api import async_playwright, Browser

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    Browser = None  # type: ignore

_pw = None
_browser = None  # type: ignore[assignment]
_last_used = 0.0
_watchdog_task = None  # type: ignore[assignment]
_launch_lock = asyncio.Lock()
_inflight = 0  # 正在进行的抓取任务数

IDLE_TIMEOUT = int(os.environ.get("NAVI_BROWSER_IDLE", "30"))  # 闲置多少秒后关闭(local 模式)
# 远程 CDP 端点(仅 NAVI_BROWSER=cdp 时使用)
CDP_ENDPOINT = (os.environ.get("NAVI_BROWSER_CDP") or "").strip() or None
# 同时抓取的页面数上限:批量刷新整页图标时,防止一次开一堆标签把内存顶爆
SCRAPE_CONCURRENCY = max(1, int(os.environ.get("NAVI_BROWSER_CONCURRENCY", "1")))
_sem = asyncio.Semaphore(SCRAPE_CONCURRENCY)

# ---------- 运行模式 ----------
MODE = (os.environ.get("NAVI_BROWSER") or "").strip().lower()
if not MODE:
    # 兼容旧部署:只设了 NAVI_BROWSER_CDP 时按 cdp 处理
    MODE = "cdp" if CDP_ENDPOINT else "off"
if MODE not in ("off", "local", "cdp"):
    MODE = "off"
if MODE == "cdp" and not CDP_ENDPOINT:
    MODE = "off"
# 真正启用浏览器需要:模式非 off 且 Playwright 已装
ACTIVE = _HAS_PLAYWRIGHT and MODE in ("local", "cdp")

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


def _on_disconnected(*_args) -> None:
    """远端浏览器被回收/崩溃时清空句柄,下次抓取会自动重建。"""
    global _browser
    _browser = None


async def _stop_driver() -> None:
    """停掉 Playwright driver 进程(只收 driver,不碰浏览器句柄)。"""
    global _pw
    pw, _pw = _pw, None
    if pw is not None:
        try:
            await pw.stop()
        except Exception:
            pass


async def _ensure_browser() -> None:
    """懒启动:首次抓取时才连接/拉起浏览器。并发请求时只启动一次。

    关键:上一次若「driver 启动成功但连接失败」,会留下一个仍在运行的 node
    driver 进程。必须先收干净再新建 —— 否则每个失败请求都泄漏一个约 120MB
    的进程,几十次就吃满宿主机。这是历史故障的根因。
    """
    global _pw, _browser
    if _browser is not None:
        return
    async with _launch_lock:
        if _browser is not None:
            return
        await _stop_driver()  # 收掉上一次可能残留的 driver
        pw = await async_playwright().start()
        try:
            if MODE == "cdp":
                br = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
            else:
                br = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
        except Exception:
            # 连接/启动失败:把刚起的 driver 收干净再抛,绝不留孤儿进程
            try:
                await pw.stop()
            except Exception:
                pass
            raise
        _pw = pw
        _browser = br
        try:
            _browser.on("disconnected", _on_disconnected)
        except Exception:
            pass


async def _close_browser() -> None:
    global _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    await _stop_driver()


async def _watchdog() -> None:
    """闲置超时回收:每 5 秒检查一次,超时关浏览器。

    cdp 模式下跳过:连接本身开销很低,反复断开重连反而会不停拉起远端
    浏览器容器,交给对方自身的会话超时回收即可。
    """
    while True:
        await asyncio.sleep(5)
        if MODE == "cdp":
            continue
        if (
            _browser is not None
            and _inflight == 0
            and time.monotonic() - _last_used > IDLE_TIMEOUT
        ):
            await _close_browser()


async def startup() -> None:
    """服务启动时只挂 watchdog,不拉起浏览器。"""
    global _watchdog_task
    if not ACTIVE or _watchdog_task is not None:
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
    浏览器按需启动,每次使用后刷新闲置计时;并发受 SCRAPE_CONCURRENCY 限制。
    """
    if not ACTIVE:
        return None
    global _last_used, _inflight
    async with _sem:
        _inflight += 1
        _last_used = time.monotonic()
        page = None
        try:
            await _ensure_browser()
            if _browser is None:
                return None
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
            _inflight -= 1
            _last_used = time.monotonic()
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
