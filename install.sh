#!/usr/bin/env bash
# =============================================================
#  Navi 安装脚本 (V1.0)
#  个人服务导航页 - https://github.com/Mooloco/Navi
#
#  用法:
#    sudo bash install.sh                  # 安装 main 分支(默认,含浏览器图标抓取)
#    sudo bash install.sh --branch lite    # 安装 lite 分支(无浏览器,更省资源)
#    sudo bash install.sh --port 8080      # 自定义端口
#    sudo bash install.sh --dir /srv/navi  # 自定义安装目录
#
#  重复执行 = 拉取最新代码并重启服务(幂等,可用于升级)
# =============================================================
set -euo pipefail

REPO_URL="https://github.com/Mooloco/Navi.git"
BRANCH="main"
PORT="8000"
INSTALL_DIR="/opt/navi"
SERVICE="navi"

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)  BRANCH="$2"; shift 2 ;;
    --port)    PORT="$2";   shift 2 ;;
    --dir)     INSTALL_DIR="$2"; shift 2 ;;
    --service) SERVICE="$2"; shift 2 ;;
    -h|--help)
      echo "用法: sudo bash install.sh [--branch main|lite] [--port 8000] [--dir /opt/navi]"
      exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [[ "$BRANCH" != "main" && "$BRANCH" != "lite" ]]; then
  echo "错误: --branch 只支持 main 或 lite"; exit 1
fi

# ---------- 前置检查 ----------
[[ $EUID -eq 0 ]] || { echo "请用 root 或 sudo 运行本脚本"; exit 1; }
command -v python3 >/dev/null || { echo "错误: 缺少 python3"; exit 1; }
command -v git     >/dev/null || { echo "错误: 缺少 git"; exit 1; }
command -v systemctl >/dev/null || { echo "错误: 缺少 systemd(systemctl)"; exit 1; }

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=${PY_VERSION%%.*}
PY_MINOR=${PY_VERSION#*.}
if (( PY_MAJOR < 3 )) || { (( PY_MAJOR == 3 )) && (( PY_MINOR < 10 )); }; then
  echo "错误: 需要 Python 3.10+,当前 $PY_VERSION"; exit 1
fi

echo "==> Navi 安装开始 (分支: $BRANCH, 端口: $PORT, 目录: $INSTALL_DIR)"

# ---------- 拉取代码 ----------
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "==> 检测到已有安装,更新代码..."
  cd "$INSTALL_DIR"
  git fetch origin
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout "$BRANCH"
  else
    git checkout -b "$BRANCH" "origin/$BRANCH"
  fi
  git pull --ff-only origin "$BRANCH"
else
  echo "==> 克隆仓库 (分支: $BRANCH)..."
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ---------- Python 环境 ----------
echo "==> 创建 Python 虚拟环境..."
if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
  python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install -q --upgrade pip
echo "==> 安装 Python 依赖..."
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

if [[ "$BRANCH" == "main" ]]; then
  echo "==> 安装 Playwright + Chromium(main 分支浏览器图标抓取需要,首次约 1 分钟)..."
  "$INSTALL_DIR/.venv/bin/pip" install -q playwright
  if ! "$INSTALL_DIR/.venv/bin/playwright" install chromium --with-deps 2>/dev/null; then
    echo "==> Chromium 系统依赖安装失败,尝试不带 --with-deps 重试..."
    "$INSTALL_DIR/.venv/bin/playwright" install chromium
  fi
fi

# ---------- systemd 服务 ----------
echo "==> 配置 systemd 服务 ($SERVICE)..."
cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Navi - personal service navigation
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
Environment=MOOLO_NAV_DB=$INSTALL_DIR/data/nav.db
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1
systemctl restart "$SERVICE"

# ---------- 等待就绪 ----------
echo "==> 等待服务启动..."
for i in $(seq 1 30); do
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/"; then
    break
  fi
  sleep 1
  if [[ $i == 30 ]]; then
    echo "错误: 服务未能在 30 秒内启动,查看日志: journalctl -u $SERVICE -n 50"
    exit 1
  fi
done

# ---------- 完成 ----------
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "=============================================="
echo "  ✅ Navi 安装完成!"
echo "----------------------------------------------"
echo "  导航页:   http://${IP:-<本机IP>}:$PORT"
echo "  管理页:   http://${IP:-<本机IP>}:$PORT/admin"
echo "  默认密码: admin123 (请登录后立即修改!)"
echo "----------------------------------------------"
echo "  常用命令:"
echo "    systemctl status $SERVICE    查看状态"
echo "    systemctl restart $SERVICE   重启服务"
echo "    journalctl -u $SERVICE -f    实时日志"
echo "=============================================="
