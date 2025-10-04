#!/usr/bin/env python3
"""
分析数据重叠度 - 为什么遗忘这么难？

检查:
1. 客户端0的数据是否在其他客户端中也存在？
2. 各客户端的类别分布
3. 遗忘客户端与保留客户端的数据重叠程度
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
from collections import Counter

from src.data import load_federated_data

print("="*80)
print("数据重叠度分析")
print("="*80)

# 测试两种设置
configs = [
    ("IID", 'iid', None),
    ("Non-IID (α=0.5)", 'noniid', 0.5),
    ("Non-IID (α=0.3)", 'noniid', 0.3),
]

for config_name, data_dist, alpha in configs:
    print(f"\n{'='*80}")
    print(f"配置: {config_name}")
    print(f"{'='*80}")

    # 加载数据
    if alpha is not None:
        fed_data = load_federated_data(
            dataset_name='mnist',
            num_clients=5,
            data_dist=data_dist,
            dirichlet_alpha=alpha,
            data_root='/home/featurize/data'
        )
    else:
        fed_data = load_federated_data(
            dataset_name='mnist',
            num_clients=5,
            data_dist=data_dist,
            data_root='/home/featurize/data'
        )

    # 分析各客户端的类别分布
    print("\n各客户端的类别分布:")
    print("-"*80)
    print(f"{'客户端':<10}", end="")
    for c in range(10):
        print(f"{'类别'+str(c):<8}", end="")
    print(f"{'总数':<10}")
    print("-"*80)

    client_class_counts = []

    for i in range(5):
        loader = fed_data.get_client_loader(i, batch_size=1024)
        all_labels = []

        for _, labels in loader:
            all_labels.extend(labels.numpy().tolist())

        class_counts = Counter(all_labels)
        client_class_counts.append(class_counts)

        print(f"客户端{i:<3}", end="")
        for c in range(10):
            count = class_counts.get(c, 0)
            print(f"{count:<8}", end="")
        print(f"{len(all_labels):<10}")

    print("-"*80)

    # 分析客户端0的类别在其他客户端中的覆盖情况
    print("\n客户端0的类别在其他客户端中的覆盖情况:")
    print("-"*80)

    client0_classes = set(client_class_counts[0].keys())
    print(f"客户端0拥有的类别: {sorted(client0_classes)}")
    print(f"客户端0的类别数量: {len(client0_classes)}")

    print("\n各类别在客户端0和其他客户端中的数量对比:")
    print("-"*80)
    print(f"{'类别':<8} {'客户端0':<12} {'客户端1-4总和':<15} {'比例':<10}")
    print("-"*80)

    for c in sorted(client0_classes):
        count_client0 = client_class_counts[0].get(c, 0)
        count_others = sum(client_class_counts[i].get(c, 0) for i in range(1, 5))

        if count_client0 > 0:
            ratio = count_others / count_client0
            print(f"{c:<8} {count_client0:<12} {count_others:<15} {ratio:<10.2f}x")

    print("-"*80)

    # 计算整体重叠度
    total_client0 = sum(client_class_counts[0].values())
    total_others = sum(sum(client_class_counts[i].values()) for i in range(1, 5))

    # 计算每个类别的"可替代性" - 其他客户端是否有足够的同类别数据
    print("\n数据可替代性分析:")
    print("-"*80)

    replaceable = 0
    non_replaceable = 0

    for c in client0_classes:
        count_client0 = client_class_counts[0].get(c, 0)
        count_others = sum(client_class_counts[i].get(c, 0) for i in range(1, 5))

        # 如果其他客户端有>=50%的同类别数据,认为可替代
        if count_others >= count_client0 * 0.5:
            replaceable += count_client0
            status = "✅ 可替代"
        else:
            non_replaceable += count_client0
            status = "❌ 不可替代"

        print(f"类别 {c}: {status} (客户端0: {count_client0}, 其他: {count_others})")

    print("-"*80)
    print(f"可替代数据比例: {replaceable}/{total_client0} = {replaceable/total_client0*100:.1f}%")
    print(f"不可替代数据比例: {non_replaceable}/{total_client0} = {non_replaceable/total_client0*100:.1f}%")

    print("\n💡 分析:")
    if replaceable / total_client0 > 0.9:
        print("   ⚠️ 客户端0的数据>90%可被其他客户端替代")
        print("   → 这解释了为什么遗忘效果差: 模型可以从其他客户端学到相同的知识")
    elif replaceable / total_client0 > 0.5:
        print("   ⚠️ 客户端0的数据>50%可被其他客户端替代")
        print("   → 遗忘会有一定效果,但不会很明显")
    else:
        print("   ✅ 客户端0有大量独特数据")
        print("   → 遗忘应该有明显效果")

print("\n" + "="*80)
print("总结")
print("="*80)
print("\n关键发现:")
print("1. IID设置: 所有客户端数据分布几乎相同 → 遗忘无效")
print("2. Non-IID (α=0.5): 数据分布有差异,但仍有大量重叠 → 遗忘效果有限")
print("3. Non-IID (α=0.3): 数据分布差异更大 → 可能有更好的遗忘效果")
print("\n建议:")
print("- 使用更低的Dirichlet alpha (0.1-0.3)创造更强的数据异质性")
print("- 但要确保Retrain基线能正常训练")
print("- 或者考虑'类别遗忘'而非'客户端遗忘'")
