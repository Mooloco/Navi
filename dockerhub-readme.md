# 🧭 Navi

**Personal service navigation** — collect all your home services (IP:port) into one clean page. Click once, jump anywhere. Admin login at `/admin` for adding/editing services.

🔗 GitHub: https://github.com/Mooloco/Navi

## Features

- Category-grouped service cards, sortable with ↑↓ buttons (persisted)
- Sort value mechanism: each card gets a 100~500 sort value (independent per category); new services append to the end (+5 increments), moving picks the mid-value of the target gap, re-balances the category only when no space remains
- Category rename with a ✎ button in edit mode (services follow automatically)
- Auto favicon fetching (httpx static parsing — no browser process) with icon cache management: refresh a single icon / clear all caches
- Admin auth at `/admin` (default password `admin123` — change it after first login)
- Web-based CRUD, custom categories, JSON import/export
- URL scheme auto-completion (`192.168.1.1:8080` → `http://192.168.1.1:8080`)
- SQLite persistence, survives restarts

## Tags

| Tag | Description |
|---|---|
| `latest` | **Newest release.** Currently V3.0 |
| `3.0` | Pinned V3.0 |

Single image, no variants. Favicon fetching is done purely with `httpx` static parsing — there is no bundled Chromium and no browser container to run. Idle memory is a few dozen MB.

## Quick Start (Docker Compose)

Clone the project (compose file included) or create your own:

```bash
git clone https://github.com/Mooloco/Navi.git && cd Navi
cp .env.example .env    # set NAVI_PORT if needed
```

`docker-compose.yml`:

```yaml
services:
  app:
    image: mooloco/navi:${NAVI_TAG:-latest}
    container_name: navi-app
    ports:
      - "${NAVI_PORT:-8000}:8000"
    environment:
      - MOOLO_NAV_DB=/data/nav.db
      - MOOLO_NAV_CACHE=/data/favicons
    volumes:
      - ${NAVI_DATA:-./data}:/data    # bind mount: host folder -> /data
    restart: unless-stopped
    mem_limit: ${NAVI_MEM_LIMIT:-256m}
```

`.env`:

```ini
NAVI_TAG=latest    # latest | 3.0
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
docker run -d --name navi-app -p 8000:8000 \
  -v navi-data:/data mooloco/navi:latest
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NAVI_TAG` | `latest` | Image tag to pull (`latest` / `3.0`) |
| `NAVI_PORT` | `8000` | Host port mapping |
| `NAVI_MEM_LIMIT` | `256m` | Container memory limit |
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
