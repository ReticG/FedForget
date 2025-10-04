#!/usr/bin/env python3
"""
FedForget 快速验证测试
验证联邦学习基本流程和FedForget遗忘效果
"""

import sys
import os
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import argparse
from pathlib import Path

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.utils.metrics import evaluate_model


def run_fedavg(
    fed_data,
    num_rounds=50,
    num_clients=10,
    participation_rate=0.1,
    local_epochs=5,
    device='cuda',
    verbose=True
):
    """
    运行标准FedAvg流程

    Args:
        fed_data: 联邦数据集
        num_rounds: 训练轮数
        num_clients: 客户端总数
        participation_rate: 每轮参与率
        local_epochs: 本地训练轮数
        device: 设备
        verbose: 是否打印详细信息

    Returns:
        训练历史和最终服务器
    """
    print("\n" + "="*60)
    print("运行标准FedAvg流程")
    print("="*60)

    # 创建服务器和模型
    model = ConvNet(num_classes=fed_data.num_classes, num_channels=1)
    server = Server(model=model, device=device)

    # 创建所有客户端
    clients = []
    for i in range(num_clients):
        client_loader = fed_data.get_client_loader(i, batch_size=32, shuffle=True)
        client = Client(
            client_id=i,
            model=ConvNet(num_classes=fed_data.num_classes, num_channels=1),
            data_loader=client_loader,
            device=device,
            lr=0.01
        )
        clients.append(client)

    # 测试数据加载器
    test_loader = fed_data.get_test_loader(batch_size=128)

    # 训练历史
    history = {
        'test_acc': [],
        'test_loss': []
    }

    # 联邦训练主循环
    for round_idx in range(num_rounds):
        # 选择参与客户端
        num_selected = max(1, int(num_clients * participation_rate))
        selected_indices = np.random.choice(num_clients, num_selected, replace=False)

        # 分发全局模型
        global_params = server.get_model_parameters()

        client_models = []
        client_weights = []

        # 客户端本地训练
        for idx in selected_indices:
            client = clients[idx]
            client.set_model_parameters(global_params)

            # 本地训练
            client.local_train(epochs=local_epochs, verbose=False)

            # 收集模型和权重
            client_models.append(client.get_model_parameters())
            client_weights.append(client.num_samples)

        # 服务器聚合
        aggregated_params = server.aggregate(client_models, client_weights)
        server.set_model_parameters(aggregated_params)

        # 评估
        test_results = server.evaluate(test_loader)
        history['test_acc'].append(test_results['accuracy'])
        history['test_loss'].append(test_results['loss'])

        if verbose and (round_idx + 1) % 10 == 0:
            print(f"Round {round_idx+1}/{num_rounds} | "
                  f"Test Acc: {test_results['accuracy']:.2f}% | "
                  f"Test Loss: {test_results['loss']:.4f}")

    final_acc = history['test_acc'][-1]
    print(f"\n最终测试准确率: {final_acc:.2f}%")

    return history, server


def run_fedforget_unlearning(
    fed_data,
    pretrained_server,
    unlearn_client_id=0,
    unlearn_rounds=20,
    device='cuda',
    lambda_forget=3.0,
    verbose=True
):
    """
    运行FedForget遗忘流程

    Args:
        fed_data: 联邦数据集
        pretrained_server: 预训练的服务器
        unlearn_client_id: 要遗忘的客户端ID
        unlearn_rounds: 遗忘训练轮数
        device: 设备
        lambda_forget: 遗忘权重系数
        verbose: 是否打印详细信息

    Returns:
        遗忘后的服务器和遗忘历史
    """
    print("\n" + "="*60)
    print(f"运行FedForget遗忘流程 - 遗忘客户端 {unlearn_client_id}")
    print("="*60)

    # 创建FedForgetServer
    model = ConvNet(num_classes=fed_data.num_classes, num_channels=1)
    fedforget_server = FedForgetServer(model=model, device=device)
    fedforget_server.set_model_parameters(pretrained_server.get_model_parameters())
    fedforget_server.lambda_forget = lambda_forget

    # 创建遗忘客户端
    unlearn_client_loader = fed_data.get_client_loader(unlearn_client_id, batch_size=32)
    unlearn_client = UnlearningClient(
        client_id=unlearn_client_id,
        model=ConvNet(num_classes=fed_data.num_classes, num_channels=1),
        data_loader=unlearn_client_loader,
        device=device,
        lr=0.01
    )

    # 准备遗忘: 设置全局模型和本地模型
    global_params = fedforget_server.get_model_parameters()
    unlearn_client.prepare_unlearning(
        global_model_params=global_params,
        local_model_params=global_params  # 简化: 假设本地模型=全局模型
    )

    # 注册遗忘客户端
    fedforget_server.register_unlearning_client(unlearn_client_id, current_round=0)

    # 创建其他常规客户端
    num_clients = fed_data.num_clients
    regular_clients = []
    for i in range(num_clients):
        if i == unlearn_client_id:
            continue

        client_loader = fed_data.get_client_loader(i, batch_size=32)
        client = Client(
            client_id=i,
            model=ConvNet(num_classes=fed_data.num_classes, num_channels=1),
            data_loader=client_loader,
            device=device,
            lr=0.01
        )
        regular_clients.append(client)

    test_loader = fed_data.get_test_loader(batch_size=128)

    # 遗忘历史
    history = {
        'test_acc': [],
        'forget_acc': []  # 在遗忘数据上的准确率
    }

    # 遗忘训练主循环
    for round_idx in range(unlearn_rounds):
        global_params = fedforget_server.get_model_parameters()

        # 遗忘客户端训练 (使用温和的梯度上升)
        unlearn_client.set_model_parameters(global_params)
        unlearn_client.unlearning_train(
            epochs=3,  # 减少轮数
            method='gradient_ascent',
            lambda_negative=0.5,  # 降低负权重,防止过度遗忘
            use_gradient_ascent=True,
            verbose=False
        )

        # 选择部分常规客户端参与
        num_selected = min(2, len(regular_clients))
        selected_clients = np.random.choice(regular_clients, num_selected, replace=False)

        client_models = [unlearn_client.get_model_parameters()]
        client_ids = [unlearn_client_id]
        client_samples = [unlearn_client.num_samples]

        for client in selected_clients:
            client.set_model_parameters(global_params)
            client.local_train(epochs=5, verbose=False)

            client_models.append(client.get_model_parameters())
            client_ids.append(client.client_id)
            client_samples.append(client.num_samples)

        # FedForget聚合
        aggregated_params = fedforget_server.aggregate_with_fedforget(
            client_models,
            client_ids,
            client_samples,
            current_round=round_idx
        )
        fedforget_server.set_model_parameters(aggregated_params)

        # 评估
        test_results = fedforget_server.evaluate(test_loader)
        history['test_acc'].append(test_results['accuracy'])

        # 评估在遗忘数据上的性能
        forget_results = evaluate_model(
            fedforget_server.model,
            unlearn_client_loader,
            device=device
        )
        history['forget_acc'].append(forget_results['accuracy'])

        if verbose and (round_idx + 1) % 5 == 0:
            print(f"Round {round_idx+1}/{unlearn_rounds} | "
                  f"Test Acc: {test_results['accuracy']:.2f}% | "
                  f"Forget Acc: {forget_results['accuracy']:.2f}%")

    final_test_acc = history['test_acc'][-1]
    final_forget_acc = history['forget_acc'][-1]

    print(f"\n遗忘后:")
    print(f"  测试准确率: {final_test_acc:.2f}%")
    print(f"  遗忘数据准确率: {final_forget_acc:.2f}%")

    return history, fedforget_server


def main():
    parser = argparse.ArgumentParser(description='FedForget快速验证测试')
    parser.add_argument('--dataset', type=str, default='mnist',
                        help='数据集 (mnist, cifar10, fashion_mnist)')
    parser.add_argument('--num_clients', type=int, default=10,
                        help='客户端数量')
    parser.add_argument('--num_rounds', type=int, default=30,
                        help='训练轮数')
    parser.add_argument('--unlearn_rounds', type=int, default=10,
                        help='遗忘轮数')
    parser.add_argument('--unlearn_client_id', type=int, default=0,
                        help='要遗忘的客户端ID')
    parser.add_argument('--lambda_forget', type=float, default=3.0,
                        help='遗忘权重系数')
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备 (cuda or cpu)')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子')

    args = parser.parse_args()

    # 设置随机种子
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # 检查设备
    if args.device == 'cuda' and not torch.cuda.is_available():
        print("CUDA不可用, 使用CPU")
        args.device = 'cpu'

    print("\n" + "="*60)
    print("FedForget快速验证测试")
    print("="*60)
    print(f"数据集: {args.dataset.upper()}")
    print(f"客户端数量: {args.num_clients}")
    print(f"训练轮数: {args.num_rounds}")
    print(f"遗忘轮数: {args.unlearn_rounds}")
    print(f"遗忘客户端: {args.unlearn_client_id}")
    print(f"设备: {args.device.upper()}")
    print("="*60)

    # 加载数据
    print("\n加载联邦数据...")
    fed_data = load_federated_data(
        dataset_name=args.dataset,
        num_clients=args.num_clients,
        data_dist='iid',
        data_root='/home/featurize/data'
    )

    # 步骤1: 运行标准FedAvg
    print("\n步骤1: 预训练 (FedAvg)")
    history_fedavg, pretrained_server = run_fedavg(
        fed_data,
        num_rounds=args.num_rounds,
        num_clients=args.num_clients,
        participation_rate=0.3,
        local_epochs=5,
        device=args.device
    )

    # 步骤2: 运行FedForget遗忘
    print("\n步骤2: 遗忘训练 (FedForget)")
    history_forget, fedforget_server = run_fedforget_unlearning(
        fed_data,
        pretrained_server,
        unlearn_client_id=args.unlearn_client_id,
        unlearn_rounds=args.unlearn_rounds,
        device=args.device,
        lambda_forget=args.lambda_forget
    )

    # 总结结果
    print("\n" + "="*60)
    print("实验总结")
    print("="*60)
    print(f"预训练最终测试准确率: {history_fedavg['test_acc'][-1]:.2f}%")
    print(f"遗忘后测试准确率: {history_forget['test_acc'][-1]:.2f}%")
    print(f"遗忘数据准确率: {history_forget['forget_acc'][-1]:.2f}%")
    print(f"性能保持率: {history_forget['test_acc'][-1] / history_fedavg['test_acc'][-1] * 100:.2f}%")
    print("="*60)

    # 成功标准
    test_acc_retained = history_forget['test_acc'][-1] / history_fedavg['test_acc'][-1]
    forget_acc_dropped = history_forget['forget_acc'][-1] < 50.0

    print("\n✓ 测试完成!")

    if test_acc_retained > 0.95 and forget_acc_dropped:
        print("✅ 成功! FedForget有效: 性能保持>95%, 遗忘数据准确率<50%")
        return 0
    else:
        print("⚠️  警告: 结果未达到预期标准")
        if test_acc_retained <= 0.95:
            print(f"  - 性能保持率 {test_acc_retained*100:.2f}% < 95%")
        if not forget_acc_dropped:
            print(f"  - 遗忘数据准确率 {history_forget['forget_acc'][-1]:.2f}% >= 50%")
        return 1


if __name__ == '__main__':
    exit(main())
