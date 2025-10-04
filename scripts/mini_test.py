#!/usr/bin/env python3
"""
极简FedForget测试 - 快速验证遗忘效果
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np

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
print(f"使用设备: {device}")

# 加载数据 (仅3个客户端, 减少数据量)
print("\n加载数据...")
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=3,  # 只用3个客户端
    data_dist='iid',
    data_root='/home/featurize/data'
)

# 步骤1: 快速预训练 (5轮)
print("\n步骤1: 预训练 (FedAvg, 5轮)")
model = ConvNet(num_classes=10, num_channels=1)
server = Server(model=model, device=device)

clients = []
for i in range(3):
    client_loader = fed_data.get_client_loader(i, batch_size=64, shuffle=True)  # 增大batch_size
    client = Client(
        client_id=i,
        model=ConvNet(num_classes=10, num_channels=1),
        data_loader=client_loader,
        device=device,
        lr=0.05  # 增大学习率
    )
    clients.append(client)

test_loader = fed_data.get_test_loader(batch_size=256)

# 预训练5轮
for round_idx in range(5):
    global_params = server.get_model_parameters()

    client_models = []
    client_weights = []

    for client in clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=3, verbose=False)  # 减少本地轮数
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

    if (round_idx + 1) % 2 == 0:
        test_results = server.evaluate(test_loader)
        print(f"Round {round_idx+1}/5 | Test Acc: {test_results['accuracy']:.2f}%")

final_results = server.evaluate(test_loader)
print(f"\n预训练完成 - 测试准确率: {final_results['accuracy']:.2f}%")

# 步骤2: FedForget遗忘 (客户端0)
print("\n步骤2: FedForget遗忘 (客户端0, 5轮)")

fedforget_server = FedForgetServer(model=ConvNet(num_classes=10, num_channels=1), device=device)
fedforget_server.set_model_parameters(server.get_model_parameters())
fedforget_server.lambda_forget = 1.5  # 适中的遗忘客户端权重提升

# 创建遗忘客户端
unlearn_client_loader = fed_data.get_client_loader(0, batch_size=64)
unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=1),
    data_loader=unlearn_client_loader,
    device=device,
    lr=0.01
)

global_params = fedforget_server.get_model_parameters()
unlearn_client.prepare_unlearning(global_model_params=global_params)
fedforget_server.register_unlearning_client(0, current_round=0)

# 其他客户端
regular_clients = [clients[1], clients[2]]

# 遗忘5轮
for round_idx in range(5):
    global_params = fedforget_server.get_model_parameters()

    # 遗忘客户端: 双教师知识蒸馏
    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=5,  # 充分训练
        distill_temp=2.0,
        alpha=0.5,  # 平衡正向学习和负向遗忘
        lambda_pos=1.0,
        lambda_neg=2.0,  # 负向遗忘权重稍大
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
    if (round_idx + 1) % 2 == 0:
        test_results = fedforget_server.evaluate(test_loader)
        forget_results = evaluate_model(fedforget_server.model, unlearn_client_loader, device=device)
        print(f"Round {round_idx+1}/5 | Test: {test_results['accuracy']:.2f}% | Forget: {forget_results['accuracy']:.2f}%")

# 最终评估
test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, unlearn_client_loader, device=device)

print("\n" + "="*60)
print("最终结果")
print("="*60)
print(f"预训练准确率: {final_results['accuracy']:.2f}%")
print(f"遗忘后测试准确率: {test_results['accuracy']:.2f}%")
print(f"遗忘数据准确率: {forget_results['accuracy']:.2f}%")
print(f"性能保持率: {test_results['accuracy'] / final_results['accuracy'] * 100:.2f}%")
print("="*60)

# 成功标准
retain_ratio = test_results['accuracy'] / final_results['accuracy']
forget_effective = forget_results['accuracy'] < 50.0

print()
if retain_ratio > 0.90 and forget_effective:
    print("✅ 成功! 性能保持>90%, 遗忘数据准确率<50%")
elif retain_ratio > 0.90:
    print("⚠️ 部分成功: 性能保持良好, 但遗忘效果不足")
elif forget_effective:
    print("⚠️ 部分成功: 遗忘有效, 但性能下降过多")
else:
    print("❌ 失败: 性能和遗忘效果都不理想")
