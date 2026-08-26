from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import auth, browser, database, favicon
from .models import AdminLogin, AdminPassword, ServiceCreate, ServiceUpdate

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    auth.ensure_default_password()
    await browser.startup()  # 挂 watchdog,按需拉起/闲置回收浏览器
    await favicon.startup()
    yield
    await favicon.shutdown()
    await browser.shutdown()


app = FastAPI(title="Navi", version="0.1.0", lifespan=lifespan)


def require_admin(authorization: str | None = Header(None)):
    if not auth.check_token(auth.extract_bearer(authorization)):
        raise HTTPException(401, "未授权,请先登录管理页面")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(STATIC_DIR / "index.html")


# ---------- 管理认证 ----------

@app.post("/api/admin/login")
def admin_login(payload: AdminLogin):
    stored = database.get_setting("password_hash")
    if stored is None or not auth.verify_password(payload.password, stored):
        raise HTTPException(401, "密码错误")
    return {"token": auth.create_token()}


@app.post("/api/admin/logout")
def admin_logout(authorization: str | None = Header(None)):
    auth.revoke_token(auth.extract_bearer(authorization))
    return {"ok": True}


@app.get("/api/admin/check")
def admin_check(_: None = Depends(require_admin)):
    return {"ok": True}


@app.post("/api/admin/password")
def admin_password(payload: AdminPassword, _: None = Depends(require_admin)):
    if not auth.change_password(payload.old_password, payload.new_password):
        raise HTTPException(401, "旧密码错误")
    return {"ok": True}


# ---------- 服务管理(写操作需登录) ----------

@app.get("/api/services")
def list_services():
    return database.list_services()


@app.post("/api/services", status_code=201, dependencies=[Depends(require_admin)])
def create_service(payload: ServiceCreate):
    return database.add_service(payload.model_dump())


@app.put("/api/services/{sid}", dependencies=[Depends(require_admin)])
def update_service(sid: int, payload: ServiceUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    svc = database.update_service(sid, data)
    if svc is None:
        raise HTTPException(404, "服务不存在")
    return svc


@app.delete("/api/services/{sid}", status_code=204, dependencies=[Depends(require_admin)])
def delete_service(sid: int):
    if not database.delete_service(sid):
        raise HTTPException(404, "服务不存在")


@app.get("/api/export", dependencies=[Depends(require_admin)])
def export_services():
    return JSONResponse(
        database.list_services(),
        headers={"Content-Disposition": 'attachment; filename="services.json"'},
    )


@app.post("/api/import", dependencies=[Depends(require_admin)])
def import_services(payload: list[ServiceCreate]):
    items = [s.model_dump() for s in payload]
    n = database.replace_all(items)
    return {"imported": n}


# ---------- 图标代理(公开) ----------

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
