# 🧭 Navi

**个人服务导航页** —— 把家里所有 `IP:端口` 的服务收拢成一个统一入口。打开一个页面,所有服务一目了然;`/admin` 密码登录后随时增删改。

> **V3.0 定版**。项目仓库: [github.com/Mooloco/Navi](https://github.com/Mooloco/Navi)
> Docker Hub: [`mooloco/navi`](https://hub.docker.com/r/mooloco/navi)

## ✨ 功能特性

- **分类分组导航** — 服务按分类排列,一目了然
- **卡片/分类排序** — 编辑模式箭头排序,持久化保存
- **排序随机数机制** — 每张卡片 100~500 排序值(分类内独立),新服务自动排末尾(+5 递增);移动时自动取区间中间值,仅空间不足时才重排该分类,目标顺序不变
- **分类重命名** — 编辑模式 ✎ 一键改名,旗下服务自动跟随
- **自动图标** — 不设图标也能显示网站真实图标(httpx 静态解析,失败回落 🔗)
- **图标缓存管理** — 编辑弹窗一键重新抓取单个图标 / 工具栏一键清空全部图标缓存
- **管理认证** — `/admin` 密码登录(默认 `admin123`),普通页面只读
- **网页编辑** — 登录后直接增删改服务,支持新建自定义分类
- **JSON 导入/导出** — 数据随时备份迁移
- **修改密码** — 管理页一键改密
- **URL 自动补全** — 输入 `192.168.1.1:8080` 自动补 `http://`
- **PWA** — 可添加到手机主屏,像原生 App 一样打开
- **持久化存储** — SQLite 实时落盘,重启不丢

## 🎨 图标是怎么抓的

纯 `httpx` 静态解析,零浏览器进程、零额外内存。单个图标的获取顺序:

1. **磁盘缓存命中** —— 按 `origin`(协议+主机+端口)做 key,一个域名一个图标
2. **失败缓存** —— 1 小时内不再重试,失败站点直接回落 🔗,不空转
3. **抓页面 HTML**,解析 `<link rel="icon">` 声明
   - 优先级按浏览器规则:普通 icon / shortcut icon 在前,`apple-touch-icon` 垫底,同 `rel` 取更小尺寸
   - 页面里没有?自动顺着**同源入口链接**(`meta refresh` / `<a href>` / `<iframe>`)再抓一层 —— 专治 OpenWrt/LuCI 那种 `/` 只是跳板、真图标在 `/cgi-bin/luci/` 的情况
4. **兜底探测常见路径** —— `/favicon.ico`、`/favicon.png`、`/apple-touch-icon.png`、`/static/favicon.ico`、`/icons/favicon.ico`,以及 3 条 LuCI argon 主题路径
5. 全部失败 → 写入失败标记,1 小时内秒回 404(前端显示 🔗)

> **为什么不用无头浏览器**:V2.x 曾内置 Playwright + Chromium 做可选渲染抓取,实测对绝大多数站点**一个图标都没多抓到**,却引入了一条 driver 泄漏路径(连接失败时每请求泄漏一个 node 进程,数十次就吃满宿主机内存)。V3.0 起彻底移除,只保留 httpx 静态解析。

## 🚀 快速安装(Ubuntu/Debian)

```bash
# 默认安装(图标抓取走 httpx 静态解析,零额外内存)
sudo bash install.sh

# 自定义端口
sudo bash install.sh --port 8080

# 自定义安装目录
sudo bash install.sh --dir /srv/navi
```

装完访问:

```
http://<服务器IP>:8000           ← 导航页(只读)
http://<服务器IP>:8000/admin     ← 管理页(密码 admin123,请立即修改)
```

> 重复执行 `install.sh` = 拉取最新代码并重启(可用于升级)。

## 🐳 Docker 部署

单镜像,无浏览器依赖,空闲内存几十 MB。

### 方式一:使用 Docker Hub 现成镜像(推荐,免构建)

不用克隆代码,直接创建 `docker-compose.yml`:

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
      - ${NAVI_DATA:-./data}:/data    # 数据存宿主机指定文件夹
    restart: unless-stopped
    mem_limit: ${NAVI_MEM_LIMIT:-256m}
```

配置 `.env`(可选,默认 `latest` + 8000):

```ini
NAVI_TAG=latest    # latest(最新定版)/ 3.0(固定版本号)
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

# 2. 配置(可选)
cp .env.example .env   # 修改 NAVI_PORT 等

# 3. 启动(带 --build 构建自己的镜像)
docker compose up -d --build

# 4. 访问 http://<主机IP>:8000 ,管理页 /admin(默认密码 admin123)
```

要点:

- **图标抓取纯 httpx 静态解析**,不启动任何浏览器进程,内存占用可忽略
- 数据持久化在 `${NAVI_DATA}`(SQLite + 图标缓存),删容器数据不丢
- `mem_limit` 给容器加了内存上限,异常时是本容器被重启,不会拖垮宿主机
- 升级:重新执行 `docker compose up -d --build`

## 🛠 手动部署

```bash
git clone https://github.com/Mooloco/Navi.git
cd Navi

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

依赖只有三个:`fastapi`、`uvicorn`、`httpx` —— 没有 `playwright`,也不需要下载 Chromium。

## 📁 目录结构

```
Navi/
├── app/
│   ├── main.py        # FastAPI 入口 + 路由
│   ├── auth.py        # 密码哈希 + 会话 token
│   ├── database.py    # SQLite 存取
│   ├── favicon.py     # 图标抓取(多层策略 + 缓存)
│   └── models.py      # 数据模型
├── static/            # 前端(原生 HTML/CSS/JS)+ PWA(sw.js / manifest / 图标)
├── deploy/            # Caddy HTTPS 反代配置(可选)
├── install.sh         # 一键安装脚本
├── requirements.txt
└── Dockerfile         # 单镜像(无浏览器)
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

## 🗺 路线图

- [x] 分类分组导航
- [x] 自动图标抓取(httpx 静态解析 + 缓存)
- [x] 网页编辑 + JSON 导入/导出
- [x] 管理认证(/admin 登录、改密码)
- [x] Docker 单镜像 + Compose 部署
- [x] PWA(可安装到主屏)
- [ ] 在线状态检测(卡片绿点/红点)
- [ ] 搜索框
- [ ] 深色模式
- [ ] DNS 记录 + OpenResty 反向代理(统一 80 端口入口)

## 📜 版本

- **V3.0**(当前)—— 移除浏览器依赖,单镜像;图标抓取纯 httpx 静态解析
- V2.x —— 可选 Playwright + Chromium 浏览器渲染抓取(已废弃:零收益 + 内存泄漏)
- V1.0 —— 首个定版

## ⚠️ 安全提示

- 默认密码 `admin123`,**首次登录后请立即修改**
- 当前为内网 HTTP 明文传输;若暴露公网,请务必前置 HTTPS(可参考 `deploy/` 里的 Caddy 配置)
