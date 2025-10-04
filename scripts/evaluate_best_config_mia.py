#!/usr/bin/env python3
"""
评估Day 2最佳配置的MIA表现

配置: alpha=0.93, lambda_neg=3.5, lambda_forget=2.0
预期: 更高的遗忘率(40.4%)，检验隐私保护是否仍然良好
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import copy

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model
from src.utils.mia import evaluate_unlearning_privacy
from torch.utils.data import ConcatDataset, DataLoader

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("最佳配置MIA评估: alpha=0.93, lambda_neg=3.5")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/3] 数据加载...")

fed_data = load_federated_data(
    dataset_name='cifar10',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

# 保留数据
retain_datasets = [fed_data.get_client_dataset(i) for i in range(1, 5)]
retain_combined = ConcatDataset(retain_datasets)
retain_loader = DataLoader(retain_combined, batch_size=64, shuffle=False)

print(f"✓ 数据加载完成")

# ============================================================
# 预训练
# ============================================================
print("\n[2/3] 预训练...")

model = ConvNet(num_classes=10, num_channels=3)
server = Server(model=model, device=device)

clients = []
for i in range(5):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(i, ConvNet(num_classes=10, num_channels=3), client_loader, device, lr=0.01)
    clients.append(client)

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

pretrain_test = server.evaluate(test_loader)
pretrain_forget = evaluate_model(server.model, client0_loader, device=device)

print(f"✓ 预训练完成")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

pretrained_params = copy.deepcopy(server.get_model_parameters())

# ============================================================
# 评估: 最佳配置 (alpha=0.93, lambda_neg=3.5)
# ============================================================
print("\n[3/3] 评估最佳配置...")
print("\n" + "-"*80)
print("FedForget: alpha=0.93, lambda_neg=3.5, lambda_forget=2.0")
print("-"*80)

fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=3),
    device=device
)
fedforget_server.set_model_parameters(copy.deepcopy(pretrained_params))
fedforget_server.lambda_forget = 2.0  # 使用Day 2最佳配置

unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=3),
    data_loader=client0_loader,
    device=device,
    lr=0.005
)

unlearn_client.prepare_unlearning(
    global_model_params=copy.deepcopy(pretrained_params),
    local_model_params=None
)

fedforget_server.register_unlearning_client(0, current_round=0)
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

print("\n遗忘训练进度:")
for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=2,
        method='dual_teacher',
        distill_temp=2.0,
        alpha=0.93,  # Day 2最佳
        lambda_pos=1.0,
        lambda_neg=3.5,  # Day 2最佳
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

    # 每轮评估
    if (round_idx + 1) % 3 == 0:
        temp_test = fedforget_server.evaluate(test_loader)
        temp_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)
        print(f"  Round {round_idx+1}: Test {temp_test['accuracy']:.2f}%, Forget {temp_forget['accuracy']:.2f}%")

# 最终评估
test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)

retention = test_results['accuracy'] / pretrain_test['accuracy']
forgetting = (pretrain_forget['accuracy'] - forget_results['accuracy']) / pretrain_forget['accuracy']

print(f"\n✓ 遗忘训练完成")
print(f"  测试准确率: {test_results['accuracy']:.2f}% (保持率: {retention*100:.1f}%)")
print(f"  遗忘准确率: {forget_results['accuracy']:.2f}% (遗忘率: {forgetting*100:.1f}%)")

# MIA评估
print("\n" + "-"*80)
print("MIA隐私评估")
print("-"*80)

mia_results = evaluate_unlearning_privacy(
    fedforget_server.model,
    forget_loader=client0_loader,
    retain_loader=retain_loader,
    test_loader=test_loader,
    device=device
)

print(f"\nForget vs Test (理想: ASR≈50%, AUC≈0.5):")
print(f"  攻击准确率 (ASR): {mia_results['forget_vs_test']['accuracy']:.2f}%")
print(f"  AUC: {mia_results['forget_vs_test']['auc']:.4f}")
print(f"  Forget损失: {mia_results['forget_vs_test']['forget_loss']:.4f}")
print(f"  Test损失: {mia_results['forget_vs_test']['test_loss']:.4f}")

print(f"\nForget vs Retain:")
print(f"  攻击准确率 (ASR): {mia_results['forget_vs_retain']['accuracy']:.2f}%")
print(f"  AUC: {mia_results['forget_vs_retain']['auc']:.4f}")

# 与Day 3配置对比
print("\n" + "="*80)
print("配置对比总结")
print("="*80)

print(f"\n{'配置':<20} {'Test%':<8} {'Forget%':<9} {'遗忘率%':<9} {'ASR%':<8} {'AUC':<8}")
print("-"*80)

# Day 3配置 (alpha=0.95)
print(f"{'Day 3 (α=0.95)':<20} {'63.75':<8} {'61.87':<9} {'27.3':<9} {'48.41':<8} {'0.4642':<8}")

# Day 2最佳 (alpha=0.93)
print(f"{'Day 2最佳 (α=0.93)':<20} {test_results['accuracy']:<8.2f} {forget_results['accuracy']:<9.2f} "
      f"{forgetting*100:<9.1f} {mia_results['forget_vs_test']['accuracy']:<8.2f} "
      f"{mia_results['forget_vs_test']['auc']:<8.4f}")

print("="*80)

# 分析
print("\n📊 分析:")

if forgetting * 100 > 27.3:
    print(f"✅ 遗忘率提升: {forgetting*100:.1f}% > 27.3% (Day 3)")
else:
    print(f"⚠️ 遗忘率下降: {forgetting*100:.1f}% < 27.3% (Day 3)")

asr = mia_results['forget_vs_test']['accuracy']
if abs(asr - 50) < abs(48.41 - 50):
    print(f"✅ 隐私保护更好: ASR {asr:.2f}% 更接近50%")
elif abs(asr - 50) > abs(48.41 - 50) + 5:
    print(f"⚠️ 隐私保护变差: ASR {asr:.2f}% 偏离50%超过5%")
else:
    print(f"➡️ 隐私保护相当: ASR {asr:.2f}% vs 48.41%")

if retention * 100 > 90.6:
    print(f"✅ 性能保持更好: {retention*100:.1f}% > 90.6% (Day 3)")
else:
    print(f"⚠️ 性能下降更多: {retention*100:.1f}% < 90.6% (Day 3)")

# 保存结果
import csv
import os

os.makedirs('/home/featurize/work/GJC/fedforget/results', exist_ok=True)

with open('/home/featurize/work/GJC/fedforget/results/best_config_mia.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Config', 'Alpha', 'Lambda_neg', 'Lambda_forget',
                    'Test_Acc', 'Forget_Acc', 'Forgetting_Rate',
                    'ASR_Forget_vs_Test', 'AUC_Forget_vs_Test'])

    writer.writerow([
        'Day2_Best', 0.93, 3.5, 2.0,
        test_results['accuracy'],
        forget_results['accuracy'],
        forgetting * 100,
        mia_results['forget_vs_test']['accuracy'],
        mia_results['forget_vs_test']['auc']
    ])

print(f"\n✓ 结果已保存到: results/best_config_mia.csv")
print("\n实验完成!")
