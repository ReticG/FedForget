"""
可复现性验证实验

目的: 验证FedForget结果的稳定性

实验设计:
- 运行3次完整实验（不同随机种子: 42, 123, 456）
- 报告均值 ± 标准差
- 配置: CIFAR-10, α=0.5, 最佳参数
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import pandas as pd
from tqdm import tqdm
import copy
import time

from src.data.datasets import load_federated_data
from src.models.cnn import ConvNet
from src.federated.client import Client, UnlearningClient
from src.federated.server import Server, FedForgetServer
from src.unlearning.baselines import RetrainBaseline, FineTuningBaseline
from src.utils.metrics import evaluate_model
from src.utils.mia import SimpleMIA


def set_seed(seed):
    """设置所有随机种子"""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def run_single_experiment(seed, device='cuda'):
    """运行单次完整实验"""
    print(f"\n{'='*60}")
    print(f"运行实验 - 种子: {seed}")
    print(f"{'='*60}")

    # 设置随机种子
    set_seed(seed)

    # 加载数据
    fed_data = load_federated_data(
        dataset_name='cifar10',
        num_clients=5,
        data_dist='noniid',
        dirichlet_alpha=0.5,
        data_root='/home/featurize/data'
    )

    results = {}

    # ========== 预训练 ==========
    print("\n预训练...")
    model = ConvNet(num_classes=10, num_channels=3).to(device)

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
    results['Pretrain_Test_Acc'] = pretrain_result['accuracy']

    pretrain_forget_result = evaluate_model(pretrain_model, forget_loader, device)
    pretrain_forget_acc = pretrain_forget_result['accuracy']

    # ========== Retrain ==========
    print("\nRetrain...")
    start_time = time.time()

    retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in range(1, 5)]
    retrain_baseline = RetrainBaseline(
        model=ConvNet(num_classes=10, num_channels=3),
        device=device,
        lr=0.01
    )
    retrain_baseline.retrain(
        retain_loaders=retain_loaders,
        rounds=20,
        local_epochs=2
    )

    retrain_time = time.time() - start_time
    retrain_model = retrain_baseline.model

    retrain_test_result = evaluate_model(retrain_model, test_loader, device)
    retrain_forget_result = evaluate_model(retrain_model, forget_loader, device)

    results['Retrain_Test_Acc'] = retrain_test_result['accuracy']
    results['Retrain_Forget_Acc'] = retrain_forget_result['accuracy']
    results['Retrain_Retention'] = (retrain_test_result['accuracy'] / results['Pretrain_Test_Acc']) * 100
    results['Retrain_Forgetting'] = ((pretrain_forget_acc - retrain_forget_result['accuracy']) / pretrain_forget_acc) * 100
    results['Retrain_Time'] = retrain_time

    # SimpleMIA
    test_loader_mia = fed_data.get_test_loader(batch_size=64)
    retrain_mia = SimpleMIA.evaluate_threshold_attack(retrain_model, forget_loader, test_loader_mia, device)
    results['Retrain_ASR'] = retrain_mia['accuracy']
    results['Retrain_AUC'] = retrain_mia['auc']

    # ========== Fine-tuning ==========
    print("\nFine-tuning...")
    start_time = time.time()

    finetune_baseline = FineTuningBaseline(
        model=copy.deepcopy(pretrain_model),
        device=device,
        lr=0.01
    )
    finetune_baseline.fine_tune(
        retain_loaders=retain_loaders,
        rounds=10,
        local_epochs=2
    )

    finetune_time = time.time() - start_time
    finetune_model = finetune_baseline.model

    finetune_test_result = evaluate_model(finetune_model, test_loader, device)
    finetune_forget_result = evaluate_model(finetune_model, forget_loader, device)

    results['FineTune_Test_Acc'] = finetune_test_result['accuracy']
    results['FineTune_Forget_Acc'] = finetune_forget_result['accuracy']
    results['FineTune_Retention'] = (finetune_test_result['accuracy'] / results['Pretrain_Test_Acc']) * 100
    results['FineTune_Forgetting'] = ((pretrain_forget_acc - finetune_forget_result['accuracy']) / pretrain_forget_acc) * 100
    results['FineTune_Time'] = finetune_time

    finetune_mia = SimpleMIA.evaluate_threshold_attack(finetune_model, forget_loader, test_loader_mia, device)
    results['FineTune_ASR'] = finetune_mia['accuracy']
    results['FineTune_AUC'] = finetune_mia['auc']

    # ========== FedForget ==========
    print("\nFedForget...")
    start_time = time.time()

    # 准备遗忘客户端
    unlearn_client = UnlearningClient(
        client_id=0,
        model=copy.deepcopy(pretrain_model),
        data_loader=forget_loader,
        device=device,
        lr=0.01
    )

    unlearn_client.prepare_unlearning(
        global_model_params=pretrain_model.state_dict(),
        local_model_params=None
    )

    fedforget_server = FedForgetServer(model=copy.deepcopy(pretrain_model), device=device)
    fedforget_server.lambda_forget = 2.0  # 设置权重系数
    fedforget_server.register_unlearning_client(0, current_round=0)

    # 遗忘训练
    for round_idx in tqdm(range(10), desc="FedForget遗忘"):
        global_params = fedforget_server.get_model_parameters()

        # 遗忘客户端
        unlearn_client.set_model_parameters(global_params)
        unlearn_client.unlearning_train(
            epochs=2,
            method='dual_teacher',
            distill_temp=2.0,
            alpha=0.93,
            lambda_pos=1.0,
            lambda_neg=3.5
        )

        # 常规客户端
        client_models = [unlearn_client.get_model_parameters()]
        client_ids = [0]
        client_samples = [unlearn_client.num_samples]

        for i in range(1, 5):
            clients[i].set_model_parameters(global_params)
            clients[i].local_train(epochs=2, verbose=False)
            client_models.append(clients[i].get_model_parameters())
            client_ids.append(i)
            client_samples.append(clients[i].num_samples)

        # FedForget聚合
        aggregated = fedforget_server.aggregate_with_fedforget(
            client_models, client_ids, client_samples,
            current_round=round_idx
        )
        fedforget_server.set_model_parameters(aggregated)

    fedforget_time = time.time() - start_time
    fedforget_model = fedforget_server.model

    fedforget_test_result = evaluate_model(fedforget_model, test_loader, device)
    fedforget_forget_result = evaluate_model(fedforget_model, forget_loader, device)

    results['FedForget_Test_Acc'] = fedforget_test_result['accuracy']
    results['FedForget_Forget_Acc'] = fedforget_forget_result['accuracy']
    results['FedForget_Retention'] = (fedforget_test_result['accuracy'] / results['Pretrain_Test_Acc']) * 100
    results['FedForget_Forgetting'] = ((pretrain_forget_acc - fedforget_forget_result['accuracy']) / pretrain_forget_acc) * 100
    results['FedForget_Time'] = fedforget_time

    fedforget_mia = SimpleMIA.evaluate_threshold_attack(fedforget_model, forget_loader, test_loader_mia, device)
    results['FedForget_ASR'] = fedforget_mia['accuracy']
    results['FedForget_AUC'] = fedforget_mia['auc']

    results['Seed'] = seed

    return results


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")

    # 运行3次实验（不同随机种子）
    seeds = [42, 123, 456]
    all_results = []

    for seed in seeds:
        result = run_single_experiment(seed, device)
        all_results.append(result)

    # 保存原始结果
    df = pd.DataFrame(all_results)
    df.to_csv('results/reproducibility_raw.csv', index=False)

    print(f"\n{'='*60}")
    print("原始实验结果")
    print(f"{'='*60}")
    print(df.to_string(index=False))

    # 计算统计量
    print(f"\n{'='*60}")
    print("统计结果 (均值 ± 标准差)")
    print(f"{'='*60}")

    metrics = [
        'Test_Acc', 'Forget_Acc', 'Retention', 'Forgetting', 'ASR', 'AUC', 'Time'
    ]
    methods = ['Retrain', 'FineTune', 'FedForget']

    stats = []
    for method in methods:
        row = {'Method': method}
        for metric in metrics:
            col_name = f"{method}_{metric}"
            if col_name in df.columns:
                mean = df[col_name].mean()
                std = df[col_name].std()
                row[metric] = f"{mean:.2f} ± {std:.2f}"
        stats.append(row)

    stats_df = pd.DataFrame(stats)
    stats_df.to_csv('results/reproducibility_stats.csv', index=False)

    print(stats_df.to_string(index=False))
    print(f"\n✅ 结果已保存:")
    print(f"  - results/reproducibility_raw.csv (原始数据)")
    print(f"  - results/reproducibility_stats.csv (统计结果)")

    # 分析稳定性
    print(f"\n{'='*60}")
    print("稳定性分析")
    print(f"{'='*60}")

    for method in methods:
        print(f"\n{method}:")
        for metric in ['Forgetting', 'Retention', 'ASR']:
            col_name = f"{method}_{metric}"
            if col_name in df.columns:
                std = df[col_name].std()
                mean = df[col_name].mean()
                cv = (std / mean) * 100 if mean != 0 else 0
                print(f"  {metric}: CV={cv:.2f}% (变异系数)")


if __name__ == '__main__':
    main()
