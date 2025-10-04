#!/usr/bin/env python3
"""
MIA评估: 对比Retrain, Fine-tuning, FedForget的隐私保护效果

评估指标:
1. 攻击成功率 (ASR): 越低越好 (接近50%=随机猜测)
2. AUC: 越低越好 (接近0.5=无区分能力)
3. 遗忘数据损失: 应该接近测试数据
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import copy

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model
from src.utils.mia import SimpleMIA, evaluate_unlearning_privacy

torch.manual_seed(42)
np.random.seed(42)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

print("="*80)
print("MIA隐私评估: Retrain vs Fine-tuning vs FedForget")
print("="*80)

# ============================================================
# 数据准备
# ============================================================
print("\n[1/4] 数据加载...")

fed_data = load_federated_data(
    dataset_name='cifar10',
    num_clients=5,
    data_dist='noniid',
    dirichlet_alpha=0.5,
    data_root='/home/featurize/data'
)

test_loader = fed_data.get_test_loader(batch_size=256)
client0_loader = fed_data.get_client_loader(0, batch_size=64)

# 为MIA准备保留数据集 (client 1-4)
retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in range(1, 5)]

# 合并保留数据用于MIA
from torch.utils.data import ConcatDataset, DataLoader
retain_datasets = [fed_data.get_client_dataset(i) for i in range(1, 5)]
retain_combined = ConcatDataset(retain_datasets)
retain_loader_combined = DataLoader(retain_combined, batch_size=64, shuffle=False)

print(f"✓ 数据加载完成")
print(f"  遗忘数据 (Client 0): {len(client0_loader.dataset)} samples")
print(f"  保留数据 (Client 1-4): {len(retain_loader_combined.dataset)} samples")
print(f"  测试数据: {len(test_loader.dataset)} samples")

# ============================================================
# 预训练
# ============================================================
print("\n[2/4] 预训练模型...")

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
# 评估1: 预训练模型 (基线)
# ============================================================
print("\n[3/4] 评估各方法...")
print("\n" + "-"*80)
print("方法1: 预训练模型 (未遗忘)")
print("-"*80)

mia_results = {}

pretrain_mia = evaluate_unlearning_privacy(
    server.model,
    forget_loader=client0_loader,
    retain_loader=retain_loader_combined,
    test_loader=test_loader,
    device=device
)

mia_results['pretrain'] = pretrain_mia

print(f"\nForget vs Test (理想: 接近50%准确率):")
print(f"  攻击准确率: {pretrain_mia['forget_vs_test']['accuracy']:.2f}%")
print(f"  AUC: {pretrain_mia['forget_vs_test']['auc']:.4f}")
print(f"  Forget损失: {pretrain_mia['forget_vs_test']['forget_loss']:.4f}")
print(f"  Test损失: {pretrain_mia['forget_vs_test']['test_loss']:.4f}")

print(f"\nForget vs Retain (Forget应该像Retain):")
print(f"  攻击准确率: {pretrain_mia['forget_vs_retain']['accuracy']:.2f}%")
print(f"  AUC: {pretrain_mia['forget_vs_retain']['auc']:.4f}")

# ============================================================
# 评估2: Retrain
# ============================================================
print("\n" + "-"*80)
print("方法2: Retrain (重新训练)")
print("-"*80)

retrain_server = Server(model=ConvNet(num_classes=10, num_channels=3), device=device)
regular_clients = [clients[1], clients[2], clients[3], clients[4]]

for round_idx in range(20):
    global_params = retrain_server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in regular_clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = retrain_server.aggregate(client_models, client_weights)
    retrain_server.set_model_parameters(aggregated)

retrain_test = retrain_server.evaluate(test_loader)
retrain_forget = evaluate_model(retrain_server.model, client0_loader, device=device)

print(f"✓ Retrain完成")
print(f"  测试准确率: {retrain_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {retrain_forget['accuracy']:.2f}%")

retrain_mia = evaluate_unlearning_privacy(
    retrain_server.model,
    forget_loader=client0_loader,
    retain_loader=retain_loader_combined,
    test_loader=test_loader,
    device=device
)

mia_results['retrain'] = retrain_mia

print(f"\nForget vs Test:")
print(f"  攻击准确率: {retrain_mia['forget_vs_test']['accuracy']:.2f}%")
print(f"  AUC: {retrain_mia['forget_vs_test']['auc']:.4f}")
print(f"  Forget损失: {retrain_mia['forget_vs_test']['forget_loss']:.4f}")
print(f"  Test损失: {retrain_mia['forget_vs_test']['test_loss']:.4f}")

print(f"\nForget vs Retain:")
print(f"  攻击准确率: {retrain_mia['forget_vs_retain']['accuracy']:.2f}%")
print(f"  AUC: {retrain_mia['forget_vs_retain']['auc']:.4f}")

# ============================================================
# 评估3: Fine-tuning
# ============================================================
print("\n" + "-"*80)
print("方法3: Fine-tuning")
print("-"*80)

finetune_server = Server(model=ConvNet(num_classes=10, num_channels=3), device=device)
finetune_server.set_model_parameters(copy.deepcopy(pretrained_params))

for round_idx in range(10):
    global_params = finetune_server.get_model_parameters()
    client_models = []
    client_weights = []

    for client in regular_clients:
        client.set_model_parameters(global_params)
        client.local_train(epochs=2, verbose=False)
        client_models.append(client.get_model_parameters())
        client_weights.append(client.num_samples)

    aggregated = finetune_server.aggregate(client_models, client_weights)
    finetune_server.set_model_parameters(aggregated)

finetune_test = finetune_server.evaluate(test_loader)
finetune_forget = evaluate_model(finetune_server.model, client0_loader, device=device)

print(f"✓ Fine-tuning完成")
print(f"  测试准确率: {finetune_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {finetune_forget['accuracy']:.2f}%")

finetune_mia = evaluate_unlearning_privacy(
    finetune_server.model,
    forget_loader=client0_loader,
    retain_loader=retain_loader_combined,
    test_loader=test_loader,
    device=device
)

mia_results['finetune'] = finetune_mia

print(f"\nForget vs Test:")
print(f"  攻击准确率: {finetune_mia['forget_vs_test']['accuracy']:.2f}%")
print(f"  AUC: {finetune_mia['forget_vs_test']['auc']:.4f}")
print(f"  Forget损失: {finetune_mia['forget_vs_test']['forget_loss']:.4f}")
print(f"  Test损失: {finetune_mia['forget_vs_test']['test_loss']:.4f}")

print(f"\nForget vs Retain:")
print(f"  攻击准确率: {finetune_mia['forget_vs_retain']['accuracy']:.2f}%")
print(f"  AUC: {finetune_mia['forget_vs_retain']['auc']:.4f}")

# ============================================================
# 评估4: FedForget (最佳配置)
# ============================================================
print("\n" + "-"*80)
print("方法4: FedForget (alpha=0.95, lambda_neg=3.0)")
print("-"*80)

fedforget_server = FedForgetServer(
    model=ConvNet(num_classes=10, num_channels=3),
    device=device
)
fedforget_server.set_model_parameters(copy.deepcopy(pretrained_params))
fedforget_server.lambda_forget = 1.5

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

for round_idx in range(10):
    global_params = fedforget_server.get_model_parameters()

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

fedforget_test = fedforget_server.evaluate(test_loader)
fedforget_forget = evaluate_model(fedforget_server.model, client0_loader, device=device)

print(f"✓ FedForget完成")
print(f"  测试准确率: {fedforget_test['accuracy']:.2f}%")
print(f"  遗忘数据准确率: {fedforget_forget['accuracy']:.2f}%")

fedforget_mia = evaluate_unlearning_privacy(
    fedforget_server.model,
    forget_loader=client0_loader,
    retain_loader=retain_loader_combined,
    test_loader=test_loader,
    device=device
)

mia_results['fedforget'] = fedforget_mia

print(f"\nForget vs Test:")
print(f"  攻击准确率: {fedforget_mia['forget_vs_test']['accuracy']:.2f}%")
print(f"  AUC: {fedforget_mia['forget_vs_test']['auc']:.4f}")
print(f"  Forget损失: {fedforget_mia['forget_vs_test']['forget_loss']:.4f}")
print(f"  Test损失: {fedforget_mia['forget_vs_test']['test_loss']:.4f}")

print(f"\nForget vs Retain:")
print(f"  攻击准确率: {fedforget_mia['forget_vs_retain']['accuracy']:.2f}%")
print(f"  AUC: {fedforget_mia['forget_vs_retain']['auc']:.4f}")

# ============================================================
# 对比总结
# ============================================================
print("\n" + "="*80)
print("MIA评估总结")
print("="*80)

print(f"\n预训练基线: Test {pretrain_test['accuracy']:.2f}%, Forget {pretrain_forget['accuracy']:.2f}%")
print()

print(f"{'方法':<12} {'Test%':<8} {'Forget%':<9} {'遗忘率%':<9} {'ASR(F vs T)%':<14} {'AUC(F vs T)':<13} {'隐私保护':<10}")
print("-"*80)

for method, name in [('pretrain', '预训练'),
                     ('retrain', 'Retrain'),
                     ('finetune', 'Fine-tune'),
                     ('fedforget', 'FedForget')]:

    if method == 'pretrain':
        test_acc = pretrain_test['accuracy']
        forget_acc = pretrain_forget['accuracy']
        forgetting = 0.0
    elif method == 'retrain':
        test_acc = retrain_test['accuracy']
        forget_acc = retrain_forget['accuracy']
        forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100
    elif method == 'finetune':
        test_acc = finetune_test['accuracy']
        forget_acc = finetune_forget['accuracy']
        forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100
    else:
        test_acc = fedforget_test['accuracy']
        forget_acc = fedforget_forget['accuracy']
        forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

    asr = mia_results[method]['forget_vs_test']['accuracy']
    auc = mia_results[method]['forget_vs_test']['auc']

    # 隐私评分: ASR越接近50%, AUC越接近0.5越好
    privacy_score = 100 - abs(asr - 50) - abs(auc - 0.5) * 100

    privacy_level = "优秀" if privacy_score > 40 else ("良好" if privacy_score > 20 else "一般")

    print(f"{name:<12} {test_acc:<8.2f} {forget_acc:<9.2f} {forgetting:<9.1f} {asr:<14.2f} {auc:<13.4f} {privacy_level:<10}")

print("="*80)

print("\n注释:")
print("- ASR (Attack Success Rate): 攻击成功率，理想值=50% (随机猜测)")
print("- AUC: ROC曲线下面积，理想值=0.5 (无区分能力)")
print("- 隐私保护评级: 基于ASR和AUC与理想值的偏差")
print()

# 保存结果
import csv
import os

os.makedirs('/home/featurize/work/GJC/fedforget/results', exist_ok=True)

with open('/home/featurize/work/GJC/fedforget/results/mia_evaluation.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Method', 'Test_Acc', 'Forget_Acc', 'Forgetting_Rate',
                    'ASR_Forget_vs_Test', 'AUC_Forget_vs_Test',
                    'ASR_Forget_vs_Retain', 'AUC_Forget_vs_Retain'])

    for method, name in [('pretrain', 'Pretrain'),
                        ('retrain', 'Retrain'),
                        ('finetune', 'FineTuning'),
                        ('fedforget', 'FedForget')]:

        if method == 'pretrain':
            test_acc = pretrain_test['accuracy']
            forget_acc = pretrain_forget['accuracy']
            forgetting = 0.0
        elif method == 'retrain':
            test_acc = retrain_test['accuracy']
            forget_acc = retrain_forget['accuracy']
            forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100
        elif method == 'finetune':
            test_acc = finetune_test['accuracy']
            forget_acc = finetune_forget['accuracy']
            forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100
        else:
            test_acc = fedforget_test['accuracy']
            forget_acc = fedforget_forget['accuracy']
            forgetting = (pretrain_forget['accuracy'] - forget_acc) / pretrain_forget['accuracy'] * 100

        writer.writerow([
            name,
            test_acc,
            forget_acc,
            forgetting,
            mia_results[method]['forget_vs_test']['accuracy'],
            mia_results[method]['forget_vs_test']['auc'],
            mia_results[method]['forget_vs_retain']['accuracy'],
            mia_results[method]['forget_vs_retain']['auc']
        ])

print("✓ 结果已保存到: results/mia_evaluation.csv")
print("\n实验完成!")
