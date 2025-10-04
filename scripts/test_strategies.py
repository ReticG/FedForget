#!/usr/bin/env python3
"""
测试不同的FedForget策略
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
print("测试FedForget不同策略")
print("="*60)

# 加载数据
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='iid',
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)

# ============================================================
# 策略0: 预训练
# ============================================================
print("\n[策略0] 预训练 (10轮FedAvg)")
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

    # 所有客户端都参与
    for client in clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=3, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = server.aggregate(client_models, client_weights)
    server.set_model_parameters(aggregated)

pretrain_results = server.evaluate(test_loader)
pretrain_model = server.get_model_parameters()

# 评估客户端0的数据
client0_loader = fed_data.get_client_loader(0, batch_size=128)
client0_before = evaluate_model(server.model, client0_loader, device=device)

print(f"预训练完成 - 测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"客户端0数据准确率: {client0_before['accuracy']:.2f}%")

# ============================================================
# 策略1: 简单排除 - 遗忘客户端不参与聚合
# ============================================================
print("\n[策略1] 简单排除策略 - 客户端0不参与聚合")
server1 = Server(model=ConvNet(num_classes=10, num_channels=1), device=device)
server1.set_model_parameters(pretrain_model)

for round_idx in range(10):
    global_params = server1.get_model_parameters()
    client_models = []
    client_weights = []

    # 只有客户端1-4参与
    for i in [1, 2, 3, 4]:
        clients[i].set_model_parameters(global_params)
        clients[i].local_train(epochs=3, verbose=False)
        client_models.append(clients[i].get_model_parameters())
        client_weights.append(clients[i].num_samples)

    aggregated = server1.aggregate(client_models, client_weights)
    server1.set_model_parameters(aggregated)

strat1_test = server1.evaluate(test_loader)
strat1_forget = evaluate_model(server1.model, client0_loader, device=device)

print(f"结果:")
print(f"  测试准确率: {strat1_test['accuracy']:.2f}% (保持率: {strat1_test['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"  遗忘数据准确率: {strat1_forget['accuracy']:.2f}%")

# ============================================================
# 策略2: 负权重 - 给遗忘客户端负权重
# ============================================================
print("\n[策略2] 负权重策略 - 客户端0参与,但权重为负")
server2 = Server(model=ConvNet(num_classes=10, num_channels=1), device=device)
server2.set_model_parameters(pretrain_model)

for round_idx in range(10):
    global_params = server2.get_model_parameters()
    client_models = []
    client_weights = []

    # 所有客户端参与
    for i in range(5):
        clients[i].set_model_parameters(global_params)
        clients[i].local_train(epochs=3, verbose=False)
        client_models.append(clients[i].get_model_parameters())

        if i == 0:
            client_weights.append(-1000)  # 负权重
        else:
            client_weights.append(clients[i].num_samples)

    aggregated = server2.aggregate(client_models, client_weights)
    server2.set_model_parameters(aggregated)

strat2_test = server2.evaluate(test_loader)
strat2_forget = evaluate_model(server2.model, client0_loader, device=device)

print(f"结果:")
print(f"  测试准确率: {strat2_test['accuracy']:.2f}% (保持率: {strat2_test['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"  遗忘数据准确率: {strat2_forget['accuracy']:.2f}%")

# ============================================================
# 总结
# ============================================================
print("\n" + "="*60)
print("策略对比总结")
print("="*60)
print(f"{'策略':<15} {'测试准确率':>12} {'遗忘准确率':>12} {'性能保持':>10}")
print("-"*60)
print(f"{'预训练':<15} {pretrain_results['accuracy']:>11.2f}% {client0_before['accuracy']:>11.2f}% {'100.0%':>10}")
print(f"{'简单排除':<15} {strat1_test['accuracy']:>11.2f}% {strat1_forget['accuracy']:>11.2f}% {strat1_test['accuracy']/pretrain_results['accuracy']*100:>9.1f}%")
print(f"{'负权重':<15} {strat2_test['accuracy']:>11.2f}% {strat2_forget['accuracy']:>11.2f}% {strat2_test['accuracy']/pretrain_results['accuracy']*100:>9.1f}%")
print("="*60)

# 成功评估
print("\n评估标准: 遗忘数据准确率<50%, 测试准确率保持>90%")
strategies = {
    '简单排除': (strat1_test['accuracy'], strat1_forget['accuracy']),
    '负权重': (strat2_test['accuracy'], strat2_forget['accuracy'])
}

for name, (test_acc, forget_acc) in strategies.items():
    retain_ratio = test_acc / pretrain_results['accuracy']
    forget_effective = forget_acc < 50.0

    status = "✅" if (retain_ratio > 0.9 and forget_effective) else "⚠️"
    print(f"{status} {name}: ", end="")

    if retain_ratio > 0.9 and forget_effective:
        print("成功!")
    elif retain_ratio > 0.9:
        print("性能保持良好,但遗忘不足")
    elif forget_effective:
        print("遗忘有效,但性能下降过多")
    else:
        print("需要改进")
