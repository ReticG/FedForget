#!/bin/bash

# FedForget 实验监控脚本
# 用法: ./monitor_experiments.sh 或 watch -n 30 ./monitor_experiments.sh

clear
echo "=========================================="
echo "FedForget 实验进度监控"
echo "更新时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查运行中的实验进程
echo "🔄 运行中的实验:"
echo ""
RUNNING_EXPERIMENTS=$(ps aux | grep -E "python.*scripts/(ablation|reproducibility|compare_10clients|shadow_model)" | grep -v grep)

if [ -z "$RUNNING_EXPERIMENTS" ]; then
    echo "  ℹ️  当前无实验运行"
else
    echo "$RUNNING_EXPERIMENTS" | awk '{printf "  [PID %s] %s (CPU: %s%%, MEM: %s%%)\n", $2, $13, $3, $4}'
fi

echo ""
echo "=========================================="
echo "📊 实验日志 (最后10行)"
echo "=========================================="

# 消融实验日志
if [ -f logs/ablation_rerun.log ]; then
    echo ""
    echo "消融实验 (ablation_rerun.log):"
    tail -10 logs/ablation_rerun.log | grep -E "运行变体|遗忘:.*%|预训练:.*%" | tail -3
fi

# 可复现性验证日志
if [ -f logs/reproducibility.log ]; then
    echo ""
    echo "可复现性验证 (reproducibility.log):"
    tail -10 logs/reproducibility.log | grep -E "Seed|方法|预训练:.*%|遗忘:.*%" | tail -3
fi

# 10客户端实验日志
if [ -f logs/compare_10clients.log ]; then
    echo ""
    echo "10客户端实验 (compare_10clients.log):"
    tail -10 logs/compare_10clients.log | grep -E "方法|预训练:.*%|遗忘:.*%" | tail -3
fi

echo ""
echo "=========================================="
echo "📁 生成的结果文件"
echo "=========================================="

# 检查结果文件
echo ""
if [ -d results ]; then
    echo "最近生成的结果文件 (最近5个):"
    ls -lht results/*.csv 2>/dev/null | head -5 | awk '{printf "  %s  %s  %s\n", $9, $5, $6" "$7" "$8}'

    if [ ! -f results/*.csv 2>/dev/null ]; then
        echo "  ℹ️  暂无新结果文件"
    fi
else
    echo "  ⚠️  results目录不存在"
fi

echo ""
echo "=========================================="
echo "💾 磁盘使用"
echo "=========================================="
echo ""
df -h /home/featurize/work/GJC/fedforget | awk 'NR==2 {printf "  使用: %s / %s (已用 %s)\n", $3, $2, $5}'

echo ""
echo "=========================================="
echo "⏰ 预计完成时间"
echo "=========================================="
echo ""

# 根据日志推测进度
if [ -f logs/ablation_rerun.log ]; then
    ABLATION_PROGRESS=$(tail -20 logs/ablation_rerun.log | grep -o "[0-9]*%" | tail -1)
    if [ ! -z "$ABLATION_PROGRESS" ]; then
        echo "  消融实验: $ABLATION_PROGRESS (预计4-5小时)"
    fi
fi

if [ -f logs/reproducibility.log ]; then
    REPRO_PROGRESS=$(tail -20 logs/reproducibility.log | grep -o "[0-9]*%" | tail -1)
    if [ ! -z "$REPRO_PROGRESS" ]; then
        echo "  可复现性: $REPRO_PROGRESS (预计3-4小时)"
    fi
fi

echo ""
echo "=========================================="
echo "📝 快速操作"
echo "=========================================="
echo ""
echo "  查看完整日志:"
echo "    tail -f logs/ablation_rerun.log"
echo "    tail -f logs/reproducibility.log"
echo ""
echo "  停止实验:"
echo "    pkill -f 'python.*ablation'"
echo "    pkill -f 'python.*reproducibility'"
echo ""
echo "  查看结果:"
echo "    cat results/ablation_study.csv"
echo "    cat results/reproducibility_5clients.csv"
echo ""
echo "=========================================="
