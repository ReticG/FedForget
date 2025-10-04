#!/usr/bin/env python3
"""
CIFAR-100上的FedForget评估

CIFAR-100特点:
- 100个细粒度类别 (vs CIFAR-10的10个)
- 每类只有600张图片 (vs CIFAR-10的6000张)
- 预期: 遗忘效果应该更好 (类别更多，泛化性较弱)
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import copy
import time

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("CIFAR-100 FedForget评估")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/4] 数据加载...")

fed_data = load_federated_data(
    dataset_name='cifar100',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

print(f"✓ 数据加载完成")
print(f"  数据集: CIFAR-100 (100 classes)")
print(f"  客户端数量: 5")
print(f"  遗忘客户端: Client 0")

# ============================================================
# 预训练
# ============================================================
print("\n[2/4] 预训练模型 (20轮)...")

model = ConvNet(num_classes=100, num_channels=3)  # 100类
server = Server(model=model, device=device)

clients = []
for i in range(5):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(i, ConvNet(num_classes=100, num_channels=3), client_loader, device, lr=0.01)
    clients.append(client)

start_time = time.time()

for round_idx in range(20):
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

    if (round_idx + 1) % 5 == 0:
        temp_test = server.evaluate(test_loader)
        print(f"  Round {round_idx+1}/20: Test {temp_test['accuracy']:.2f}%")

pretrain_time = time.time() - start_time

pretrain_test = server.evaluate(test_loader)
pretrain_forget = evaluate_model(server.model, client0_loader, device=device)

print(f"\n✓ 预训练完成 ({pretrain_time:.1f}s)")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

pretrained_params = copy.deepcopy(server.get_model_parameters())

# ============================================================
# Retrain基线
# ============================================================
print("\n[3/4] Retrain基线...")

retrain_server = Server(model=ConvNet(num_classes=100, num_channels=3), device=device)
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

start_time = time.time()

for round_idx in range(20):
    global_params = retrain_server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in regular_clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = retrain_server.aggregate(client_models, client_weights)
    retrain_server.set_model_parameters(aggregated)

retrain_time = time.time() - start_time

retrain_test = retrain_server.evaluate(test_loader)
retrain_forget = evaluate_model(retrain_server.model, client0_loader, device=device)

print(f"✓ Retrain完成 ({retrain_time:.1f}s)")
print(f"  测试准确率: {retrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {retrain_forget['accuracy']:.2f}%")

# ============================================================
# FedForget (最佳配置)
# ============================================================
print("\n[4/4] FedForget (alpha=0.93, lambda_neg=3.5)...")

fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=100, num_channels=3),
    device=device
)
fedforget_server.set_model_parameters(copy.deepcopy(pretrained_params))
fedforget_server.lambda_forget = 2.0

unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=100, num_channels=3),
    data_loader=client0_loader,
    device=device,
    lr=0.005
)

unlearn_client.prepare_unlearning(
    global_model_params=copy.deepcopy(pretrained_params),
    local_model_params=None
)

fedforget_server.register_unlearning_client(0, current_round=0)

start_time = time.time()

for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=2,
        method='dual_teacher',
        distill_temp=2.0,
        alpha=0.93,
        lambda_pos=1.0,
        lambda_neg=3.5,
        verbose=False
    )

    selected_regular = np.random.choice(regular_clients, 2, replace=False)

    client_models = [unlearn_client.get_model_parameters()]
    client_ids = [0]
    client_samples = [unlearn_client.num_samples]

    for client in selected_regular:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_ids.append(client.client_id)
        client_samples.append(client.num_samples)

    aggregated = fedforget_server.aggregate_with_fedforget(
        client_models,
        client_ids,
        client_samples,
        current_round=round_idx
    )
    fedforget_server.set_model_parameters(aggregated)

    if (round_idx + 1) % 3 == 0:
        temp_test = fedforget_server.evaluate(test_loader)
        temp_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)
        print(f"  Round {round_idx+1}/10: Test {temp_test['accuracy']:.2f}%, Forget {temp_forget['accuracy']:.2f}%")

fedforget_time = time.time() - start_time

fedforget_test = fedforget_server.evaluate(test_loader)
fedforget_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)

print(f"\n✓ FedForget完成 ({fedforget_time:.1f}s)")
print(f"  测试准确率: {fedforget_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {fedforget_forget['accuracy']:.2f}%")

# ============================================================
# 结果对比
# ============================================================
print("\n" + "="*80)
print("CIFAR-100结果总结")
print("="*80)

print(f"\n预训练基线: Test {pretrain_test['accuracy']:.2f}%, Forget {pretrain_forget['accuracy']:.2f}%")
print()

# 计算指标
methods = ['Retrain', 'FedForget']
test_accs = [retrain_test['accuracy'], fedforget_test['accuracy']]
forget_accs = [retrain_forget['accuracy'], fedforget_forget['accuracy']]
times = [retrain_time, fedforget_time]

retentions = [(acc / pretrain_test['accuracy']) * 100 for acc in test_accs]
forgettings = [((pretrain_forget['accuracy'] - acc) / pretrain_forget['accuracy']) * 100 for acc in forget_accs]

print(f"{'方法':<12} {'Test%':<8} {'Forget%':<9} {'保持率%':<9} {'遗忘率%':<9} {'耗时(s)':<10}")
print("-"*80)

for i, method in enumerate(methods):
    print(f"{method:<12} {test_accs[i]:<8.2f} {forget_accs[i]:<9.2f} {retentions[i]:<9.1f} "
          f"{forgettings[i]:<9.1f} {times[i]:<10.1f}")

print("="*80)

# 与CIFAR-10对比
print("\n📊 CIFAR-100 vs CIFAR-10对比:")
print()
print("CIFAR-10 (已知结果):")
print("  FedForget: 遗忘率 31.2%, 保持率 89.7%")
print()
print(f"CIFAR-100 (本次实验):")
print(f"  FedForget: 遗忘率 {forgettings[1]:.1f}%, 保持率 {retentions[1]:.1f}%")
print()

if forgettings[1] > 31.2:
    print(f"✅ CIFAR-100遗忘率更高: {forgettings[1]:.1f}% > 31.2%")
    print("   → 验证了100类数据集遗忘效果更好的假设")
else:
    print(f"⚠️ CIFAR-100遗忘率未提升: {forgettings[1]:.1f}% ≤ 31.2%")

# 保存结果
import csv
import os

os.makedirs('/home/featurize/work/GJC/fedforget/results', exist_ok=True)

with open('/home/featurize/work/GJC/fedforget/results/cifar100_comparison.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Method', 'Dataset', 'Test_Acc', 'Forget_Acc', 'Retention', 'Forgetting', 'Time'])

    for i, method in enumerate(methods):
        writer.writerow([
            method, 'CIFAR-100',
            test_accs[i], forget_accs[i],
            retentions[i], forgettings[i],
            times[i]
        ])

print(f"\n✓ 结果已保存到: results/cifar100_comparison.csv")
print("\n实验完成!")
