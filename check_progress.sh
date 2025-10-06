#!/bin/bash

# FedForget 实验快速进度检查

echo "=========================================="
echo "FedForget 实验进度 ($(date '+%H:%M:%S'))"
echo "=========================================="
echo ""

# 检查运行中的进程
echo "🔄 运行中的实验:"
RUNNING=$(ps aux | grep -E "python.*scripts/(ablation|reproducibility)" | grep -v grep)
if [ -z "$RUNNING" ]; then
    echo "  ❌ 无实验运行"
else
    echo "$RUNNING" | awk '{printf "  ✅ PID %s: %s (CPU: %s%%, 运行时间: %s)\n", $2, $11" "$12, $3, $10}'
fi

echo ""
echo "=========================================="
echo "📊 实验进度"
echo "=========================================="

# 消融实验
echo ""
echo "消融实验 (ablation_study.py):"
if [ -f logs/ablation_rerun.log ]; then
    ABLATION_VARIANT=$(tail -30 logs/ablation_rerun.log | grep "运行变体" | tail -1)
    ABLATION_PROGRESS=$(tail -20 logs/ablation_rerun.log | grep -o "[0-9]*%" | tail -1)
    ABLATION_STAGE=$(tail -20 logs/ablation_rerun.log | grep -E "预训练|遗忘" | tail -1 | grep -o "^[^:]*")

    if [ ! -z "$ABLATION_VARIANT" ]; then
        echo "  $ABLATION_VARIANT"
    fi
    if [ ! -z "$ABLATION_PROGRESS" ]; then
        echo "  进度: $ABLATION_PROGRESS ($ABLATION_STAGE)"
    else
        echo "  进度: 初始化中..."
    fi
else
    echo "  ⚠️  日志文件不存在"
fi

# 可复现性验证
echo ""
echo "可复现性验证 (reproducibility_test.py):"
if [ -f logs/reproducibility.log ]; then
    REPRO_SEED=$(tail -50 logs/reproducibility.log | grep "种子" | tail -1)
    REPRO_PROGRESS=$(tail -20 logs/reproducibility.log | grep -o "[0-9]*%" | tail -1)
    REPRO_STAGE=$(tail -30 logs/reproducibility.log | grep -E "预训练|Retrain|Fine-tuning|FedForget" | tail -1 | cut -d':' -f1 | sed 's/^[ \t]*//')

    if [ ! -z "$REPRO_SEED" ]; then
        echo "  $REPRO_SEED"
    fi
    if [ ! -z "$REPRO_PROGRESS" ]; then
        echo "  进度: $REPRO_PROGRESS ($REPRO_STAGE)"
    else
        echo "  阶段: $REPRO_STAGE"
    fi
else
    echo "  ⚠️  日志文件不存在"
fi

echo ""
echo "=========================================="
echo "📁 结果文件"
echo "=========================================="
echo ""

if [ -f results/ablation_study.csv ]; then
    echo "  ✅ 消融实验结果已生成"
    ls -lh results/ablation_study.csv | awk '{print "     "$9" ("$5")"}'
else
    echo "  ⏳ 消融实验结果待生成"
fi

if [ -f results/reproducibility_5clients.csv ]; then
    echo "  ✅ 可复现性结果已生成"
    ls -lh results/reproducibility_5clients.csv | awk '{print "     "$9" ("$5")"}'
else
    echo "  ⏳ 可复现性结果待生成"
fi

echo ""
echo "=========================================="
echo "⏰ 预计完成时间"
echo "=========================================="
echo ""
echo "  消融实验: 约14:00 (4-5小时)"
echo "  可复现性: 约18:00 (9小时)"
echo ""
echo "=========================================="
echo ""
echo "💡 提示:"
echo "  查看完整日志: tail -f logs/ablation_rerun.log"
echo "  查看可复现性: tail -f logs/reproducibility.log"
echo ""
