#!/usr/bin/env python3
"""
CIFAR-10数据集上的遗忘对比实验

CIFAR-10特点:
- 32x32彩色图像
- 10个类别: 飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车
- 比MNIST复杂得多,泛化性应该更弱
- 理论上应该有更好的遗忘效果

实验设置:
- Non-IID (Dirichlet alpha=0.5)
- 5个客户端,遗忘客户端0
- 对比Retrain, Fine-tuning, FedForget
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
print("CIFAR-10数据集上的机器遗忘对比实验")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/5] 数据加载 (CIFAR-10, Non-IID, Dirichlet alpha=0.5)...")
fed_data = load_federated_data(
    dataset_name='cifar10',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
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

# 分析数据分布
print("\n各客户端数据分布:")
print("-"*80)
class_names = ['飞机', '汽车', '鸟', '猫', '鹿', '狗', '青蛙', '马', '船', '卡车']

for i in range(5):
    loader = fed_data.get_client_loader(i, batch_size=1024)
    all_labels = []
    for _, labels in loader:
        all_labels.extend(labels.numpy().tolist())

    from collections import Counter
    class_counts = Counter(all_labels)

    print(f"\n客户端{i} ({len(all_labels)}样本):")
    for c in range(10):
        count = class_counts.get(c, 0)
        print(f"  类别{c} ({class_names[c]}): {count:4d} ({count/len(all_labels)*100:5.1f}%)")

print("-"*80)

# ============================================================
# 预训练
# ============================================================
print("\n[2/5] 预训练模型 (20轮, CIFAR-10需要更多轮)...")
model = ConvNet(num_classes=10, num_channels=3)  # 3通道彩色图像
server = Server(model=model, device=device)

clients = []
for i in range(5):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(
        client_id=i,
        model=ConvNet(num_classes=10, num_channels=3),
        data_loader=client_loader,
        device=device,
        lr=0.01  # CIFAR-10使用较小学习率
    )
    clients.append(client)

pretrain_start = time.time()
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
        test_results = server.evaluate(test_loader)
        print(f"  Round {round_idx+1}/20 | Test: {test_results['accuracy']:.2f}%")

pretrain_time = time.time() - pretrain_start

pretrain_test = server.evaluate(test_loader)
pretrain_forget = evaluate_model(server.model, client0_loader, device=device)
pretrain_class_acc = compute_class_accuracy(server.model, client0_loader, num_classes=10, device=device)

print(f"\n✓ 预训练完成 (耗时: {pretrain_time:.1f}s)")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")
print(f"\n  客户端0各类别准确率:")
for c in range(10):
    print(f"    {class_names[c]}: {pretrain_class_acc[c]:.2f}%")

pretrained_params = server.get_model_parameters()

# ============================================================
# 方法1: Retrain
# ============================================================
print("\n[3/5] 方法1: Retrain (从头重新训练,排除客户端0)...")
retrain_model = ConvNet(num_classes=10, num_channels=3)
retrain = RetrainBaseline(retrain_model, device=device, lr=0.01)

retrain_start = time.time()
retrain.retrain(retain_loaders, rounds=20, local_epochs=2, verbose=False)
retrain_time = time.time() - retrain_start

retrain_test = retrain.evaluate(test_loader)
retrain_forget = evaluate_model(retrain.model, client0_loader, device=device)
retrain_class_acc = compute_class_accuracy(retrain.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成 (耗时: {retrain_time:.1f}s)")
print(f"  测试准确率: {retrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {retrain_forget['accuracy']:.2f}%")

# ============================================================
# 方法2: Fine-tuning
# ============================================================
print("\n[4/5] 方法2: Fine-tuning (在剩余数据上继续训练)...")
finetune_model = ConvNet(num_classes=10, num_channels=3)
finetune = FineTuningBaseline(finetune_model, pretrained_params, device=device, lr=0.005)

finetune_start = time.time()
finetune.finetune(retain_loaders, rounds=10, local_epochs=2, verbose=False)
finetune_time = time.time() - finetune_start

finetune_test = finetune.evaluate(test_loader)
finetune_forget = evaluate_model(finetune.model, client0_loader, device=device)
finetune_class_acc = compute_class_accuracy(finetune.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成 (耗时: {finetune_time:.1f}s)")
print(f"  测试准确率: {finetune_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {finetune_forget['accuracy']:.2f}%")

# ============================================================
# 方法3: FedForget
# ============================================================
print("\n[5/5] 方法3: FedForget (双教师知识蒸馏)...")
fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=3),
    device=device
)
fedforget_server.set_model_parameters(pretrained_params)
fedforget_server.lambda_forget = 1.5

unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=3),
    data_loader=client0_loader,
    device=device,
    lr=0.005
)

unlearn_client.prepare_unlearning(
    global_model_params=pretrained_params,
    local_model_params=None
)

fedforget_server.register_unlearning_client(0, current_round=0)
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

fedforget_start = time.time()

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

fedforget_time = time.time() - fedforget_start

fedforget_test = fedforget_server.evaluate(test_loader)
fedforget_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)
fedforget_class_acc = compute_class_accuracy(fedforget_server.model, client0_loader, num_classes=10, device=device)

print(f"✓ 完成 (耗时: {fedforget_time:.1f}s)")
print(f"  测试准确率: {fedforget_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {fedforget_forget['accuracy']:.2f}%")

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "="*80)
print("CIFAR-10完整对比结果")
print("="*80)

print("\n预训练基线:")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

print("\n" + "-"*80)
print(f"{'方法':<20} {'测试准确率':<12} {'遗忘准确率':<12} {'保持率':<10} {'遗忘率':<10} {'耗时':<8}")
print("-"*80)

methods = [
    ("Retrain", retrain_test['accuracy'], retrain_forget['accuracy'], retrain_time),
    ("Fine-tuning", finetune_test['accuracy'], finetune_forget['accuracy'], finetune_time),
    ("FedForget", fedforget_test['accuracy'], fedforget_forget['accuracy'], fedforget_time),
]

for method_name, test_acc, forget_acc, exec_time in methods:
    retention = test_acc / pretrain_test['accuracy'] * 100
    forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

    print(f"{method_name:<20} {test_acc:>6.2f}%      {forget_acc:>6.2f}%      "
          f"{retention:>5.1f}%     {forgetting:>5.1f}%     {exec_time:>5.1f}s")

print("="*80)

# ============================================================
# 各类别对比
# ============================================================
print("\n各方法在客户端0数据上的类别准确率对比:")
print("-"*80)
print(f"{'类别':<10} {'预训练':<10} {'Retrain':<10} {'Fine-tune':<10} {'FedForget':<10} {'下降(Retrain)':<15}")
print("-"*80)

for c in range(10):
    pretrain_acc = pretrain_class_acc[c]
    retrain_acc = retrain_class_acc[c]
    finetune_acc = finetune_class_acc[c]
    fedforget_acc = fedforget_class_acc[c]

    drop = pretrain_acc - retrain_acc
    marker = "🔥" if drop > 5.0 else ""

    print(f"{class_names[c]:<10} {pretrain_acc:>6.2f}%   {retrain_acc:>6.2f}%   "
          f"{finetune_acc:>6.2f}%   {fedforget_acc:>6.2f}%   {drop:>+6.2f}%  {marker}")

print("="*80)

# ============================================================
# 评估
# ============================================================
print("\n评估标准: 测试准确率保持>85%, 遗忘数据准确率下降>10%")
print("-"*80)

for method_name, test_acc, forget_acc, _ in methods:
    retention = test_acc / pretrain_test['accuracy']
    forgetting_ratio = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy']

    # CIFAR-10更难,降低保持率要求到85%
    success = retention > 0.85 and forgetting_ratio > 0.10

    status = "✅" if success else "⚠️"
    print(f"{status} {method_name:<20} 保持率: {retention*100:.1f}%, 遗忘率: {forgetting_ratio*100:.1f}%")

print("="*80)

# 对比MNIST
print("\n💡 CIFAR-10 vs MNIST对比:")
print("-"*80)
print("MNIST (alpha=0.5):")
print("  Retrain: 保持率99.7%, 遗忘率1.6%")
print("  FedForget: 保持率99.8%, 遗忘率0.6%")
print()
print("CIFAR-10 (alpha=0.5):")
retrain_retention = retrain_test['accuracy'] / pretrain_test['accuracy']
retrain_forgetting = (pretrain_forget['accuracy'] - retrain_forget['accuracy']) / pretrain_forget['accuracy']
fedforget_retention = fedforget_test['accuracy'] / pretrain_test['accuracy']
fedforget_forgetting = (pretrain_forget['accuracy'] - fedforget_forget['accuracy']) / pretrain_forget['accuracy']

print(f"  Retrain: 保持率{retrain_retention*100:.1f}%, 遗忘率{retrain_forgetting*100:.1f}%")
print(f"  FedForget: 保持率{fedforget_retention*100:.1f}%, 遗忘率{fedforget_forgetting*100:.1f}%")
print()

if retrain_forgetting > 0.016:  # 大于MNIST的1.6%
    print("✅ CIFAR-10的遗忘效果明显优于MNIST!")
    print("   原因: CIFAR-10更复杂,泛化性更弱,少量数据不足以学好所有类别")
else:
    print("⚠️ CIFAR-10的遗忘效果仍然不理想")
    print("   可能需要更激进的Non-IID设置或类别遗忘策略")

print("\n实验完成!")
