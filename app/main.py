from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import browser, database, favicon
from .models import ServiceCreate, ServiceUpdate

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    await favicon.startup()
    await browser.startup()
    yield
    await browser.shutdown()
    await favicon.shutdown()


app = FastAPI(title="Navi", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/services")
def list_services():
    return database.list_services()


@app.post("/api/services", status_code=201)
def create_service(payload: ServiceCreate):
    return database.add_service(payload.model_dump())


@app.put("/api/services/{sid}")
def update_service(sid: int, payload: ServiceUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    svc = database.update_service(sid, data)
    if svc is None:
        raise HTTPException(404, "服务不存在")
    return svc


@app.delete("/api/services/{sid}", status_code=204)
def delete_service(sid: int):
    if not database.delete_service(sid):
        raise HTTPException(404, "服务不存在")


@app.get("/api/export")
def export_services():
    return JSONResponse(
        database.list_services(),
        headers={"Content-Disposition": 'attachment; filename="services.json"'},
    )


@app.post("/api/import")
def import_services(payload: list[ServiceCreate]):
    items = [s.model_dump() for s in payload]
    n = database.replace_all(items)
    return {"imported": n}


@app.get("/api/favicon")
async def favicon_api(u: str):
    """favicon 代理:解析 HTML icon 声明/默认路径抓取,磁盘缓存,失败 404。"""
    result = await favicon.fetch_favicon(u)
    if result is None:
        raise HTTPException(404, "favicon not found")
    data, media_type = result
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
