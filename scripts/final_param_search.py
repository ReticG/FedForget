#!/usr/bin/env python3
"""
最终参数搜索 - 精选关键配置

策略: 测试少量高质量配置，确保稳定性
目标: 找到保持率>90%, 遗忘率>30%的配置
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import time
import copy

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model, compute_class_accuracy

device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("FedForget最终参数搜索 - CIFAR-10")
print("="*80)

# ============================================================
# 数据和预训练（只做一次）
# ============================================================
print("\n准备数据和预训练...")
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

# 预训练
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
# 精选配置测试
# ============================================================
print("\n" + "="*80)
print("测试精选配置")
print("="*80)

# 精选8个配置
configs = [
    # (alpha, lambda_neg, lambda_forget, 描述)
    (0.98, 1.0, 1.5, "非常保守"),
    (0.97, 1.5, 1.5, "保守"),
    (0.96, 2.0, 1.5, "中等偏保守"),
    (0.95, 2.5, 1.5, "中等"),
    (0.95, 3.0, 1.5, "当前最佳"),
    (0.94, 3.0, 1.5, "中等偏激进"),
    (0.93, 3.5, 2.0, "激进"),
    (0.92, 4.0, 2.0, "非常激进"),
]

results = []

for idx, (alpha, lambda_neg, lambda_forget, desc) in enumerate(configs, 1):
    print(f"\n[{idx}/{len(configs)}] {desc}: alpha={alpha}, lambda_neg={lambda_neg}, lambda_forget={lambda_forget}")

    # 设置独立随机种子
    torch.manual_seed(42 + idx)
    np.random.seed(42 + idx)

    # 创建FedForget
    fedforget_server = FedForgetServer(
        model=ConvNet(num_classes=10, num_channels=3),
        device=device
    )
    fedforget_server.set_model_parameters(copy.deepcopy(pretrained_params))
    fedforget_server.lambda_forget = lambda_forget

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

    start_time = time.time()
    crashed = False

    # 遗忘训练
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

        # 检测崩溃
        if round_idx == 2:  # 第3轮检查
            temp_test = fedforget_server.evaluate(test_loader)
            if temp_test['accuracy'] < 50.0:
                print(f"  ⚠️ 崩溃! Round 3 Test={temp_test['accuracy']:.2f}%")
                crashed = True
                break

    exec_time = time.time() - start_time

    if crashed:
        print(f"  ✗ 配置失败")
        results.append({
            'config': desc,
            'alpha': alpha,
            'lambda_neg': lambda_neg,
            'lambda_forget': lambda_forget,
            'status': 'CRASHED',
            'test_acc': 0,
            'forget_acc': 0,
            'retention': 0,
            'forgetting': 0,
            'time': exec_time
        })
    else:
        test_results = fedforget_server.evaluate(test_loader)
        forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)

        retention = test_results['accuracy'] / pretrain_test['accuracy'] * 100
        forgetting = (pretrain_forget['accuracy'] - forget_results['accuracy']) / pretrain_forget['accuracy'] * 100

        print(f"  ✓ 测试: {test_results['accuracy']:.2f}%, 遗忘: {forget_results['accuracy']:.2f}%")
        print(f"    保持率: {retention:.1f}%, 遗忘率: {forgetting:.1f}%, 耗时: {exec_time:.1f}s")

        results.append({
            'config': desc,
            'alpha': alpha,
            'lambda_neg': lambda_neg,
            'lambda_forget': lambda_forget,
            'status': 'OK',
            'test_acc': test_results['accuracy'],
            'forget_acc': forget_results['accuracy'],
            'retention': retention,
            'forgetting': forgetting,
            'time': exec_time
        })

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "="*80)
print("最终结果汇总")
print("="*80)

print(f"\n预训练基线: Test {pretrain_test['accuracy']:.2f}%, Forget {pretrain_forget['accuracy']:.2f}%")
print()

valid_results = [r for r in results if r['status'] == 'OK']
crashed_results = [r for r in results if r['status'] == 'CRASHED']

print(f"成功配置: {len(valid_results)}/{len(results)}")
print(f"崩溃配置: {len(crashed_results)}/{len(results)}")

if len(valid_results) > 0:
    print("\n" + "-"*80)
    print(f"{'配置':<15} {'Alpha':<7} {'λ_neg':<7} {'Test%':<8} {'Forget%':<9} {'保持%':<8} {'遗忘%':<8} {'达标':<6}")
    print("-"*80)

    for r in valid_results:
        goal_met = r['retention'] > 90.0 and r['forgetting'] > 30.0
        marker = "✅" if goal_met else ""

        print(f"{r['config']:<15} {r['alpha']:<7.2f} {r['lambda_neg']:<7.1f} "
              f"{r['test_acc']:<8.2f} {r['forget_acc']:<9.2f} "
              f"{r['retention']:<8.1f} {r['forgetting']:<8.1f} {marker:<6}")

    print("="*80)

    # 最佳配置
    best_forgetting = max(valid_results, key=lambda x: x['forgetting'])
    best_balanced = max([r for r in valid_results if r['retention'] > 90],
                       key=lambda x: x['forgetting'], default=None)

    print("\n🏆 推荐配置:")
    print(f"\n1. 最大遗忘率:")
    print(f"   {best_forgetting['config']}: alpha={best_forgetting['alpha']}, lambda_neg={best_forgetting['lambda_neg']}")
    print(f"   → 遗忘率 {best_forgetting['forgetting']:.1f}%, 保持率 {best_forgetting['retention']:.1f}%")

    if best_balanced:
        print(f"\n2. 最佳平衡 (保持率>90%):")
        print(f"   {best_balanced['config']}: alpha={best_balanced['alpha']}, lambda_neg={best_balanced['lambda_neg']}")
        print(f"   → 遗忘率 {best_balanced['forgetting']:.1f}%, 保持率 {best_balanced['retention']:.1f}%")

    # 保存结果
    import csv
    import os
    os.makedirs('/home/featurize/work/GJC/fedforget/results', exist_ok=True)

    with open('/home/featurize/work/GJC/fedforget/results/final_param_search.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['config', 'alpha', 'lambda_neg', 'lambda_forget',
                                                'status', 'test_acc', 'forget_acc', 'retention',
                                                'forgetting', 'time'])
        writer.writeheader()
        writer.writerows(results)

    print("\n✓ 结果已保存到: results/final_param_search.csv")

print("\n实验完成!")
