# 🧭 Navi

**Personal service navigation** — collect all your home services (IP:port) into one clean page. Click once, jump anywhere. Admin login at `/admin` for adding/editing services.

🔗 GitHub: https://github.com/Mooloco/Navi

## Features

- Category-grouped service cards, sortable with ↑↓ buttons (persisted)
- Sort value mechanism: each card gets a 10~200 sort value (independent per category); moving picks the mid-value of the target gap, auto re-balances the category when no integer space remains
- Auto favicon fetching (browser-based in `main` mode) with icon cache management: refresh a single icon / clear all caches
- Admin auth at `/admin` (default password `admin123` — change it after first login)
- Web-based CRUD, custom categories, JSON import/export
- URL scheme auto-completion (`192.168.1.1:8080` → `http://192.168.1.1:8080`)
- SQLite persistence, survives restarts

## Tags

| Tag | Description | Size |
|---|---|---|
| `main` | Full features: browser-based favicon fetching via a separate `browserless/chrome` container (CDP) | ~442MB |
| `lite` | Lightweight: no browser, regex-based favicon fetching only | ~246MB |

The app image never bundles a browser kernel — in `main` mode it talks to the `browserless/chrome` container over CDP. Pick `lite` for low-resource machines.

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
    image: mooloco/navi:${NAVI_BRANCH:-main}
    container_name: navi-app
    ports:
      - "${NAVI_PORT:-8000}:8000"
    environment:
      - MOOLO_NAV_DB=/data/nav.db
      - MOOLO_NAV_CACHE=/data/favicons
      - NAVI_BROWSER_CDP=ws://browser:3000
    volumes:
      - ${NAVI_DATA:-./data}:/data    # bind mount: host folder -> /data
    restart: unless-stopped

  browser:
    image: browserless/chrome:latest
    container_name: navi-browser
    restart: unless-stopped
    profiles: ["main"]      # deployed only in main mode
```

`.env`:

```ini
NAVI_BRANCH=main   # main (full) | lite (lightweight, no browser)
NAVI_PORT=8000
NAVI_DATA=./data   # host folder for data (SQLite + icon cache)
```

Start:

```bash
# main mode: app + browser containers, full icon fetching
docker compose --profile main up -d

# lite mode: app only, no browser container deployed
docker compose --profile lite up -d
```

Access `http://<host>:8000` — admin page at `/admin` (default password `admin123`, **change it after first login**).

## Single Container (docker run)

```bash
# main (for full icon fetching, point NAVI_BROWSER_CDP at your own Chromium service)
docker run -d --name navi-app -p 8000:8000 \
  -e NAVI_BROWSER_CDP=ws://browser:3000 \
  -v navi-data:/data mooloco/navi:main

# lite (standalone, no browser needed)
docker run -d --name navi-app -p 8000:8000 \
  -v navi-data:/data mooloco/navi:lite
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NAVI_BRANCH` | `main` | Compose deployment mode (`main`/`lite`) |
| `NAVI_PORT` | `8000` | Host port mapping |
| `MOOLO_NAV_DB` | `/data/nav.db` | SQLite database path |
| `MOOLO_NAV_CACHE` | `/data/favicons` | Favicon cache directory |
| `NAVI_BROWSER_CDP` | `ws://browser:3000` | Remote Chromium CDP endpoint (main mode only) |

## Data Persistence

All data (service list + icon cache) lives in the `navi-data` volume at `/data`. Removing the container keeps your data — recreate with the same volume name.

## Upgrading

```bash
docker compose --profile ${NAVI_BRANCH:-main} up -d --pull always
```

## Security Note

- Default admin password is `admin123` — **change it immediately** via the 🔑 button on the admin page.
- Designed for LAN use over HTTP; put it behind HTTPS if exposed to the public internet.
