#!/usr/bin/env python3
"""
调试FedForget崩溃问题

问题: 之前alpha=0.95, lambda_neg=3.0成功,现在却崩溃
可能原因:
1. 随机种子导致数据分布不同
2. 参数设置有误
3. 代码逻辑问题

测试:
1. 完全复现之前成功的实验
2. 逐步增加lambda_neg,找到崩溃点
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

# 固定随机种子
torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("调试FedForget崩溃问题")
print("="*80)

# 加载数据
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
print("\n预训练...")
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

print(f"预训练完成:")
print(f"  测试准确率: {pretrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {pretrain_forget['accuracy']:.2f}%")

pretrained_params = server.get_model_parameters()

# 测试1: 完全复现之前的成功配置
print("\n" + "="*80)
print("测试1: alpha=0.95, lambda_neg=3.0 (之前成功的配置)")
print("="*80)

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

for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

    # 遗忘客户端
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

    # 聚合
    aggregated = fedforget_server.aggregate_with_fedforget(
        client_models,
        client_ids,
        client_samples,
        current_round=round_idx
    )
    fedforget_server.set_model_parameters(aggregated)

    # 每轮评估
    test_results = fedforget_server.evaluate(test_loader)
    forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)
    print(f"Round {round_idx+1}/10 | Test: {test_results['accuracy']:.2f}% | Forget: {forget_results['accuracy']:.2f}%")

test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)

retention = test_results['accuracy'] / pretrain_test['accuracy']
forgetting = (pretrain_forget['accuracy'] - forget_results['accuracy']) / pretrain_forget['accuracy']

print(f"\n最终结果:")
print(f"  测试准确率: {test_results['accuracy']:.2f}% (保持率: {retention*100:.1f}%)")
print(f"  遗忘准确率: {forget_results['accuracy']:.2f}% (遗忘率: {forgetting*100:.1f}%)")

if test_results['accuracy'] < 50.0:
    print("\n❌ 模型崩溃!")
else:
    print("\n✅ 成功!")

# 测试2: 更保守的参数
print("\n" + "="*80)
print("测试2: alpha=0.98, lambda_neg=1.0 (更保守)")
print("="*80)

fedforget_server2 = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=3),
    device=device
)
fedforget_server2.set_model_parameters(pretrained_params)
fedforget_server2.lambda_forget = 1.5

unlearn_client2 = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=3),
    data_loader=client0_loader,
    device=device,
    lr=0.005
)

unlearn_client2.prepare_unlearning(
    global_model_params=pretrained_params,
    local_model_params=None
)

fedforget_server2.register_unlearning_client(0, current_round=0)

for round_idx in range(10):
    global_params = fedforget_server2.get_model_parameters()

    unlearn_client2.set_model_parameters(global_params)
    unlearn_client2.unlearning_train(
        epochs=2,
        method='dual_teacher',
        distill_temp=2.0,
        alpha=0.98,
        lambda_pos=1.0,
        lambda_neg=1.0,
        verbose=False
    )

    selected_regular = np.random.choice(regular_clients, 2, replace=False)

    client_models = [unlearn_client2.get_model_parameters()]
    client_ids = [0]
    client_samples = [unlearn_client2.num_samples]

    for client in selected_regular:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_ids.append(client.client_id)
        client_samples.append(client.num_samples)

    aggregated = fedforget_server2.aggregate_with_fedforget(
        client_models,
        client_ids,
        client_samples,
        current_round=round_idx
    )
    fedforget_server2.set_model_parameters(aggregated)

    test_results = fedforget_server2.evaluate(test_loader)
    forget_results = evaluate_model(fedforget_server2.model, client0_loader, device=device)
    print(f"Round {round_idx+1}/10 | Test: {test_results['accuracy']:.2f}% | Forget: {forget_results['accuracy']:.2f}%")

test_results = fedforget_server2.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server2.model, client0_loader, device=device)

retention = test_results['accuracy'] / pretrain_test['accuracy']
forgetting = (pretrain_forget['accuracy'] - forget_results['accuracy']) / pretrain_forget['accuracy']

print(f"\n最终结果:")
print(f"  测试准确率: {test_results['accuracy']:.2f}% (保持率: {retention*100:.1f}%)")
print(f"  遗忘准确率: {forget_results['accuracy']:.2f}% (遗忘率: {forgetting*100:.1f}%)")

if test_results['accuracy'] < 50.0:
    print("\n❌ 模型崩溃!")
else:
    print("\n✅ 成功!")

print("\n实验完成!")
