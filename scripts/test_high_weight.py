#!/usr/bin/env python3
"""
测试高权重遗忘策略
遗忘客户端权重占主导 (80%)
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*60)
print("测试高权重遗忘策略")
print("遗忘客户端权重: 80%, 其他客户端权重: 20%")
print("="*60)

# 加载数据
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='iid',
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

# 预训练
print("\n预训练 (5轮)...")
from src.federated import Server
model = ConvNet(num_classes=10, num_channels=1)
server = Server(model=model, device=device)

clients = []
for i in range(5):
    client_loader = fed_data.get_client_loader(i, batch_size=64)
    client = Client(i, ConvNet(num_classes=10, num_channels=1), client_loader, device, lr=0.05)
    clients.append(client)

for round_idx in range(5):
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

pretrain_results = server.evaluate(test_loader)
client0_before = evaluate_model(server.model, client0_loader, device=device)

print(f"预训练完成:")
print(f"  测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"  客户端0准确率: {client0_before['accuracy']:.2f}%")

# FedForget遗忘
print("\nFedForget遗忘 (5轮)...")
print("方法: dual_teacher + gradient_ascent")
print("参数: alpha=0.5, lambda_neg=1.0")
print("聚合权重: 遗忘客户端80%, 其他20%")

old_global_model_params = server.get_model_parameters()

fedforget_server = FedForgetServer(ConvNet(num_classes=10, num_channels=1), device=device)
fedforget_server.set_model_parameters(old_global_model_params)
fedforget_server.lambda_forget = 10.0  # 大幅提升遗忘客户端权重

unlearn_client = UnlearningClient(
    0, ConvNet(num_classes=10, num_channels=1), client0_loader, device, lr=0.01
)

unlearn_client.prepare_unlearning(
    global_model_params=old_global_model_params,
    local_model_params=None
)

fedforget_server.register_unlearning_client(0, current_round=0)
regular_clients = [clients[1], clients[2]]

for round_idx in range(5):
    global_params = fedforget_server.get_model_parameters()

    # 遗忘客户端: 双教师KD + 梯度上升
    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=2,
        method='dual_teacher',  # 会结合梯度上升(因为没有教师B)
        alpha=0.5,  # 50%正向学习, 50%梯度上升
        lambda_pos=1.0,
        lambda_neg=1.0,
        verbose=False
    )

    # 常规客户端
    client_models = [unlearn_client.get_model_parameters()]
    client_ids = [0]
    client_samples = [unlearn_client.num_samples]

    for client in regular_clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_ids.append(client.client_id)
        client_samples.append(client.num_samples)

    # 聚合 (lambda_forget=10.0会让遗忘客户端权重占主导)
    aggregated = fedforget_server.aggregate_with_fedforget(
        client_models, client_ids, client_samples, current_round=round_idx
    )
    fedforget_server.set_model_parameters(aggregated)

    test_results = fedforget_server.evaluate(test_loader)
    forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)
    print(f"Round {round_idx+1}/5 | Test: {test_results['accuracy']:.2f}% | "
          f"Forget: {forget_results['accuracy']:.2f}%")

# 最终评估
test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)

print("\n" + "="*60)
print("结果")
print("="*60)
print(f"预训练测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"遗忘后测试准确率: {test_results['accuracy']:.2f}% "
      f"(保持率: {test_results['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"遗忘数据准确率: {forget_results['accuracy']:.2f}%")

retain_ratio = test_results['accuracy'] / pretrain_results['accuracy']
forget_effective = forget_results['accuracy'] < 60.0

if retain_ratio > 0.90 and forget_effective:
    print("\n✅ 成功!")
elif retain_ratio > 0.90:
    print("\n⚠️ 性能保持良好, 遗忘效果不足")
elif forget_effective:
    print("\n⚠️ 遗忘有效, 性能下降过多")
else:
    print("\n两项指标都需改进")
