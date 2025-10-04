#!/usr/bin/env python3
"""
测试简单排除策略 - 最简单的遗忘方法
遗忘客户端不参与聚合,让其他客户端稀释它的贡献
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.utils.metrics import evaluate_model

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*60)
print("测试简单排除策略")
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
print("\n预训练 (所有5个客户端, 10轮)...")
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

pretrain_results = server.evaluate(test_loader)
client0_before = evaluate_model(server.model, client0_loader, device=device)

print(f"预训练完成:")
print(f"  测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"  客户端0数据准确率: {client0_before['accuracy']:.2f}%")

# 简单排除遗忘
print("\n遗忘 (排除客户端0, 继续训练10轮)...")
pretrain_model = server.get_model_parameters()

for round_idx in range(10):
    global_params = server.get_model_parameters()
    client_models = []
    client_weights = []

    # 只有客户端1-4参与
    for i in [1, 2, 3, 4]:
        clients[i].set_model_parameters(global_params)
        clients[i].local_train(epochs=2, verbose=False)
        client_models.append(clients[i].get_model_parameters())
        client_weights.append(clients[i].num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

    if (round_idx + 1) % 5 == 0:
        test_results = server.evaluate(test_loader)
        forget_results = evaluate_model(server.model, client0_loader, device=device)
        print(f"Round {round_idx+1}/10 | Test: {test_results['accuracy']:.2f}% | Forget: {forget_results['accuracy']:.2f}%")

# 最终评估
test_results = server.evaluate(test_loader)
forget_results = evaluate_model(server.model, client0_loader, device=device)

print("\n" + "="*60)
print("结果")
print("="*60)
print(f"预训练测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"预训练客户端0准确率: {client0_before['accuracy']:.2f}%")
print(f"\n遗忘后测试准确率: {test_results['accuracy']:.2f}% (保持率: {test_results['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"遗忘后客户端0准确率: {forget_results['accuracy']:.2f}%")

forget_drop_ratio = (client0_before['accuracy'] - forget_results['accuracy']) / client0_before['accuracy']
print(f"\n客户端0准确率下降: {forget_drop_ratio*100:.1f}%")

# 成功评估
retain_ratio = test_results['accuracy'] / pretrain_results['accuracy']
forget_effective = forget_results['accuracy'] < 60.0

print("\n评估:")
if retain_ratio > 0.95 and forget_effective:
    print("✅ 成功! 性能保持>95%, 遗忘数据准确率<60%")
elif retain_ratio > 0.95:
    print("⚠️ 性能保持良好, 但遗忘效果不足")
    print("   简单排除策略的局限: 只能稀释贡献,不能主动遗忘")
elif forget_effective:
    print("⚠️ 遗忘有效, 但性能下降过多")
else:
    print("❌ 两个指标都不理想")

print("\n💡 启示:")
print("   简单排除策略虽然简单,但遗忘效果有限")
print("   需要更主动的遗忘方法(如梯度上升、知识蒸馏)")
