#!/usr/bin/env python3
"""
测试修正后的FedForget - 教师A为旧全局模型
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
print("测试修正后的FedForget")
print("核心修正: 教师A = 遗忘前的旧全局模型 (固定不变)")
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

# ============================================================
# 步骤1: 预训练
# ============================================================
print("\n步骤1: 预训练 (10轮)...")
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

# ============================================================
# 步骤2: FedForget遗忘 (关键修正)
# ============================================================
print("\n步骤2: FedForget遗忘...")
print("参数: alpha=0.9, lambda_neg=3.0, epochs=3")

# 保存遗忘前的旧全局模型 (作为教师A,在整个遗忘过程中固定不变)
old_global_model_params = server.get_model_parameters()
print(f"✓ 已保存旧全局模型作为教师A (固定不变)")

# 创建FedForgetServer
fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=1),
    device=device
)
fedforget_server.set_model_parameters(old_global_model_params)
fedforget_server.lambda_forget = 1.5

# 创建遗忘客户端
unlearn_client = UnlearningClient(
    client_id=0,
    model=ConvNet(num_classes=10, num_channels=1),
    data_loader=client0_loader,
    device=device,
    lr=0.01
)

# 只在遗忘开始时准备教师A (使用旧全局模型)
unlearn_client.prepare_unlearning(
    global_model_params=old_global_model_params,  # 教师A = 旧全局模型
    local_model_params=None  # 教师B = None (只用教师A)
)
print(f"✓ 遗忘客户端已准备,教师A已设置")

fedforget_server.register_unlearning_client(0, current_round=0)

# 其他常规客户端
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

# 遗忘训练10轮
print(f"\n开始遗忘训练 (10轮)...")
for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

    # 遗忘客户端: 双教师KD
    # 关键: 不更新教师A! 教师A始终是old_global_model
    unlearn_client.set_model_parameters(global_params)
    unlearn_client.unlearning_train(
        epochs=3,  # 每轮训练3个epoch
        distill_temp=2.0,
        alpha=0.9,  # 90%正向学习(从教师A), 10%负向遗忘
        lambda_pos=1.0,
        lambda_neg=3.0,  # 负向遗忘强度
        verbose=False
    )

    # 选择2个常规客户端参与
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

    # 评估
    if (round_idx + 1) % 2 == 0:
        test_results = fedforget_server.evaluate(test_loader)
        forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)
        print(f"Round {round_idx+1}/10 | Test: {test_results['accuracy']:.2f}% | "
              f"Forget: {forget_results['accuracy']:.2f}%")

# ============================================================
# 最终评估
# ============================================================
test_results = fedforget_server.evaluate(test_loader)
forget_results = evaluate_model(fedforget_server.model, client0_loader, device=device)

print("\n" + "="*60)
print("最终结果")
print("="*60)
print(f"预训练:")
print(f"  测试准确率: {pretrain_results['accuracy']:.2f}%")
print(f"  客户端0准确率: {client0_before['accuracy']:.2f}%")
print(f"\n遗忘后:")
print(f"  测试准确率: {test_results['accuracy']:.2f}% "
      f"(保持率: {test_results['accuracy']/pretrain_results['accuracy']*100:.1f}%)")
print(f"  客户端0准确率: {forget_results['accuracy']:.2f}%")

# 计算遗忘效果
forget_drop = client0_before['accuracy'] - forget_results['accuracy']
forget_ratio = forget_drop / client0_before['accuracy']

print(f"\n遗忘效果:")
print(f"  客户端0准确率下降: {forget_drop:.2f}% (下降比例: {forget_ratio*100:.1f}%)")

# 成功评估
retain_ratio = test_results['accuracy'] / pretrain_results['accuracy']
forget_effective = forget_results['accuracy'] < 60.0

print("\n" + "="*60)
if retain_ratio > 0.90 and forget_effective:
    print("✅ 成功! 性能保持>90%, 遗忘数据准确率<60%")
    print(f"   测试准确率保持: {retain_ratio*100:.1f}%")
    print(f"   遗忘数据准确率: {forget_results['accuracy']:.2f}%")
elif retain_ratio > 0.90:
    print("⚠️ 性能保持良好, 但遗忘效果不足")
    print(f"   遗忘数据准确率: {forget_results['accuracy']:.2f}% (目标: <60%)")
    print(f"   建议: 增大lambda_neg或增加遗忘轮数")
elif forget_effective:
    print("⚠️ 遗忘有效, 但性能下降过多")
    print(f"   测试准确率保持: {retain_ratio*100:.1f}% (目标: >90%)")
    print(f"   建议: 增大alpha或减少遗忘强度")
else:
    print("❌ 需要调整参数")
    print(f"   测试准确率保持: {retain_ratio*100:.1f}%")
    print(f"   遗忘数据准确率: {forget_results['accuracy']:.2f}%")

print("="*60)
