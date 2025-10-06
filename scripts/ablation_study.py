"""
消融实验 (Ablation Study)

目的: 验证FedForget各组件的贡献

实验变体:
1. FedForget (完整) - 基线
2. No Weight Adjustment (λ_forget=1.0) - 移除动态权重调整
3. No Distillation (只用梯度上升) - 移除知识蒸馏
4. Single Teacher (只用Teacher A) - 移除双教师
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import pandas as pd
from tqdm import tqdm
import copy

from src.data.datasets import load_federated_data
from src.models.cnn import ConvNet
from src.federated.client import Client, UnlearningClient
from src.federated.server import Server, FedForgetServer
from src.unlearning.baselines import RetrainBaseline
from src.utils.metrics import evaluate_model, compute_forgetting_score
from src.utils.mia import SimpleMIA


def run_fedforget_variant(variant_name, fed_data, device='cuda',
                          use_weight_adjustment=True,
                          use_distillation=True,
                          use_dual_teacher=True):
    """
    运行FedForget的一个变体

    Args:
        variant_name: 变体名称
        fed_data: 联邦数据集
        use_weight_adjustment: 是否使用动态权重调整
        use_distillation: 是否使用知识蒸馏
        use_dual_teacher: 是否使用双教师（False则只用Teacher A）
    """
    print(f"\n{'='*60}")
    print(f"运行变体: {variant_name}")
    print(f"{'='*60}")

    # 创建模型
    model = ConvNet(num_classes=10, num_channels=3).to(device)

    # 预训练
    print("\n预训练...")
    clients = []
    for i in range(5):
        client_loader = fed_data.get_client_loader(i, batch_size=64)
        client = Client(
            client_id=i,
            model=copy.deepcopy(model),
            data_loader=client_loader,
            device=device,
            lr=0.01
        )
        clients.append(client)

    server = Server(model=model, device=device)

    for round_idx in tqdm(range(20), desc="预训练"):
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

    pretrain_model = copy.deepcopy(model)

    # 评估预训练
    test_loader = fed_data.get_test_loader(batch_size=256)
    forget_loader = fed_data.get_client_loader(0, batch_size=64)

    pretrain_result = evaluate_model(pretrain_model, test_loader, device)
    pretrain_test_acc = pretrain_result['accuracy']

    # 遗忘阶段
    print(f"\n{variant_name}遗忘...")

    # 准备遗忘客户端
    unlearn_client = UnlearningClient(
        client_id=0,
        model=copy.deepcopy(model),
        data_loader=forget_loader,
        device=device,
        lr=0.01
    )

    # 准备教师模型
    # 只在使用蒸馏时调用prepare_unlearning()
    if use_distillation:
        unlearn_client.prepare_unlearning(
            global_model_params=pretrain_model.state_dict(),
            local_model_params=unlearn_client.model.state_dict() if use_dual_teacher else None
        )
        unlearn_client.is_unlearning = True  # 标记为遗忘模式
    else:
        # No Distillation变体：不使用知识蒸馏
        unlearn_client.is_unlearning = True  # 仍需标记为遗忘模式

    # 创建服务器
    if use_weight_adjustment:
        fedforget_server = FedForgetServer(model=copy.deepcopy(model), device=device)
        fedforget_server.lambda_forget = 2.0  # 设置权重系数
        fedforget_server.register_unlearning_client(0, current_round=0)
    else:
        fedforget_server = Server(model=copy.deepcopy(model), device=device)

    # 遗忘训练
    for round_idx in tqdm(range(10), desc=f"{variant_name}遗忘"):
        global_params = fedforget_server.get_model_parameters()

        # 遗忘客户端训练
        unlearn_client.set_model_parameters(global_params)

        if use_distillation:
            # 使用蒸馏 (dual_teacher方法内部会根据local_model是否存在自动处理单/双教师)
            unlearn_client.unlearning_train(
                epochs=2,
                method='dual_teacher',
                distill_temp=2.0,
                alpha=0.93,
                lambda_pos=1.0,
                lambda_neg=3.5
            )
        else:
            # 只用梯度上升（负向学习）
            unlearn_client.unlearning_train(
                epochs=2,
                method='gradient_ascent',
                alpha=0.0,  # 只用负向学习
                lambda_neg=3.5
            )

        # 常规客户端训练
        client_models = [unlearn_client.get_model_parameters()]
        client_ids = [0]
        client_samples = [unlearn_client.num_samples]

        for i in range(1, 5):
            clients[i].set_model_parameters(global_params)
            clients[i].local_train(epochs=2, verbose=False)
            client_models.append(clients[i].get_model_parameters())
            client_ids.append(i)
            client_samples.append(clients[i].num_samples)

        # 聚合
        if use_weight_adjustment:
            aggregated = fedforget_server.aggregate_with_fedforget(
                client_models, client_ids, client_samples,
                current_round=round_idx
            )
        else:
            aggregated = fedforget_server.aggregate(client_models, client_samples)

        fedforget_server.set_model_parameters(aggregated)

    # 评估
    final_model = fedforget_server.model

    test_result = evaluate_model(final_model, test_loader, device)
    test_acc = test_result['accuracy']

    forget_result = evaluate_model(final_model, forget_loader, device)
    forget_acc = forget_result['accuracy']

    # 计算遗忘分数
    pretrain_forget_result = evaluate_model(pretrain_model, forget_loader, device)
    pretrain_forget_acc = pretrain_forget_result['accuracy']

    retention = (test_acc / pretrain_test_acc) * 100
    forgetting = ((pretrain_forget_acc - forget_acc) / pretrain_forget_acc) * 100

    # SimpleMIA评估
    test_loader_mia = fed_data.get_test_loader(batch_size=64)
    mia_result = SimpleMIA.evaluate_threshold_attack(
        final_model, forget_loader, test_loader_mia, device
    )

    return {
        'Variant': variant_name,
        'Test_Acc': test_acc,
        'Forget_Acc': forget_acc,
        'Retention': retention,
        'Forgetting': forgetting,
        'ASR': mia_result['accuracy'],
        'AUC': mia_result['auc']
    }


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")

    # 设置随机种子
    seed = 42
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    # 加载数据
    print("\n加载数据...")
    fed_data = load_federated_data(
        dataset_name='cifar10',
        num_clients=5,
        data_dist='noniid',
        dirichlet_alpha=0.5,
        data_root='/home/featurize/data'
    )

    results = []

    # 1. FedForget (完整版) - 基线
    result = run_fedforget_variant(
        "FedForget (Full)",
        fed_data,
        device,
        use_weight_adjustment=True,
        use_distillation=True,
        use_dual_teacher=True
    )
    results.append(result)

    # 2. No Weight Adjustment
    result = run_fedforget_variant(
        "No Weight Adjustment",
        fed_data,
        device,
        use_weight_adjustment=False,
        use_distillation=True,
        use_dual_teacher=True
    )
    results.append(result)

    # 3. No Distillation (只用梯度上升)
    result = run_fedforget_variant(
        "No Distillation",
        fed_data,
        device,
        use_weight_adjustment=True,
        use_distillation=False,
        use_dual_teacher=False
    )
    results.append(result)

    # 4. Single Teacher (只用Teacher A)
    result = run_fedforget_variant(
        "Single Teacher",
        fed_data,
        device,
        use_weight_adjustment=True,
        use_distillation=True,
        use_dual_teacher=False
    )
    results.append(result)

    # 保存结果
    df = pd.DataFrame(results)
    df.to_csv('results/ablation_study.csv', index=False)

    print(f"\n{'='*60}")
    print("消融实验结果")
    print(f"{'='*60}")
    print(df.to_string(index=False))
    print(f"\n✅ 结果已保存到: results/ablation_study.csv")

    # 分析组件贡献
    print(f"\n{'='*60}")
    print("组件贡献分析")
    print(f"{'='*60}")

    full_result = results[0]

    for i in range(1, len(results)):
        variant = results[i]
        print(f"\n{variant['Variant']}:")
        print(f"  遗忘率变化: {variant['Forgetting']:.1f}% vs {full_result['Forgetting']:.1f}% "
              f"(Δ={variant['Forgetting']-full_result['Forgetting']:.1f}%)")
        print(f"  保持率变化: {variant['Retention']:.1f}% vs {full_result['Retention']:.1f}% "
              f"(Δ={variant['Retention']-full_result['Retention']:.1f}%)")
        print(f"  ASR变化: {variant['ASR']:.1f}% vs {full_result['ASR']:.1f}% "
              f"(Δ={variant['ASR']-full_result['ASR']:.1f}%)")


if __name__ == '__main__':
    main()
