# Navi

个人服务导航页:把家里所有 IP:端口 服务收拢成一个统一入口。(项目目录名沿用例: moolo-nav)

## 技术栈

- 后端:FastAPI + SQLite(数据文件 `data/nav.db`,可用环境变量 `MOOLO_NAV_DB` 覆盖)
- 前端:原生 HTML/CSS/JS,零框架

## 开发运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | 导航页 |
| GET | /api/services | 服务列表 |
| POST | /api/services | 新增服务 |
| PUT | /api/services/{id} | 修改服务(部分字段) |
| DELETE | /api/services/{id} | 删除服务 |
| GET | /api/export | 导出全部服务(JSON 下载) |
| POST | /api/import | 导入服务清单(整体替换) |

## Docker

```bash
docker build -t moolo/nav .
docker run -d --name moolo-nav -p 8000:8000 -v nav-data:/data moolo/nav
```

## 路线图

- [x] 分类分组导航
- [x] 网页编辑 + JSON 导出/导入
- [ ] 在线状态检测(GET /api/health 已预留)
- [ ] 搜索框
- [ ] 深色模式
- [ ] PDC 上加 DNS 记录(nav.moolo.net)
- [ ] OpenResty/nginx 反向代理,统一 80 端口入口
