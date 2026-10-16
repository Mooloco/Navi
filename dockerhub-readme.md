# 🧭 Navi

**Personal service navigation** — collect all your home services (IP:port) into one clean page. Click once, jump anywhere. Admin login at `/admin` for adding/editing services.

🔗 GitHub: https://github.com/Mooloco/Navi

## Features

- Category-grouped service cards, sortable with ↑↓ buttons (persisted)
- Sort value mechanism: each card gets a 100~500 sort value (independent per category); new services append to the end (+5 increments), moving picks the mid-value of the target gap, re-balances the category only when no space remains
- Category rename with a ✎ button in edit mode (services follow automatically)
- Auto favicon fetching (static HTML parsing by default; optional browser rendering) with icon cache management: refresh a single icon / clear all caches
- Admin auth at `/admin` (default password `admin123` — change it after first login)
- Web-based CRUD, custom categories, JSON import/export
- URL scheme auto-completion (`192.168.1.1:8080` → `http://192.168.1.1:8080`)
- SQLite persistence, survives restarts

## Tags

| Tag | Description | Size |
|---|---|---|
| `lite` | **Default.** No browser; static (httpx) favicon fetching only | ~150MB |
| `main` | Adds Playwright + Chromium for optional browser-rendered favicon fetching (enable with `NAVI_BROWSER=local`) | ~1.5GB |

Favicon fetching uses static HTML parsing by default and needs no browser process. Pick `main` only if a few of your services render their icons with JavaScript — with `NAVI_BROWSER=off` (the default) the bundled Chromium just sits idle.

## Quick Start (Docker Compose)

Clone the project (compose file included) or create your own:

```bash
git clone https://github.com/Mooloco/Navi.git && cd Navi
cp .env.example .env    # set NAVI_BRANCH / NAVI_PORT
```

`docker-compose.yml`:

```yaml
services:
  app:
    image: mooloco/navi:${NAVI_BRANCH:-lite}
    container_name: navi-app
    ports:
      - "${NAVI_PORT:-8000}:8000"
    environment:
      - MOOLO_NAV_DB=/data/nav.db
      - MOOLO_NAV_CACHE=/data/favicons
      - NAVI_BROWSER=${NAVI_BROWSER:-off}
    volumes:
      - ${NAVI_DATA:-./data}:/data    # bind mount: host folder -> /data
    restart: unless-stopped
    mem_limit: ${NAVI_MEM_LIMIT:-768m}
```

`.env`:

```ini
NAVI_BRANCH=lite   # lite (default, no browser ~150MB) | main (with Chromium ~1.5GB)
NAVI_BROWSER=off   # off (default) | local (in-process Chromium) | cdp (external browser container)
NAVI_PORT=8000
NAVI_DATA=./data   # host folder for data (SQLite + icon cache)
```

Start:

```bash
docker compose up -d
```

Access `http://<host>:8000` — admin page at `/admin` (default password `admin123`, **change it after first login**).

## Single Container (docker run)

```bash
# default: standalone, static favicon fetching, no browser needed
docker run -d --name navi-app -p 8000:8000 \
  -v navi-data:/data mooloco/navi:lite

# with browser rendering (main tag bundles Chromium; enable it via NAVI_BROWSER)
docker run -d --name navi-app -p 8000:8000 \
  -e NAVI_BROWSER=local \
  -v navi-data:/data mooloco/navi:main
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NAVI_BRANCH` | `lite` | Image variant (`lite` = no browser / `main` = bundles Chromium) |
| `NAVI_BROWSER` | `off` | Browser backend: `off` / `local` (in-process Chromium) / `cdp` |
| `NAVI_BROWSER_CDP` | (unset) | Remote Chromium CDP/Playwright endpoint, used only when `NAVI_BROWSER=cdp` |
| `NAVI_PORT` | `8000` | Host port mapping |
| `NAVI_MEM_LIMIT` | `768m` | Container memory limit |
| `MOOLO_NAV_DB` | `/data/nav.db` | SQLite database path |
| `MOOLO_NAV_CACHE` | `/data/favicons` | Favicon cache directory |

## Data Persistence

All data (service list + icon cache) lives in the `navi-data` volume at `/data`. Removing the container keeps your data — recreate with the same volume name.

## Upgrading

```bash
docker compose pull && docker compose up -d
```

## Security Note

- Default admin password is `admin123` — **change it immediately** via the 🔑 button on the admin page.
- Designed for LAN use over HTTP; put it behind HTTPS if exposed to the public internet.
