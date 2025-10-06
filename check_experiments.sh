#!/bin/bash

# 实验进度监控脚本

echo "=========================================="
echo "FedForget 实验进度监控"
echo "=========================================="
echo ""

# 检查运行中的Python进程
echo "运行中的实验:"
ps aux | grep "python scripts/" | grep -v grep | awk '{print "  - " $11 " " $12 " (PID: " $2 ")"}'
echo ""

# 检查消融实验
if [ -f "/tmp/ablation_study.log" ]; then
    echo "消融实验日志 (最后10行):"
    tail -10 /tmp/ablation_study.log | sed 's/^/  /'
    echo ""
fi

# 检查Shadow MIA
if [ -f "/tmp/shadow_mia_fixed.log" ]; then
    echo "Shadow MIA日志 (影子模型进度):"
    grep "影子模型.*测试准确率" /tmp/shadow_mia_fixed.log | tail -5 | sed 's/^/  /'
    echo ""
fi

# 检查结果文件
echo "已生成的结果文件:"
ls -lh results/*.csv 2>/dev/null | tail -5 | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}'
echo ""

echo "=========================================="
echo "使用方法: watch -n 10 ./check_experiments.sh"
echo "=========================================="
