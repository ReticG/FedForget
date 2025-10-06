#!/bin/bash
# 10客户端实验进度监控脚本

echo "=========================================="
echo "10客户端实验进度 ($(date +%H:%M:%S))"
echo "=========================================="
echo ""

# 检查运行中的进程
echo "🔄 运行中的实验:"
ps aux | grep "compare_10clients" | grep -v grep | while read line; do
    pid=$(echo $line | awk '{print $2}')
    cpu=$(echo $line | awk '{print $3}')
    mem=$(echo $line | awk '{print $4}')
    time=$(echo $line | awk '{print $10}')
    echo "  ✅ PID $pid: CPU ${cpu}%, MEM ${mem}%, 运行时间: ${time}"
done

if [ -z "$(ps aux | grep 'compare_10clients' | grep -v grep)" ]; then
    echo "  ⚠️  没有运行中的10客户端实验"
fi

echo ""
echo "=========================================="
echo "📊 实验进度 (Seed 42)"
echo "=========================================="
echo ""

if [ -f logs/10clients_seed42.log ]; then
    # 提取最新的进度信息
    echo "最新进度:"
    tail -5 logs/10clients_seed42.log | grep -E "预训练|Retrain|Fine|FedForget|遗忘"
    echo ""

    # 检查是否有结果
    if grep -q "结果已保存" logs/10clients_seed42.log; then
        echo "  ✅ Seed 42 实验已完成!"
    else
        echo "  🔄 Seed 42 实验运行中..."
    fi
else
    echo "  ⏳ 日志文件尚未生成"
fi

echo ""
echo "=========================================="
echo "📁 结果文件"
echo "=========================================="
echo ""

if [ -f results/10clients_seed42.csv ]; then
    echo "  ✅ results/10clients_seed42.csv (已生成)"
else
    echo "  ⏳ results/10clients_seed42.csv (待生成)"
fi

echo ""
echo "=========================================="
echo "⏰ 预计完成时间"
echo "=========================================="
echo ""

if [ -f logs/10clients_seed42.log ]; then
    # 估算完成时间
    start_time=$(stat -c %Y logs/10clients_seed42.log)
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    # 假设总共需要5小时 (18000秒)
    total_time=18000
    remaining=$((total_time - elapsed))

    if [ $remaining -gt 0 ]; then
        hours=$((remaining / 3600))
        minutes=$(((remaining % 3600) / 60))
        echo "  预计还需: ${hours}小时${minutes}分钟"

        finish_time=$((current_time + remaining))
        finish_str=$(date -d @$finish_time +%H:%M)
        echo "  预计完成: ${finish_str}"
    else
        echo "  实验可能已完成或接近完成"
    fi
fi

echo ""
echo "=========================================="
echo ""
echo "💡 提示:"
echo "  查看完整日志: tail -f logs/10clients_seed42.log"
echo "  查看进度: watch -n 30 ./check_10clients.sh"
echo ""
