#!/usr/bin/env python3
"""
完整对比所有遗忘方法

对比:
1. Retrain - 从头重新训练(理想基线)
2. Fine-tuning - 在剩余数据上继续训练
3. FedForget - 我们的方法
4. No unlearning - 不做任何处理(最差基线)

评估指标:
- Test Accuracy: 测试准确率(模型效用)
- Forget Accuracy: 遗忘数据准确率(遗忘效果)
- Retention Ratio: 测试准确率保持率
- Forgetting Ratio: 遗忘数据准确率下降率
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
from src.utils.metrics import evaluate_model

# 固定随机种子
torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("机器遗忘方法完整对比实验")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/5] 数据加载...")
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='iid',
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)  # 遗忘客户端
retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in [1, 2, 3, 4]]

print(f"✓ 数据加载完成")
print(f"  总客户端数: 5")
print(f"  遗忘客户端: 0")
print(f"  保留客户端: 1, 2, 3, 4")

# ============================================================
# 预训练 (所有方法共用)
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

pretrain_start = time.time()
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

pretrain_time = time.time() - pretrain_start

pretrain_test = server.evaluate(test_loader)
pretrain_forget = evaluate_model(server.model, client0_loader, device=device)

print(f"✓ 预训练完成 (耗时: {pretrain_time:.1f}s)")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

# 保存预训练参数
pretrained_params = server.get_model_parameters()

# ============================================================
# 方法1: No Unlearning (最差基线)
# ============================================================
print("\n[3/5] 方法1: No Unlearning (不做任何处理)...")
no_unlearn_test = pretrain_test
no_unlearn_forget = pretrain_forget
print(f"✓ 结果:")
print(f"  测试准确率: {no_unlearn_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {no_unlearn_forget['accuracy']:.2f}%")

# ============================================================
# 方法2: Retrain (理想基线)
# ============================================================
print("\n[4/5] 方法2: Retrain (从头重新训练,排除客户端0)...")
retrain_model = ConvNet(num_classes=10, num_channels=1)
retrain = RetrainBaseline(retrain_model, device=device, lr=0.05)

retrain_start = time.time()
retrain.retrain(retain_loaders, rounds=10, local_epochs=2, verbose=False)
retrain_time = time.time() - retrain_start

retrain_test = retrain.evaluate(test_loader)
retrain_forget = evaluate_model(retrain.model, client0_loader, device=device)

print(f"✓ 完成 (耗时: {retrain_time:.1f}s)")
print(f"  测试准确率: {retrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {retrain_forget['accuracy']:.2f}%")

# ============================================================
# 方法3: Fine-tuning
# ============================================================
print("\n[5/5] 方法3: Fine-tuning (在剩余数据上继续训练)...")
finetune_model = ConvNet(num_classes=10, num_channels=1)
finetune = FineTuningBaseline(finetune_model, pretrained_params, device=device, lr=0.01)

finetune_start = time.time()
finetune.finetune(retain_loaders, rounds=5, local_epochs=2, verbose=False)
finetune_time = time.time() - finetune_start

finetune_test = finetune.evaluate(test_loader)
finetune_forget = evaluate_model(finetune.model, client0_loader, device=device)

print(f"✓ 完成 (耗时: {finetune_time:.1f}s)")
print(f"  测试准确率: {finetune_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {finetune_forget['accuracy']:.2f}%")

# ============================================================
# 方法4: FedForget (我们的方法)
# ============================================================
print("\n方法4: FedForget (双教师知识蒸馏 + 动态权重调整)...")
print("测试多组参数...")

fedforget_configs = [
    # (alpha, lambda_neg, lambda_forget, rounds, description)
    (0.95, 3.0, 1.5, 10, "保守参数"),
    (0.90, 5.0, 2.0, 10, "中等参数"),
    (0.85, 8.0, 2.5, 10, "激进参数"),
]

fedforget_results = []

for alpha, lambda_neg, lambda_forget, rounds, desc in fedforget_configs:
    print(f"\n  配置: {desc}")
    print(f"    alpha={alpha}, lambda_neg={lambda_neg}, lambda_forget={lambda_forget}, rounds={rounds}")

    fedforget_server = FedForgetServer(
        model=ConvNet(num_classes=10, num_channels=1),
        device=device
    )
    fedforget_server.set_model_parameters(pretrained_params)
    fedforget_server.lambda_forget = lambda_forget

    unlearn_client = UnlearningClient(
        client_id=0,
        model=ConvNet(num_classes=10, num_channels=1),
        data_loader=client0_loader,
        device=device,
        lr=0.01
    )

    # 准备遗忘: 教师A = 预训练模型(固定)
    unlearn_client.prepare_unlearning(
        global_model_params=pretrained_params,
        local_model_params=None
    )

    fedforget_server.register_unlearning_client(0, current_round=0)
    regular_clients = [clients[1], clients[2], clients[3], clients[4]]

    fedforget_start = time.time()

    for round_idx in range(rounds):
        global_params = fedforget_server.get_model_parameters()

        # 遗忘客户端训练
        unlearn_client.set_model_parameters(global_params)
        unlearn_client.unlearning_train(
            epochs=2,
            method='dual_teacher',
            distill_temp=2.0,
            alpha=alpha,
            lambda_pos=1.0,
            lambda_neg=lambda_neg,
            verbose=False
        )

        # 随机选择2个常规客户端
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

        # FedForget聚合
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

    print(f"  ✓ 完成 (耗时: {fedforget_time:.1f}s)")
    print(f"    测试准确率: {fedforget_test['accuracy']:.2f}%")
    print(f"    遗忘数据准确率: {fedforget_forget['accuracy']:.2f}%")

    fedforget_results.append({
        'config': desc,
        'alpha': alpha,
        'lambda_neg': lambda_neg,
        'lambda_forget': lambda_forget,
        'test_acc': fedforget_test['accuracy'],
        'forget_acc': fedforget_forget['accuracy'],
        'time': fedforget_time
    })

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
print(f"{'方法':<20} {'测试准确率':<12} {'遗忘准确率':<12} {'保持率':<10} {'遗忘率':<10} {'耗时':<8}")
print("-"*80)

methods = [
    ("No Unlearning", no_unlearn_test['accuracy'], no_unlearn_forget['accuracy'], 0.0),
    ("Retrain (理想)", retrain_test['accuracy'], retrain_forget['accuracy'], retrain_time),
    ("Fine-tuning", finetune_test['accuracy'], finetune_forget['accuracy'], finetune_time),
]

for method_name, test_acc, forget_acc, exec_time in methods:
    retention = test_acc / pretrain_test['accuracy'] * 100
    forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

    print(f"{method_name:<20} {test_acc:>6.2f}%      {forget_acc:>6.2f}%      "
          f"{retention:>5.1f}%     {forgetting:>5.1f}%     {exec_time:>5.1f}s")

print("-"*80)

for result in fedforget_results:
    method_name = f"FedForget ({result['config']})"
    test_acc = result['test_acc']
    forget_acc = result['forget_acc']
    exec_time = result['time']

    retention = test_acc / pretrain_test['accuracy'] * 100
    forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

    print(f"{method_name:<20} {test_acc:>6.2f}%      {forget_acc:>6.2f}%      "
          f"{retention:>5.1f}%     {forgetting:>5.1f}%     {exec_time:>5.1f}s")

print("="*80)

# ============================================================
# 成功评估
# ============================================================
print("\n评估标准: 测试准确率保持>90%, 遗忘数据准确率<60%")
print("-"*80)

for method_name, test_acc, forget_acc, _ in methods[1:]:  # 排除No Unlearning
    retention = test_acc / pretrain_test['accuracy']
    success = retention > 0.90 and forget_acc < 60.0

    status = "✅" if success else "⚠️"
    print(f"{status} {method_name:<20} 保持率: {retention*100:.1f}%, 遗忘准确率: {forget_acc:.2f}%")

for result in fedforget_results:
    method_name = f"FedForget ({result['config']})"
    test_acc = result['test_acc']
    forget_acc = result['forget_acc']

    retention = test_acc / pretrain_test['accuracy']
    success = retention > 0.90 and forget_acc < 60.0

    status = "✅" if success else "⚠️"
    print(f"{status} {method_name:<20} 保持率: {retention*100:.1f}%, 遗忘准确率: {forget_acc:.2f}%")

print("="*80)

# ============================================================
# 最佳FedForget配置
# ============================================================
best_fedforget = min(fedforget_results, key=lambda x: x['forget_acc'])
best_retention = best_fedforget['test_acc'] / pretrain_test['accuracy']

print("\n最佳FedForget配置:")
print(f"  配置: {best_fedforget['config']}")
print(f"  alpha={best_fedforget['alpha']}, lambda_neg={best_fedforget['lambda_neg']}, "
      f"lambda_forget={best_fedforget['lambda_forget']}")
print(f"  测试准确率: {best_fedforget['test_acc']:.2f}% (保持率: {best_retention*100:.1f}%)")
print(f"  遗忘准确率: {best_fedforget['forget_acc']:.2f}%")

if best_retention > 0.90 and best_fedforget['forget_acc'] < 60.0:
    print("\n🎉 FedForget成功达到目标!")
else:
    print("\n💡 FedForget需要进一步优化")
    if best_retention <= 0.90:
        print("   - 测试准确率保持不足,建议增大alpha")
    if best_fedforget['forget_acc'] >= 60.0:
        print("   - 遗忘效果不足,建议增大lambda_neg或lambda_forget")

print("\n实验完成!")
