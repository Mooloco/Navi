# =============================================================
#  Navi 镜像 (V3.0)
#
#  单镜像:图标抓取走 httpx 静态解析(解析 <link rel="icon"> 声明 +
#  常见路径探测 + 同源入口链接追踪),零额外浏览器进程/内存。
#
#  历史:V2.x 曾内置 Playwright + Chromium 做可选的浏览器渲染抓取。
#  实测对绝大多数站点一个图标都没多抓到,却引入了一条 Playwright
#  driver 泄漏路径(连接失败时每请求泄漏一个 node 进程,数十次吃满
#  宿主机内存)。V3.0 起彻底移除浏览器依赖。
# =============================================================
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

ENV MOOLO_NAV_DB=/data/nav.db \
    MOOLO_NAV_CACHE=/data/favicons

VOLUME /data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
