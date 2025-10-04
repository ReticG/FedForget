#!/usr/bin/env python3
"""
平衡的Non-IID遗忘对比实验

改进:
1. 使用更温和的Non-IID参数 (Dirichlet alpha=0.5)
2. 确保所有客户端都有足够的数据进行训练
3. 评估Retrain基线是否能正常工作
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import time

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.unlearning.baselines import RetrainBaseline, FineTuningBaseline
from src.utils.metrics import evaluate_model, compute_class_accuracy

# 固定随机种子
torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("平衡的Non-IID设置下的机器遗忘对比实验")
print("="*80)

# ============================================================
# 数据准备 - 平衡的Non-IID
# ============================================================
print("\n[1/5] 数据加载 (Non-IID, Dirichlet alpha=0.5)...")
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,  # 更温和的Non-IID设置
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)
retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in [1, 2, 3, 4]]

print(f"✓ 数据加载完成")
print(f"  总客户端数: 5")
print(f"  遗忘客户端: 0")
print(f"  保留客户端: 1, 2, 3, 4")
print(f"  数据分布: Non-IID (Dirichlet alpha=0.5)")

# ============================================================
# 预训练
# ============================================================
print("\n[2/5] 预训练模型 (10轮)...")
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

pretrain_test = server.evaluate(test_loader)
pretrain_forget = evaluate_model(server.model, client0_loader, device=device)
pretrain_class_acc = compute_class_accuracy(server.model, client0_loader, num_classes=10, device=device)

print(f"✓ 预训练完成")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")
print(f"\n  客户端0各类别准确率:")
for class_id, acc in pretrain_class_acc.items():
    print(f"    类别 {class_id}: {acc:.2f}%")

pretrained_params = server.get_model_parameters()

# ============================================================
# 方法1: Retrain (检查是否正常工作)
# ============================================================
print("\n[3/5] 方法1: Retrain (从头重新训练,排除客户端0)...")
print("  检查Retrain基线是否能正常训练...")

retrain_model = ConvNet(num_classes=10, num_channels=1)
retrain = RetrainBaseline(retrain_model, device=device, lr=0.05)

retrain.retrain(retain_loaders, rounds=10, local_epochs=2, verbose=False)

retrain_test = retrain.evaluate(test_loader)
retrain_forget = evaluate_model(retrain.model, client0_loader, device=device)
retrain_class_acc = compute_class_accuracy(retrain.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成")
print(f"  测试准确率: {retrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {retrain_forget['accuracy']:.2f}%")
print(f"\n  客户端0各类别准确率:")
for class_id, acc in retrain_class_acc.items():
    print(f"    类别 {class_id}: {acc:.2f}%")

# 检查Retrain是否正常
if retrain_test['accuracy'] < 50.0:
    print("\n⚠️ 警告: Retrain测试准确率异常低,可能存在问题")
    print("   可能原因:")
    print("   1. 客户端1-4的数据分布过于不平衡")
    print("   2. 某些类别的数据量不足")
    print("   3. 训练轮数或学习率设置不当")
else:
    print(f"\n✓ Retrain基线正常工作")

# ============================================================
# 方法2: Fine-tuning
# ============================================================
print("\n[4/5] 方法2: Fine-tuning (在剩余数据上继续训练)...")
finetune_model = ConvNet(num_classes=10, num_channels=1)
finetune = FineTuningBaseline(finetune_model, pretrained_params, device=device, lr=0.01)

finetune.finetune(retain_loaders, rounds=5, local_epochs=2, verbose=False)

finetune_test = finetune.evaluate(test_loader)
finetune_forget = evaluate_model(finetune.model, client0_loader, device=device)
finetune_class_acc = compute_class_accuracy(finetune.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成")
print(f"  测试准确率: {finetune_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {finetune_forget['accuracy']:.2f}%")
print(f"\n  客户端0各类别准确率:")
for class_id, acc in finetune_class_acc.items():
    print(f"    类别 {class_id}: {acc:.2f}%")

# ============================================================
# 方法3: FedForget
# ============================================================
print("\n[5/5] 方法3: FedForget (双教师知识蒸馏)...")

fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=1),
    device=device
)
fedforget_server.set_model_parameters(pretrained_params)
fedforget_server.lambda_forget = 1.5

unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=1),
    data_loader=client0_loader,
    device=device,
    lr=0.01
)

unlearn_client.prepare_unlearning(
    global_model_params=pretrained_params,
    local_model_params=None
)

fedforget_server.register_unlearning_client(0, current_round=0)
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=2,
        method='dual_teacher',
        distill_temp=2.0,
        alpha=0.95,
        lambda_pos=1.0,
        lambda_neg=3.0,
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

fedforget_test = fedforget_server.evaluate(test_loader)
fedforget_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)
fedforget_class_acc = compute_class_accuracy(fedforget_server.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成")
print(f"  测试准确率: {fedforget_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {fedforget_forget['accuracy']:.2f}%")
print(f"\n  客户端0各类别准确率:")
for class_id, acc in fedforget_class_acc.items():
    print(f"    类别 {class_id}: {acc:.2f}%")

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "="*80)
print("完整对比结果")
print("="*80)

print("\n预训练基线:")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

print("\n" + "-"*80)
print(f"{'方法':<20} {'测试准确率':<12} {'遗忘准确率':<12} {'保持率':<10} {'遗忘率':<10}")
print("-"*80)

methods = [
    ("Retrain", retrain_test['accuracy'], retrain_forget['accuracy']),
    ("Fine-tuning", finetune_test['accuracy'], finetune_forget['accuracy']),
    ("FedForget", fedforget_test['accuracy'], fedforget_forget['accuracy']),
]

for method_name, test_acc, forget_acc in methods:
    retention = test_acc / pretrain_test['accuracy'] * 100
    forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

    print(f"{method_name:<20} {test_acc:>6.2f}%      {forget_acc:>6.2f}%      "
          f"{retention:>5.1f}%     {forgetting:>5.1f}%")

print("="*80)

# ============================================================
# 各类别对比
# ============================================================
print("\n各方法在客户端0数据上的类别准确率对比:")
print("-"*80)
print(f"{'类别':<8} {'预训练':<10} {'Retrain':<10} {'Fine-tune':<10} {'FedForget':<10}")
print("-"*80)

for class_id in range(10):
    pretrain_acc = pretrain_class_acc[class_id]
    retrain_acc = retrain_class_acc[class_id]
    finetune_acc = finetune_class_acc[class_id]
    fedforget_acc = fedforget_class_acc[class_id]

    print(f"{class_id:<8} {pretrain_acc:>6.2f}%   {retrain_acc:>6.2f}%   "
          f"{finetune_acc:>6.2f}%   {fedforget_acc:>6.2f}%")

print("="*80)

print("\n实验完成!")
