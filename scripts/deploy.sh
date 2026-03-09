#!/bin/bash
# 体育预测系统 - 数据更新 + 部署脚本
# 每天 3:00 运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/sports-dashboard-deploy.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始部署..." >> "$LOG_FILE"

cd "$PROJECT_DIR"

# 1. 生成最新数据
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 生成数据..." >> "$LOG_FILE"
python3 scripts/generate_data.py >> "$LOG_FILE" 2>&1

# 2. Git 提交
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 提交更改..." >> "$LOG_FILE"
git add data/
git commit -m "chore: auto update data $(date '+%Y-%m-%d')" || echo "无更改" >> "$LOG_FILE"

# 3. 推送到 GitHub
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 推送..." >> "$LOG_FILE"
git push origin gh-pages >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 部署完成！" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
