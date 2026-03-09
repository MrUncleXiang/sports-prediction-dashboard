#!/bin/bash
# 从数据库导出最新数据并部署到 GitHub Pages

set -e  # 遇到错误立即退出

echo "🚀 开始数据导出和部署..."

cd /home/zcx/.openclaw/workspace/phase2_website

# 1. 从数据库生成最新数据
echo "📊 生成数据文件..."
python3 data/generate_data.py

# 2. 检查是否有变更
if git diff --quiet data/*.json; then
    echo "ℹ️  数据无变更，跳过提交"
else
    # 3. 提交变更
    echo "💾 提交变更..."
    git add data/*.json
    git commit -m "data: 自动更新 $(date +%Y-%m-%d)"
    
    # 4. 推送到 GitHub
    echo "📤 推送到 GitHub Pages..."
    git push origin gh-pages
    
    echo "✅ 部署完成！"
fi
