# 🧭 Navi

**个人服务导航页** —— 把家里所有 `IP:端口` 的服务收拢成一个统一入口。打开一个页面,所有服务一目了然;`/admin` 密码登录后随时增删改。

> V1.0 定版。项目仓库: [github.com/Mooloco/Navi](https://github.com/Mooloco/Navi)

## ✨ 功能特性

- **分类分组导航** — 服务按分类排列,一目了然
- **卡片/分类排序** — 编辑模式箭头排序,持久化保存
- **排序随机数机制** — 每张卡片 100~500 排序值(分类内独立),新服务自动排末尾(+5 递增);移动时自动取区间中间值,仅空间不足时才重排该分类,目标顺序不变
- **分类重命名** — 编辑模式 ✎ 一键改名,旗下服务自动跟随
- **自动图标** — 不设图标也能显示网站真实图标(httpx 静态解析,可选浏览器渲染,失败回落 🔗)
- **图标缓存管理** — 编辑弹窗一键重新抓取单个图标 / 工具栏一键清空全部图标缓存
- **管理认证** — `/admin` 密码登录(默认 `admin123`),普通页面只读
- **网页编辑** — 登录后直接增删改服务,支持新建自定义分类
- **JSON 导入/导出** — 数据随时备份迁移
- **修改密码** — 管理页一键改密
- **URL 自动补全** — 输入 `192.168.1.1:8080` 自动补 `http://`
- **持久化存储** — SQLite 实时落盘,重启不丢

## 🚀 快速安装(Ubuntu/Debian)

```bash
# 默认:图标抓取走 httpx 静态解析,零额外内存(推荐)
sudo bash install.sh

# 需要浏览器渲染抓取时(少数 SPA,额外约 400MB)
sudo bash install.sh --with-browser

# lite 分支:连浏览器代码都没有,最省资源(低配机器用)
sudo bash install.sh --branch lite

# 自定义端口
sudo bash install.sh --port 8080
```

装完访问:

```
http://<服务器IP>:8000           ← 导航页(只读)
http://<服务器IP>:8000/admin     ← 管理页(密码 admin123,请立即修改)
```

> 重复执行 `install.sh` = 拉取最新代码并重启(可用于升级)。

## 🐳 Docker 部署

### 方式一:使用 Docker Hub 现成镜像(推荐,免构建)

不用克隆代码,直接创建 `docker-compose.yml`:

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
      - ${NAVI_DATA:-./data}:/data    # 数据存宿主机指定文件夹
    restart: unless-stopped
    mem_limit: ${NAVI_MEM_LIMIT:-768m}
```

配置 `.env`(可选,默认 lite + 8000):

```ini
NAVI_BRANCH=lite   # lite(默认,无浏览器 ~150MB)/ main(含 Chromium ~1.5GB)
NAVI_BROWSER=off   # off(默认,httpx 静态抓取)/ local(进程内 Chromium)/ cdp(外部浏览器容器)
NAVI_PORT=8000
NAVI_DATA=./data   # 数据目录(宿主机文件夹,SQLite + 图标缓存)
```

启动(不加 `--build`,直接拉取现成镜像):

```bash
docker compose up -d
```

升级:

```bash
docker compose pull && docker compose up -d
```

访问 `http://<主机IP>:8000`,管理页 `/admin`(默认密码 `admin123`,请立即修改)。

> 已克隆本仓库的话也可以免构建:先 `docker compose pull` 拉取现成镜像,再 `docker compose up -d`(不触发构建)。

### 方式二:源码构建(需要改代码时)

```bash
# 1. 拉代码
git clone https://github.com/Mooloco/Navi.git && cd Navi

# 2. 配置(可选,默认 lite + 8000 端口)
cp .env.example .env   # 修改 NAVI_BRANCH / NAVI_PORT

# 3. 启动(带 --build 构建自己的镜像)
docker compose up -d --build

# 4. 访问 http://<主机IP>:8000 ,管理页 /admin(默认密码 admin123)
```

要点:

- **图标抓取默认走 httpx 静态解析**,不启动浏览器进程,内存占用可忽略
- 需要浏览器渲染时设 `NAVI_BROWSER=local`(镜像需 `NAVI_BRANCH=main`,进程内 Chromium,闲置 30s 自动回收)
- 数据持久化在 `${NAVI_DATA}`(SQLite + 图标缓存),删容器数据不丢
- `mem_limit` 给容器加了内存上限,异常时是本容器被重启,不会拖垮宿主机
- 升级:重新执行 `docker compose up -d --build`

## 🛠 手动部署

```bash
git clone https://github.com/Mooloco/Navi.git
cd Navi

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 可选:浏览器渲染抓取(默认不需要,httpx 静态解析已覆盖绝大多数站点)
.venv/bin/pip install playwright
.venv/bin/playwright install chromium --with-deps
export NAVI_BROWSER=local   # 不设则只用 httpx 静态抓取

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📁 目录结构

```
Navi/
├── app/
│   ├── main.py        # FastAPI 入口 + 路由
│   ├── auth.py        # 密码哈希 + 会话 token
│   ├── database.py    # SQLite 存取
│   ├── favicon.py     # 图标抓取(多层策略 + 缓存)
│   ├── browser.py     # Playwright 浏览器模拟(可选,默认关闭)
│   └── models.py      # 数据模型
├── static/            # 前端(原生 HTML/CSS/JS)
├── install.sh         # 一键安装脚本
├── requirements.txt
├── Dockerfile.lite    # Docker 镜像:轻量版(默认,无浏览器)
└── Dockerfile.main    # Docker 镜像:含 Chromium,可选浏览器渲染抓取
```

## 🔌 API

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| GET | / | 导航页 | - |
| GET | /admin | 管理页(前端登录) | - |
| POST | /api/admin/login | 登录,返回 token | - |
| POST | /api/admin/logout | 退出登录 | token |
| GET | /api/admin/check | 校验 token | token |
| POST | /api/admin/password | 修改密码 | token |
| GET | /api/services | 服务列表 | - |
| POST | /api/services | 新增服务 | ✅ token |
| PUT | /api/services/{id} | 修改服务 | ✅ token |
| DELETE | /api/services/{id} | 删除服务 | ✅ token |
| GET | /api/export | 导出 JSON | ✅ token |
| POST | /api/import | 导入 JSON(整体替换) | ✅ token |
| POST | /api/reorder | 保存分类/服务排序(排序随机数) | ✅ token |
| POST | /api/category/rename | 重命名分类 | ✅ token |
| GET | /api/favicon?u=URL | 图标代理(缓存) | - |
| DELETE | /api/favicon?u=URL | 清除单个服务的图标缓存 | ✅ token |
| DELETE | /api/favicon/all | 清空全部图标缓存 | ✅ token |

鉴权方式:`Authorization: Bearer <token>`

## 🌿 分支

- **main**(默认):图标抓取走 httpx 静态解析;浏览器渲染为**可选**(Playwright,按需启动,闲置 30s 回收)
- **lite**:不含浏览器代码,仅轻量静态抓取,资源占用最低

## 🗺 路线图

- [x] 分类分组导航
- [x] 自动图标抓取(多层策略 + 可选浏览器渲染)
- [x] 网页编辑 + JSON 导入/导出
- [x] 管理认证(/admin 登录、改密码)
- [x] Docker 镜像 + Compose 部署(main/lite 按分支分流)
- [ ] 在线状态检测(卡片绿点/红点)
- [ ] 搜索框
- [ ] 深色模式
- [ ] DNS 记录 + OpenResty 反向代理(统一 80 端口入口)

## ⚠️ 安全提示

- 默认密码 `admin123`,**首次登录后请立即修改**
- 当前为内网 HTTP 明文传输;若暴露公网,请务必前置 HTTPS
