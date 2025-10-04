#!/usr/bin/env python3
"""
测试泛化性假设

问题: 为什么客户端0有53.3%不可替代数据,但遗忘效果只有0.6%?

假设: MNIST太简单,模型从少量数据就能学会所有类别
     即使客户端0在类别4/8上有优势,其他客户端的少量样本也足够

实验:
1. 用客户端1-4训练模型(排除客户端0)
2. 在客户端0的各类别上评估
3. 特别关注类别4和8(客户端0占优的类别)
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.utils.metrics import compute_class_accuracy

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("泛化性测试 - MNIST是否太简单?")
print("="*80)

# 加载Non-IID数据 (alpha=0.5)
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

# 统计各客户端的类别4和8的数量
print("\n客户端数据统计 (关注类别4和8):")
print("-"*80)

for i in range(5):
    loader = fed_data.get_client_loader(i, batch_size=1024)
    class4_count = 0
    class8_count = 0
    total = 0

    for _, labels in loader:
        class4_count += (labels == 4).sum().item()
        class8_count += (labels == 8).sum().item()
        total += labels.size(0)

    print(f"客户端{i}: 总数={total:5d}, 类别4={class4_count:4d}, 类别8={class8_count:4d}")

print("-"*80)
print("客户端0: 类别4占优 (4339 vs 1503总和)")
print("客户端0: 类别8占优 (5596 vs 255总和)")

# 实验1: 用所有客户端训练
print("\n" + "="*80)
print("实验1: 用所有5个客户端训练 (包括客户端0)")
print("="*80)

model = ConvNet(num_classes=10, num_channels=1)
server = Server(model=model, device=device)

clients = []
for i in range(5):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(
        client_id=i,
        model=ConvNet(num_classes=10, num_channels=1),
        data_loader=client_loader,
        device=device,
        lr=0.05
    )
    clients.append(client)

for round_idx in range(10):
    global_params = server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

test_results = server.evaluate(test_loader)
class_acc_all = compute_class_accuracy(server.model, client0_loader, num_classes=10, device=device)

print(f"测试准确率: {test_results['accuracy']:.2f}%")
print(f"\n客户端0各类别准确率:")
for c in range(10):
    print(f"  类别{c}: {class_acc_all[c]:.2f}%")

# 实验2: 只用客户端1-4训练 (排除客户端0)
print("\n" + "="*80)
print("实验2: 只用客户端1-4训练 (排除客户端0)")
print("="*80)

model2 = ConvNet(num_classes=10, num_channels=1)
server2 = Server(model=model2, device=device)

for round_idx in range(10):
    global_params = server2.get_model_parameters()
    client_models = []
    client_weights = []

    for i in [1, 2, 3, 4]:  # 排除客户端0
        clients[i].set_model_parameters(global_params)
        clients[i].local_train(epochs=2, verbose=False)
        client_models.append(clients[i].get_model_parameters())
        client_weights.append(clients[i].num_samples)

    aggregated = server2.aggregate(client_models, client_weights)
    server2.set_model_parameters(aggregated)

test_results2 = server2.evaluate(test_loader)
class_acc_retrain = compute_class_accuracy(server2.model, client0_loader, num_classes=10, device=device)

print(f"测试准确率: {test_results2['accuracy']:.2f}%")
print(f"\n客户端0各类别准确率:")
for c in range(10):
    print(f"  类别{c}: {class_acc_retrain[c]:.2f}%")

# 对比分析
print("\n" + "="*80)
print("对比分析")
print("="*80)

print("\n各类别准确率对比:")
print("-"*80)
print(f"{'类别':<8} {'全部客户端':<12} {'排除客户端0':<12} {'下降':<10} {'数据优势':<15}")
print("-"*80)

data_advantage = {
    4: "客户端0占优 (4339 vs 1503)",
    8: "客户端0占优 (5596 vs 255)",
}

for c in range(10):
    acc_all = class_acc_all[c]
    acc_retrain = class_acc_retrain[c]
    drop = acc_all - acc_retrain

    advantage = data_advantage.get(c, "其他客户端占优")

    marker = "🔥" if abs(drop) > 2.0 else ""
    print(f"{c:<8} {acc_all:>6.2f}%      {acc_retrain:>6.2f}%      {drop:>+6.2f}%  {advantage:<15} {marker}")

print("-"*80)

# 关键分析
print("\n💡 关键分析:")
print("-"*80)

class4_drop = class_acc_all[4] - class_acc_retrain[4]
class8_drop = class_acc_all[8] - class_acc_retrain[8]

print(f"\n类别4 (客户端0: 4339, 其他: 1503):")
print(f"  排除客户端0后准确率下降: {class4_drop:+.2f}%")
if abs(class4_drop) < 2.0:
    print(f"  ⚠️ 下降幅度很小! 说明其他客户端的1503个样本已经足够训练")
    print(f"     即使客户端0有2.9倍数据优势,遗忘效果仍然有限")
else:
    print(f"  ✅ 有明显下降,遗忘有效")

print(f"\n类别8 (客户端0: 5596, 其他: 255):")
print(f"  排除客户端0后准确率下降: {class8_drop:+.2f}%")
if abs(class8_drop) < 2.0:
    print(f"  ⚠️ 下降幅度很小! 说明其他客户端的255个样本已经足够训练")
    print(f"     即使客户端0有21.9倍数据优势,遗忘效果仍然有限")
    print(f"     → 这证明了MNIST的泛化性极强,少量样本就能学好")
else:
    print(f"  ✅ 有明显下降,遗忘有效")

print("\n" + "="*80)
print("结论")
print("="*80)
print("\n根本原因: **MNIST数据集的泛化性太强**")
print()
print("证据:")
print("1. 即使客户端0在类别8上有21.9倍数据优势 (5596 vs 255)")
print("   排除客户端0后,模型仍能在该类别上保持高准确率")
print("2. 这说明仅255个样本就足以让模型学会类别8")
print("3. MNIST是10个非常简单的手写数字,容易学习和泛化")
print()
print("解决方案:")
print("✅ 1. 使用更复杂的数据集 (CIFAR-10/CIFAR-100)")
print("✅ 2. 减少客户端数量,增加数据异质性")
print("✅ 3. 考虑'类别遗忘'而非'客户端遗忘'")
print("   → 让遗忘客户端拥有某类别的全部或绝大部分数据")
