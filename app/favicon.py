import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "favicons"
USER_AGENT = "Mozilla/5.0 (Navi/0.1)"

ICON_EXTS = ["ico", "png", "svg", "jpg", "jpeg", "gif", "webp"]
EXT_MEDIA = {
    "ico": "image/x-icon",
    "png": "image/png",
    "svg": "image/svg+xml",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}
FAIL_TTL = 3600  # 抓取失败后 1 小时内不再重试(秒回 404)

# 常见图标路径:HTML 解析失败时逐条探测(静态资源通常不受防爬限制)
COMMON_PATHS = [
    "/favicon.ico",
    "/favicon.png",
    "/apple-touch-icon.png",
    "/static/favicon.ico",
    "/icons/favicon.ico",
    "/luci-static/argon/icon/favicon-32x32.png",
    "/luci-static/argon/favicon.ico",
    "/luci-static/resources/icons/favicon.ico",
]

_client: httpx.AsyncClient | None = None


def _cache_path(origin: str, ext: str) -> Path:
    return CACHE_DIR / (hashlib.md5(origin.encode()).hexdigest() + "." + ext)


def _fail_path(origin: str) -> Path:
    return CACHE_DIR / (hashlib.md5(origin.encode()).hexdigest() + ".fail")


def parse_origin(url: str) -> str | None:
    try:
        p = urlparse(url)
        if p.scheme in ("http", "https") and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except ValueError:
        pass
    return None


def _ext_from_ctype(ctype: str) -> str | None:
    ctype = ctype.lower().split(";")[0].strip()
    mapping = {
        "image/x-icon": "ico",
        "image/vnd.microsoft.icon": "ico",
        "image/png": "png",
        "image/svg+xml": "svg",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    return mapping.get(ctype)


def _find_icon_href(html: str, base_url: str) -> str | None:
    """从 HTML 里解析 <link rel=...icon...> 的 href,按浏览器优先级取最合适的。"""
    pat = re.compile(
        r'<link\b[^>]*\brel=["\']([^"\']*)["\'][^>]*>',
        re.IGNORECASE,
    )
    candidates = []
    for m in pat.finditer(html):
        tag = m.group(0)
        rel = m.group(1).lower().strip()
        if "icon" not in rel:
            continue
        hm = re.search(r'href=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if not hm:
            continue
        sm = re.search(r'sizes=["\'](\d+)x(\d+)["\']', tag, re.IGNORECASE)
        size = int(sm.group(1)) if sm else 0
        # 优先级:非 apple 的 icon/shortcut icon 在前,apple-touch-icon 垫底;同 rel 取小尺寸
        priority = 1 if "apple" in rel else 0
        candidates.append((priority, size, hm.group(1)))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    return urljoin(base_url, candidates[0][2])


_SKIP_LINK = re.compile(
    r"\.(css|js|png|jpe?g|gif|ico|svg|webp|woff2?|ttf|zip|tar|gz)(\?|$)", re.I
)


def _collect_entry_links(html: str, base_url: str, origin: str, limit: int = 6) -> list[str]:
    """收集页面内的同源入口链接(meta refresh / a href / iframe),过滤静态资源。"""
    links: set[str] = set()

    for m in re.finditer(
        r"<meta\b[^>]*http-equiv=[\"']refresh[\"'][^>]*>", html, re.I
    ):
        cm = re.search(r"url=([^\"'>]+)", m.group(0), re.I)
        if cm:
            u = urljoin(base_url, cm.group(1).strip())
            if u.startswith(origin):
                links.add(u)

    for m in re.finditer(r"<a\b[^>]*\bhref=[\"']([^\"']+)[\"']", html, re.I):
        u = urljoin(base_url, m.group(1))
        if u.startswith(origin):
            links.add(u)

    for m in re.finditer(r"<iframe\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html, re.I):
        u = urljoin(base_url, m.group(1))
        if u.startswith(origin):
            links.add(u)

    return [u for u in links if not _SKIP_LINK.search(u)][:limit]


async def _fetch_html(url: str) -> str | None:
    try:
        resp = await _client.get(url)
        ctype = resp.headers.get("content-type", "")
        if resp.status_code == 200 and "html" in ctype:
            return resp.text
    except Exception:
        pass
    return None


async def _try_download(client, url: str) -> tuple[bytes, str] | None:
    try:
        resp = await client.get(url)
        ctype = resp.headers.get("content-type", "")
        if resp.status_code == 200 and ctype.startswith("image/"):
            ext = _ext_from_ctype(ctype) or "ico"
            return resp.content, ext
    except Exception:
        pass
    return None


def _save_cache(origin: str, data: bytes, ext: str) -> None:
    _cache_path(origin, ext).write_bytes(data)
    _fail_path(origin).unlink(missing_ok=True)


async def startup() -> None:
    global _client
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _client = httpx.AsyncClient(
        follow_redirects=True,
        timeout=6.0,
        headers={"User-Agent": USER_AGENT},
    )


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def fetch_favicon(url: str) -> tuple[bytes, str] | None:
    """返回 (图片字节, 媒体类型);失败返回 None。策略:
    1) 磁盘缓存命中直接返回
    2) 抓页面 HTML,解析 <link rel="icon"> 声明
    3) 兜底默认 /favicon.ico
    4) 全部失败 → 失败缓存,24h 内秒回 None
    """
    origin = parse_origin(url)
    if origin is None:
        return None

    # 1. 磁盘缓存(多扩展名)
    for ext in ICON_EXTS:
        cache = _cache_path(origin, ext)
        if cache.exists():
            return cache.read_bytes(), EXT_MEDIA[ext]

    # 失败缓存:TTL 内直接失败
    fail = _fail_path(origin)
    if fail.exists():
        try:
            if time.time() - float(fail.read_text()) < FAIL_TTL:
                return None
        except ValueError:
            pass
        fail.unlink(missing_ok=True)

    # 2. 轻量抓取:抓页面 HTML,解析 icon 声明;没有则追踪入口链接(meta refresh / a href)
    pages = [url] if url.startswith(origin) else [url, origin + "/"]
    page_html = None
    page_url = None
    for p in pages:
        page_html = await _fetch_html(p)
        if page_html is not None:
            page_url = p
            break
    if page_html is not None:
        href = _find_icon_href(page_html, page_url)
        if href:
            got = await _try_download(_client, href)
            if got:
                data, ext = got
                _save_cache(origin, data, ext)
                return data, EXT_MEDIA[ext]
        # 顺着页面里的同源入口链接找 icon(如 OpenWrt: / -> meta refresh -> /cgi-bin/luci/)
        for entry in _collect_entry_links(page_html, page_url, origin):
            sub_html = await _fetch_html(entry)
            if sub_html is None:
                continue
            href = _find_icon_href(sub_html, entry)
            if href:
                got = await _try_download(_client, href)
                if got:
                    data, ext = got
                    _save_cache(origin, data, ext)
                    return data, EXT_MEDIA[ext]

    # 3. 常见图标路径探测(覆盖 LuCI argon 主题、默认 favicon 等)
    for path in COMMON_PATHS:
        got = await _try_download(_client, origin + path)
        if got:
            data, ext = got
            _save_cache(origin, data, ext)
            return data, EXT_MEDIA[ext]

    # 4. 记录失败
    fail.write_text(str(time.time()))
    return None
