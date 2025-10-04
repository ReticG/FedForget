#!/usr/bin/env python3
"""
FedForget参数搜索
快速找到有效的超参数组合
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import json
from pathlib import Path

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"使用设备: {device}\n")

# 加载数据
print("加载数据...")
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=3,
    data_dist='iid',
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
unlearn_client_loader = fed_data.get_client_loader(0, batch_size=64)

# ============================================================
# 预训练一次,后续所有实验共用
# ============================================================
print("\n预训练全局模型 (5轮)...")
model = ConvNet(num_classes=10, num_channels=1)
server = Server(model=model, device=device)

clients = []
for i in range(3):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(
        client_id=i,
        model=ConvNet(num_classes=10, num_channels=1),
        data_loader=client_loader,
        device=device,
        lr=0.05
    )
    clients.append(client)

for round_idx in range(5):
    global_params = server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=3, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

pretrain_results = server.evaluate(test_loader)
pretrain_model = server.get_model_parameters()
client0_before = evaluate_model(server.model, unlearn_client_loader, device=device)

print(f"预训练完成:")
print(f"  测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"  客户端0数据准确率: {client0_before['accuracy']:.2f}%")

# ============================================================
# 参数搜索
# ============================================================
print("\n" + "="*70)
print("开始参数搜索")
print("="*70)

# 参数网格 (调整后 - alpha应该更大,让正向学习占主导)
param_grid = {
    'alpha': [0.8, 0.9, 0.95],  # 正向学习权重 (更大,让负向只起辅助作用)
    'lambda_neg': [0.5, 1.0, 2.0],  # 负向遗忘强度 (降低,防止过度破坏)
    'unlearn_epochs': [2],  # 遗忘训练轮数 (先固定,快速测试)
    'lambda_forget': [1.0],  # 服务器端权重 (先固定)
}

results = []
total_experiments = (len(param_grid['alpha']) *
                    len(param_grid['lambda_neg']) *
                    len(param_grid['unlearn_epochs']) *
                    len(param_grid['lambda_forget']))

print(f"总共{total_experiments}组参数需要测试\n")

exp_idx = 0

for alpha in param_grid['alpha']:
    for lambda_neg in param_grid['lambda_neg']:
        for unlearn_epochs in param_grid['unlearn_epochs']:
            for lambda_forget in param_grid['lambda_forget']:
                exp_idx += 1

                print(f"[{exp_idx}/{total_experiments}] 测试参数组合:")
                print(f"  alpha={alpha}, lambda_neg={lambda_neg}, " +
                      f"unlearn_epochs={unlearn_epochs}, lambda_forget={lambda_forget}")

                # 创建FedForgetServer
                fedforget_server = FedForgetServer(
                    model=ConvNet(num_classes=10, num_channels=1),
                    device=device
                )
                fedforget_server.set_model_parameters(pretrain_model)
                fedforget_server.lambda_forget = lambda_forget

                # 创建遗忘客户端
                unlearn_client = UnlearningClient(
                    client_id=0,
                    model=ConvNet(num_classes=10, num_channels=1),
                    data_loader=unlearn_client_loader,
                    device=device,
                    lr=0.01
                )

                global_params = fedforget_server.get_model_parameters()
                unlearn_client.prepare_unlearning(
                    global_model_params=global_params,
                    local_model_params=global_params  # 假设本地模型=全局模型
                )
                fedforget_server.register_unlearning_client(0, current_round=0)

                # 其他客户端
                regular_clients = [clients[1], clients[2]]

                # 遗忘训练 (3轮,快速测试)
                for round_idx in range(3):
                    global_params = fedforget_server.get_model_parameters()

                    # 遗忘客户端
                    unlearn_client.set_model_parameters(global_params)
                    unlearn_client.unlearning_train(
                        epochs=unlearn_epochs,
                        distill_temp=2.0,
                        alpha=alpha,
                        lambda_pos=1.0,
                        lambda_neg=lambda_neg,
                        verbose=False
                    )

                    # 常规客户端
                    client_models = [unlearn_client.get_model_parameters()]
                    client_ids = [0]
                    client_samples = [unlearn_client.num_samples]

                    for client in regular_clients:
                        client.set_model_parameters(global_params)
                        client.local_train(epochs=3, verbose=False)
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

                # 评估
                test_results = fedforget_server.evaluate(test_loader)
                forget_results = evaluate_model(
                    fedforget_server.model,
                    unlearn_client_loader,
                    device=device
                )

                # 计算指标
                test_acc = test_results['accuracy']
                forget_acc = forget_results['accuracy']
                retain_ratio = test_acc / pretrain_results['accuracy']
                forget_drop = (client0_before['accuracy'] - forget_acc) / client0_before['accuracy']

                # 成功标准
                success = (retain_ratio > 0.90 and forget_acc < 60.0)

                result = {
                    'alpha': alpha,
                    'lambda_neg': lambda_neg,
                    'unlearn_epochs': unlearn_epochs,
                    'lambda_forget': lambda_forget,
                    'test_acc': test_acc,
                    'forget_acc': forget_acc,
                    'retain_ratio': retain_ratio,
                    'forget_drop': forget_drop,
                    'success': success
                }
                results.append(result)

                # 打印结果
                status = "✅" if success else "⚠️"
                print(f"  {status} 测试准确率: {test_acc:.2f}% (保持率: {retain_ratio*100:.1f}%)")
                print(f"     遗忘准确率: {forget_acc:.2f}% (下降: {forget_drop*100:.1f}%)")
                print()

# ============================================================
# 分析结果
# ============================================================
print("="*70)
print("参数搜索完成 - 结果分析")
print("="*70)

# 按成功排序
results_sorted = sorted(results, key=lambda x: (x['success'], -x['retain_ratio'], x['forget_acc']), reverse=True)

print("\n最佳参数组合 (Top 5):")
print("-"*70)
for i, r in enumerate(results_sorted[:5]):
    status = "✅ 成功" if r['success'] else "⚠️ 部分成功"
    print(f"\n{i+1}. {status}")
    print(f"   参数: alpha={r['alpha']}, lambda_neg={r['lambda_neg']}, " +
          f"epochs={r['unlearn_epochs']}, lambda_forget={r['lambda_forget']}")
    print(f"   测试准确率: {r['test_acc']:.2f}% (保持率: {r['retain_ratio']*100:.1f}%)")
    print(f"   遗忘准确率: {r['forget_acc']:.2f}% (下降: {r['forget_drop']*100:.1f}%)")

# 保存结果
output_dir = Path('/home/featurize/work/GJC/fedforget/results')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'param_search_results.json'

with open(output_file, 'w') as f:
    json.dump(results_sorted, f, indent=2)

print(f"\n完整结果已保存至: {output_file}")

# 找到最佳参数
if any(r['success'] for r in results):
    best = next(r for r in results_sorted if r['success'])
    print("\n" + "="*70)
    print("✅ 找到有效参数组合!")
    print("="*70)
    print(f"最佳参数:")
    print(f"  alpha = {best['alpha']}")
    print(f"  lambda_neg = {best['lambda_neg']}")
    print(f"  unlearn_epochs = {best['unlearn_epochs']}")
    print(f"  lambda_forget = {best['lambda_forget']}")
    print(f"\n性能:")
    print(f"  测试准确率: {best['test_acc']:.2f}% (保持率: {best['retain_ratio']*100:.1f}%)")
    print(f"  遗忘准确率: {best['forget_acc']:.2f}%")
else:
    print("\n⚠️ 未找到完全成功的参数组合,需要进一步调整")
    print("建议:")
    print("  1. 增大lambda_neg (加强遗忘)")
    print("  2. 调整alpha (平衡正负向学习)")
    print("  3. 增加遗忘轮数")
