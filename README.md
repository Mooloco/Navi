# 🧭 Navi

**个人服务导航页** —— 把家里所有 `IP:端口` 的服务收拢成一个统一入口。打开一个页面,所有服务一目了然;`/admin` 密码登录后随时增删改。

> V1.0 定版。项目仓库: [github.com/Mooloco/Navi](https://github.com/Mooloco/Navi)

## ✨ 功能特性

- **分类分组导航** — 服务按分类排列,一目了然
- **卡片/分类排序** — 编辑模式箭头排序,持久化保存
- **排序随机数机制** — 每张卡片 100~500 排序值(分类内独立),新服务自动排末尾(+5 递增);移动时自动取区间中间值,仅空间不足时才重排该分类,目标顺序不变
- **分类重命名** — 编辑模式 ✎ 一键改名,旗下服务自动跟随
- **自动图标** — 不设图标也能显示网站真实图标(浏览器模拟抓取,失败回落 🔗)
- **图标缓存管理** — 编辑弹窗一键重新抓取单个图标 / 工具栏一键清空全部图标缓存
- **管理认证** — `/admin` 密码登录(默认 `admin123`),普通页面只读
- **网页编辑** — 登录后直接增删改服务,支持新建自定义分类
- **JSON 导入/导出** — 数据随时备份迁移
- **修改密码** — 管理页一键改密
- **URL 自动补全** — 输入 `192.168.1.1:8080` 自动补 `http://`
- **持久化存储** — SQLite 实时落盘,重启不丢

## 🚀 快速安装(Ubuntu/Debian)

```bash
# main 分支(推荐):含浏览器图标抓取,首次安装约 1~2 分钟
sudo bash install.sh

# lite 分支:无浏览器,更省资源(低配机器用)
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
    image: mooloco/navi:${NAVI_BRANCH:-main}
    container_name: navi-app
    ports:
      - "${NAVI_PORT:-8000}:8000"
    environment:
      - MOOLO_NAV_DB=/data/nav.db
      - MOOLO_NAV_CACHE=/data/favicons
      - NAVI_BROWSER_CDP=ws://browser:3000
    volumes:
      - ${NAVI_DATA:-./data}:/data    # 数据存宿主机指定文件夹
    restart: unless-stopped

  browser:
    image: browserless/chrome:latest
    container_name: navi-browser
    restart: unless-stopped
    profiles: ["main"]      # 仅 main 模式部署
```

配置 `.env`(可选,默认 main + 8000):

```ini
NAVI_BRANCH=main   # main(完整)/ lite(轻量,无浏览器)
NAVI_PORT=8000
NAVI_DATA=./data   # 数据目录(宿主机文件夹,SQLite + 图标缓存)
```

启动(不加 `--build`,直接拉取现成镜像):

```bash
docker compose --profile main up -d    # main 完整版(应用 + 浏览器容器)
docker compose --profile lite up -d    # lite 轻量版(仅应用容器)
```

升级:

```bash
docker compose --profile ${NAVI_BRANCH:-main} up -d --pull always
```

访问 `http://<主机IP>:8000`,管理页 `/admin`(默认密码 `admin123`,请立即修改)。

> 已克隆本仓库的话也可以免构建:先 `docker compose --profile main pull` 拉取现成镜像,再 `docker compose --profile main up -d`(不触发构建)。

### 方式二:源码构建(需要改代码时)

```bash
# 1. 拉代码
git clone https://github.com/Mooloco/Navi.git && cd Navi

# 2. 配置(可选,默认 main + 8000 端口)
cp .env.example .env   # 修改 NAVI_BRANCH / NAVI_PORT

# 3. 启动(带 --build 构建自己的镜像)
docker compose --profile main up -d --build    # 或 --profile lite

# 4. 访问 http://<主机IP>:8000 ,管理页 /admin(默认密码 admin123)
```

要点:

- 一个 `.env` 变量 `NAVI_BRANCH` 决定部署形态:main 带浏览器容器,lite 不部署浏览器容器
- 数据持久化在数据卷 `navi-data`(SQLite + 图标缓存),删容器数据不丢
- main 模式应用镜像**不含浏览器内核**(~442MB),浏览器功能由独立 `browserless/chrome` 容器经 CDP 提供,可独立升级
- 升级:重新执行 `docker compose --profile <分支> up -d --build`

## 🛠 手动部署

```bash
git clone https://github.com/Mooloco/Navi.git
cd Navi

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# main 分支额外需要浏览器(图标抓取):
.venv/bin/pip install playwright
.venv/bin/playwright install chromium --with-deps

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
│   ├── browser.py     # Playwright 浏览器模拟(main 分支)
│   └── models.py      # 数据模型
├── static/            # 前端(原生 HTML/CSS/JS)
├── install.sh         # 一键安装脚本
├── requirements.txt
└── Dockerfile         # Docker 版(规划中)
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

- **main**(推荐):浏览器模拟图标抓取(Playwright,按需启动,闲置 30s 自动回收)
- **lite**:无浏览器,仅轻量正则抓取,资源占用最低

## 🗺 路线图

- [x] 分类分组导航
- [x] 自动图标抓取(多层策略 + 浏览器模拟)
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
