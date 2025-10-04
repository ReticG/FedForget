#\!/bin/bash
# FedForget 开发启动脚本
# 用法: bash START_DEV.sh

cd ~/work/GJC/fedforget

echo "==================================="
echo "FedForget 开发环境"
echo "==================================="
echo "工作目录: $(pwd)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo ""
echo "📋 当前任务（查看 MEMORY.md）:"
cat MEMORY.md | grep -A 10 "⏳ 待办事项" | head -15
echo ""
echo "🚀 开始开发..."
echo ""
echo "现在你可以："
echo "1. 编辑代码: vim/nano src/xxx.py"
echo "2. 运行脚本: python scripts/xxx.py"  
echo "3. 查看记忆: cat MEMORY.md"
echo "4. 更新记忆: vim MEMORY.md"
echo ""
echo "提示: 我（Claude）已经准备好了实现计划"
echo "你可以让我开始自动实现，或者手动编码"
echo ""

# 保持shell开启
exec /bin/bash
