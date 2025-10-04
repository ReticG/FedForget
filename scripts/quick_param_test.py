#!/usr/bin/env python3
"""
快速测试单个参数组合
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

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*60)
print("快速测试FedForget - alpha=0.95, lambda_neg=5.0")
print("="*60)

# 加载数据
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=3,
    data_dist='iid',
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
unlearn_client_loader = fed_data.get_client_loader(0, batch_size=64)

# 预训练
print("\n预训练 (3轮)...")
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

for round_idx in range(3):
    global_params = server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)  # 减少epoch
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

pretrain_results = server.evaluate(test_loader)
pretrain_model = server.get_model_parameters()
client0_before = evaluate_model(server.model, unlearn_client_loader, device=device)

print(f"预训练完成 - 测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"客户端0数据准确率: {client0_before['accuracy']:.2f}%")

# FedForget遗忘
print("\nFedForget遗忘 (3轮)...")
print("参数: alpha=0.95, lambda_neg=5.0, epochs=1")

fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=1),
    device=device
)
fedforget_server.set_model_parameters(pretrain_model)
fedforget_server.lambda_forget = 1.0

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
    local_model_params=global_params
)
fedforget_server.register_unlearning_client(0, current_round=0)

regular_clients = [clients[1], clients[2]]

for round_idx in range(3):
    global_params = fedforget_server.get_model_parameters()

    # 遗忘客户端: 双教师KD
    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=1,  # 只训练1个epoch
        distill_temp=2.0,
        alpha=0.95,  # 95%正向学习, 5%负向遗忘
        lambda_pos=1.0,
        lambda_neg=5.0,  # 增大负向遗忘强度
        verbose=True
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

    # 聚合
    aggregated = fedforget_server.aggregate_with_fedforget(
        client_models,
        client_ids,
        client_samples,
        current_round=round_idx
    )
    fedforget_server.set_model_parameters(aggregated)

    # 评估
    test_results = fedforget_server.evaluate(test_loader)
    forget_results = evaluate_model(fedforget_server.model, unlearn_client_loader, device=device)
    print(f"Round {round_idx+1}/3 | Test: {test_results['accuracy']:.2f}% | Forget: {forget_results['accuracy']:.2f}%")

# 最终评估
test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, unlearn_client_loader, device=device)

print("\n" + "="*60)
print("结果")
print("="*60)
print(f"预训练测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"遗忘后测试准确率: {test_results['accuracy']:.2f}% (保持率: {test_results['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"遗忘数据准确率: {forget_results['accuracy']:.2f}%")

retain_ratio = test_results['accuracy'] / pretrain_results['accuracy']
forget_effective = forget_results['accuracy'] < 60.0

if retain_ratio > 0.90 and forget_effective:
    print("\n✅ 成功! 性能保持>90%, 遗忘数据准确率<60%")
elif retain_ratio > 0.90:
    print("\n⚠️ 性能保持良好, 但遗忘效果不足")
    print(f"   建议: 增大lambda_neg (当前1.0 -> 尝试2.0-5.0)")
elif forget_effective:
    print("\n⚠️ 遗忘有效, 但性能下降过多")
    print(f"   建议: 增大alpha (当前0.95 -> 尝试0.98)")
else:
    print("\n❌ 需要调整参数")
