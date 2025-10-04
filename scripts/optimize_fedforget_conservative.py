#!/usr/bin/env python3
"""
FedForget保守参数优化 (修复版)

修复:
1. 每个配置重新加载预训练参数(深拷贝)
2. 使用更保守的参数范围
3. 固定随机种子确保可重复性
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import time
import csv
import copy
from itertools import product

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model

device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("FedForget保守参数优化 (修复版)")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/3] 数据加载...")
torch.manual_seed(42)
np.random.seed(42)

fed_data = load_federated_data(
    dataset_name='cifar10',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

print(f"✓ 数据加载完成")

# ============================================================
# 预训练
# ============================================================
print("\n[2/3] 预训练模型 (20轮)...")
torch.manual_seed(42)
np.random.seed(42)

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

# 深拷贝预训练参数
pretrained_params = copy.deepcopy(server.get_model_parameters())

# ============================================================
# 参数搜索 (更保守的范围)
# ============================================================
print("\n[3/3] 参数搜索...")

# 更保守的搜索空间
alpha_values = [0.96, 0.97, 0.98, 0.99]
lambda_neg_values = [0.5, 1.0, 1.5, 2.0, 3.0]
lambda_forget = 1.5

total_configs = len(alpha_values) * len(lambda_neg_values)
print(f"搜索空间: {len(alpha_values)} alphas × {len(lambda_neg_values)} lambda_negs = {total_configs} 配置")
print()

results = []
config_idx = 0

for alpha, lambda_neg in product(alpha_values, lambda_neg_values):
    config_idx += 1
    print(f"[{config_idx}/{total_configs}] 测试: alpha={alpha}, lambda_neg={lambda_neg}")

    # 每次都重新设置随机种子
    torch.manual_seed(42 + config_idx)
    np.random.seed(42 + config_idx)

    # 创建新的FedForgetServer (深拷贝参数)
    fedforget_server = FedForgetServer(
        model=ConvNet(num_classes=10, num_channels=3),
        device=device
    )
    fedforget_server.set_model_parameters(copy.deepcopy(pretrained_params))
    fedforget_server.lambda_forget = lambda_forget

    # 创建新的遗忘客户端
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

    # 遗忘训练
    start_time = time.time()
    early_stop = False

    for round_idx in range(10):
        global_params = fedforget_server.get_model_parameters()

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

        # 早停检测
        if (round_idx + 1) % 3 == 0:
            temp_test = fedforget_server.evaluate(test_loader)
            if temp_test['accuracy'] < 50.0:
                print(f"  ⚠️ 早停! Round {round_idx+1}, Test={temp_test['accuracy']:.2f}%")
                early_stop = True
                break

    exec_time = time.time() - start_time

    # 最终评估
    if early_stop:
        test_acc = temp_test['accuracy']
        forget_acc = 0.0
        status = "CRASHED"
    else:
        test_results = fedforget_server.evaluate(test_loader)
        forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)
        test_acc = test_results['accuracy']
        forget_acc = forget_results['accuracy']
        status = "OK"

    # 计算指标
    retention = test_acc / pretrain_test['accuracy']
    forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy']

    result = {
        'alpha': alpha,
        'lambda_neg': lambda_neg,
        'lambda_forget': lambda_forget,
        'test_acc': test_acc,
        'forget_acc': forget_acc,
        'retention': retention * 100,
        'forgetting': forgetting * 100,
        'time': exec_time,
        'status': status
    }
    results.append(result)

    # 打印结果
    if status == "OK":
        print(f"  ✓ Test: {test_acc:.2f}%, Forget: {forget_acc:.2f}%, "
              f"保持率: {retention*100:.1f}%, 遗忘率: {forgetting*100:.1f}%")
    else:
        print(f"  ✗ 模型崩溃")

    print()

# ============================================================
# 结果汇总
# ============================================================
print("="*80)
print("参数搜索完成")
print("="*80)

# 保存到CSV
csv_path = '/home/featurize/work/GJC/fedforget/results/fedforget_conservative_cifar10.csv'
import os
os.makedirs('/home/featurize/work/GJC/fedforget/results', exist_ok=True)

with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['alpha', 'lambda_neg', 'lambda_forget',
                                            'test_acc', 'forget_acc', 'retention',
                                            'forgetting', 'time', 'status'])
    writer.writeheader()
    writer.writerows(results)

print(f"\n✓ 结果已保存到: {csv_path}")

# 过滤有效结果
valid_results = [r for r in results if r['status'] == 'OK']

print(f"\n有效配置: {len(valid_results)}/{len(results)}")

if len(valid_results) > 0:
    valid_results_sorted = sorted(valid_results, key=lambda x: x['forgetting'], reverse=True)

    print("\n" + "="*80)
    print("所有有效配置 (按遗忘率排序)")
    print("="*80)
    print(f"{'Rank':<6} {'Alpha':<8} {'λ_neg':<8} {'Test%':<8} {'Forget%':<9} {'保持率%':<10} {'遗忘率%':<10}")
    print("-"*80)

    for i, r in enumerate(valid_results_sorted, 1):
        success = r['retention'] > 90.0 and r['forgetting'] > 25.0
        marker = "🎯" if success else ""

        print(f"{i:<6} {r['alpha']:<8.2f} {r['lambda_neg']:<8.1f} {r['test_acc']:<8.2f} "
              f"{r['forget_acc']:<9.2f} {r['retention']:<10.1f} {r['forgetting']:<10.1f} {marker}")

    print("="*80)

    # 推荐配置
    print("\n推荐配置:")

    # 最大遗忘率 (保持率>85%)
    high_forgetting = [r for r in valid_results if r['retention'] > 85.0]
    if high_forgetting:
        best = max(high_forgetting, key=lambda x: x['forgetting'])
        print(f"\n1. 最大遗忘率 (保持率>85%):")
        print(f"   alpha={best['alpha']}, lambda_neg={best['lambda_neg']}")
        print(f"   → 遗忘率: {best['forgetting']:.1f}%, 保持率: {best['retention']:.1f}%")

    # 最佳平衡 (保持率>90%, 遗忘率>20%)
    balanced = [r for r in valid_results if r['retention'] > 90.0 and r['forgetting'] > 20.0]
    if balanced:
        best = max(balanced, key=lambda x: x['forgetting'])
        print(f"\n2. 最佳平衡 (保持率>90%, 遗忘率>20%):")
        print(f"   alpha={best['alpha']}, lambda_neg={best['lambda_neg']}")
        print(f"   → 遗忘率: {best['forgetting']:.1f}%, 保持率: {best['retention']:.1f}%")

    # 最高保持率 (遗忘率>15%)
    high_retention = [r for r in valid_results if r['forgetting'] > 15.0]
    if high_retention:
        best = max(high_retention, key=lambda x: x['retention'])
        print(f"\n3. 最高保持率 (遗忘率>15%):")
        print(f"   alpha={best['alpha']}, lambda_neg={best['lambda_neg']}")
        print(f"   → 遗忘率: {best['forgetting']:.1f}%, 保持率: {best['retention']:.1f}%")

print("\n实验完成!")
