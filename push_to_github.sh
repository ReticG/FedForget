#!/bin/bash

# FedForget GitHub推送脚本
# 使用方法: ./push_to_github.sh <YOUR_GITHUB_TOKEN>

echo "======================================"
echo "FedForget GitHub 推送脚本"
echo "======================================"
echo ""

# 检查是否提供了token
if [ -z "$1" ]; then
    echo "❌ 错误: 需要提供GitHub Personal Access Token"
    echo ""
    echo "使用方法:"
    echo "  ./push_to_github.sh <YOUR_TOKEN>"
    echo ""
    echo "获取Token:"
    echo "  1. 访问: https://github.com/settings/tokens"
    echo "  2. 点击 'Generate new token (classic)'"
    echo "  3. 选择权限: ✅ repo"
    echo "  4. 生成并复制token"
    echo "  5. 运行: ./push_to_github.sh <粘贴token>"
    echo ""
    exit 1
fi

TOKEN="$1"

echo "📊 检查Git状态..."
git status

echo ""
echo "📝 查看待推送的commits..."
git log --oneline origin/main..HEAD 2>/dev/null || git log --oneline -17

echo ""
echo "🔑 配置临时凭证..."
# 临时配置使用token的URL
git remote set-url origin "https://ReticG:${TOKEN}@github.com/ReticG/FedForget.git"

echo ""
echo "🚀 推送到GitHub..."
if git push origin main; then
    echo ""
    echo "✅ 推送成功!"
    echo ""
    echo "🔗 查看仓库: https://github.com/ReticG/FedForget"
    echo ""
    echo "📊 推送统计:"
    git log --oneline -1
    echo ""

    # 恢复为HTTPS URL (不包含token)
    echo "🔒 清理凭证..."
    git remote set-url origin "https://github.com/ReticG/FedForget.git"

    echo ""
    echo "✅ 全部完成!"
    echo ""
    echo "下一步:"
    echo "  1. 访问 https://github.com/ReticG/FedForget 验证"
    echo "  2. 开始LaTeX转换和PDF编译"
    echo "  3. 准备论文提交!"
    echo ""
else
    echo ""
    echo "❌ 推送失败!"
    echo ""
    echo "可能的原因:"
    echo "  1. Token无效或过期"
    echo "  2. Token权限不足 (需要'repo'权限)"
    echo "  3. 网络连接问题"
    echo "  4. 仓库访问权限问题"
    echo ""
    echo "请检查并重试。"
    echo ""

    # 恢复为HTTPS URL
    git remote set-url origin "https://github.com/ReticG/FedForget.git"
    exit 1
fi
