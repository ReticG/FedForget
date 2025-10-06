"""
Non-IID鲁棒性实验

测试FedForget在不同Non-IID程度下的表现
Dirichlet alpha: 0.1 (极端Non-IID), 0.3, 0.5, 0.7, 1.0 (接近IID)

目标: 证明FedForget在各种数据分布下都稳定有效
"""

import sys
sys.path.append('/home/featurize/work/GJC/fedforget')

import torch
import numpy as np
import pandas as pd
from tqdm import tqdm
import copy
import time

from src.data import load_federated_data
from src.models import ConvNet
from src.federated import Client, Server
from src.federated.server import FedForgetServer
from src.federated.client import UnlearningClient
from src.unlearning.baselines import RetrainBaseline, FineTuningBaseline
from src.utils.metrics import evaluate_model
from src.utils.mia import SimpleMIA

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def run_experiment(alpha_value, dataset_name='cifar10', num_clients=5):
    """
    运行单个Non-IID设置的完整实验
    """
    print(f"\n{'='*80}")
    print(f"Non-IID实验: Dirichlet α={alpha_value}")
    print(f"{'='*80}")

    # 设置随机种子
    torch.manual_seed(42)
    np.random.seed(42)

    # 加载数据
    print(f"加载数据 (Dirichlet α={alpha_value})...")
    fed_data = load_federated_data(
        dataset_name=dataset_name,
        num_clients=num_clients,
        data_dist='noniid',
        dirichlet_alpha=alpha_value,
        data_root='/home/featurize/data'
    )

    test_loader = fed_data.get_test_loader(batch_size=256)
    forget_loader = fed_data.get_client_loader(0, batch_size=64)

    # 预训练
    print("预训练...")
    model = ConvNet(num_classes=10, num_channels=3).to(device)
    clients = []
    for i in range(num_clients):
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

    for _ in tqdm(range(20), desc="Pretrain"):
        # 获取全局参数
        global_params = server.get_model_parameters()
        client_models = []
        client_weights = []

        # 各客户端本地训练
        for client in clients:
            client.set_model_parameters(global_params)
            client.local_train(epochs=2, verbose=False)
            client_models.append(client.get_model_parameters())
            client_weights.append(client.num_samples)

        # 聚合
        aggregated = server.aggregate(client_models, client_weights)
        server.set_model_parameters(aggregated)

    pretrain_model = copy.deepcopy(model)
    pretrain_result_test = evaluate_model(pretrain_model, test_loader, device)
    pretrain_test_acc = pretrain_result_test['accuracy']
    pretrain_result_forget = evaluate_model(pretrain_model, forget_loader, device)
    pretrain_forget_acc = pretrain_result_forget['accuracy']

    print(f"预训练完成: Test={pretrain_test_acc:.2f}%, Forget={pretrain_forget_acc:.2f}%")

    # 结果存储
    results = []

    # 1. Retrain
    print("\n[1/3] Retrain...")
    start_time = time.time()
    try:
        # 创建retain_loaders (排除客户端0)
        retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in range(1, num_clients)]

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
        retrain_model = retrain_baseline.model
        retrain_time = time.time() - start_time

        retrain_result_test = evaluate_model(retrain_model, test_loader, device)
        retrain_test_acc = retrain_result_test['accuracy']
        retrain_result_forget = evaluate_model(retrain_model, forget_loader, device)
        retrain_forget_acc = retrain_result_forget['accuracy']

        # MIA评估
        mia_results = SimpleMIA.evaluate_threshold_attack(
            retrain_model, forget_loader, test_loader, device
        )

        retention = (retrain_test_acc / pretrain_test_acc) * 100
        forgetting = ((pretrain_forget_acc - retrain_forget_acc) / pretrain_forget_acc) * 100

        results.append({
            'Alpha': alpha_value,
            'Method': 'Retrain',
            'Test_Acc': retrain_test_acc,
            'Forget_Acc': retrain_forget_acc,
            'Retention': retention,
            'Forgetting': forgetting,
            'ASR': mia_results['accuracy'],
            'AUC': mia_results['auc'],
            'Time': retrain_time,
            'Status': 'Success'
        })
        print(f"  Test={retrain_test_acc:.2f}%, Forget={retrain_forget_acc:.2f}%, Forgetting={forgetting:.1f}%")

    except Exception as e:
        print(f"  Retrain失败: {e}")
        results.append({
            'Alpha': alpha_value,
            'Method': 'Retrain',
            'Test_Acc': 0,
            'Forget_Acc': 0,
            'Retention': 0,
            'Forgetting': 0,
            'ASR': 50,
            'AUC': 0.5,
            'Time': 0,
            'Status': f'Failed: {str(e)[:50]}'
        })

    # 2. Fine-tuning
    print("\n[2/3] Fine-tuning...")
    start_time = time.time()

    # 创建retain_loaders (排除客户端0)
    retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in range(1, num_clients)]

    finetune_baseline = FineTuningBaseline(
        model=ConvNet(num_classes=10, num_channels=3),
        pretrained_params=copy.deepcopy(pretrain_model.state_dict()),
        device=device,
        lr=0.001  # Fine-tuning uses smaller learning rate
    )
    finetune_baseline.finetune(
        retain_loaders=retain_loaders,
        rounds=10,
        local_epochs=2
    )
    finetune_model = finetune_baseline.model
    finetune_time = time.time() - start_time

    finetune_result_test = evaluate_model(finetune_model, test_loader, device)
    finetune_test_acc = finetune_result_test['accuracy']
    finetune_result_forget = evaluate_model(finetune_model, forget_loader, device)
    finetune_forget_acc = finetune_result_forget['accuracy']

    mia_results = SimpleMIA.evaluate_threshold_attack(
        finetune_model, forget_loader, test_loader, device
    )

    retention = (finetune_test_acc / pretrain_test_acc) * 100
    forgetting = ((pretrain_forget_acc - finetune_forget_acc) / pretrain_forget_acc) * 100

    results.append({
        'Alpha': alpha_value,
        'Method': 'Fine-tuning',
        'Test_Acc': finetune_test_acc,
        'Forget_Acc': finetune_forget_acc,
        'Retention': retention,
        'Forgetting': forgetting,
        'ASR': mia_results['accuracy'],
        'AUC': mia_results['auc'],
        'Time': finetune_time,
        'Status': 'Success'
    })
    print(f"  Test={finetune_test_acc:.2f}%, Forget={finetune_forget_acc:.2f}%, Forgetting={forgetting:.1f}%")

    # 3. FedForget (最佳配置)
    print("\n[3/3] FedForget (alpha=0.93, lambda_neg=3.5)...")
    start_time = time.time()

    # 创建客户端
    clients = []
    for i in range(num_clients):
        client_loader = fed_data.get_client_loader(i, batch_size=64)
        if i == 0:
            client = UnlearningClient(
                client_id=0,
                model=copy.deepcopy(pretrain_model),
                data_loader=client_loader,
                device=device,
                lr=0.01
            )
        else:
            client = Client(
                client_id=i,
                model=copy.deepcopy(pretrain_model),
                data_loader=client_loader,
                device=device,
                lr=0.01
            )
        clients.append(client)

    # 准备遗忘
    clients[0].prepare_unlearning(
        global_model_params=copy.deepcopy(pretrain_model.state_dict()),
        local_model_params=None
    )

    # FedForget服务器
    fedforget_server = FedForgetServer(
        model=copy.deepcopy(pretrain_model),
        device=device
    )
    fedforget_server.register_unlearning_client(0, current_round=0)

    # 遗忘训练
    for round_idx in tqdm(range(10), desc="FedForget"):
        global_params = fedforget_server.get_model_parameters()

        # 遗忘客户端训练
        clients[0].set_model_parameters(global_params)
        clients[0].unlearning_train(
            epochs=2,
            method='dual_teacher',
            distill_temp=2.0,
            alpha=0.93,
            lambda_pos=1.0,
            lambda_neg=3.5,
            verbose=False
        )

        # 常规客户端训练
        client_models = [clients[0].get_model_parameters()]
        client_ids = [0]
        client_samples = [clients[0].num_samples]

        for i in range(1, 5):
            clients[i].set_model_parameters(global_params)
            clients[i].local_train(epochs=2, verbose=False)
            client_models.append(clients[i].get_model_parameters())
            client_ids.append(i)
            client_samples.append(clients[i].num_samples)

        # FedForget聚合
        aggregated = fedforget_server.aggregate_with_fedforget(
            client_models,
            client_ids,
            client_samples,
            current_round=round_idx
        )
        fedforget_server.set_model_parameters(aggregated)

    fedforget_time = time.time() - start_time

    fedforget_model = fedforget_server.model
    fedforget_result_test = evaluate_model(fedforget_model, test_loader, device)
    fedforget_test_acc = fedforget_result_test['accuracy']
    fedforget_result_forget = evaluate_model(fedforget_model, forget_loader, device)
    fedforget_forget_acc = fedforget_result_forget['accuracy']

    mia_results = SimpleMIA.evaluate_threshold_attack(
        fedforget_model, forget_loader, test_loader, device
    )

    retention = (fedforget_test_acc / pretrain_test_acc) * 100
    forgetting = ((pretrain_forget_acc - fedforget_forget_acc) / pretrain_forget_acc) * 100

    results.append({
        'Alpha': alpha_value,
        'Method': 'FedForget',
        'Test_Acc': fedforget_test_acc,
        'Forget_Acc': fedforget_forget_acc,
        'Retention': retention,
        'Forgetting': forgetting,
        'ASR': mia_results['accuracy'],
        'AUC': mia_results['auc'],
        'Time': fedforget_time,
        'Status': 'Success'
    })
    print(f"  Test={fedforget_test_acc:.2f}%, Forget={fedforget_forget_acc:.2f}%, Forgetting={forgetting:.1f}%")

    return results


def main():
    print("="*80)
    print("Non-IID鲁棒性实验")
    print("测试FedForget在不同Non-IID程度下的表现")
    print("="*80)

    # 测试不同的alpha值
    alpha_values = [0.1, 0.3, 0.5, 0.7, 1.0]
    all_results = []

    for alpha in alpha_values:
        results = run_experiment(alpha)
        all_results.extend(results)

    # 保存结果
    df = pd.DataFrame(all_results)
    results_path = '/home/featurize/work/GJC/fedforget/results/noniid_robustness.csv'
    df.to_csv(results_path, index=False)

    print(f"\n{'='*80}")
    print("Non-IID鲁棒性实验完成")
    print(f"{'='*80}")
    print(f"\n结果已保存到: {results_path}")

    # 显示汇总
    print(f"\n{'='*80}")
    print("实验汇总")
    print(f"{'='*80}\n")
    print(df.to_string(index=False))

    # 分析
    print(f"\n{'='*80}")
    print("关键发现")
    print(f"{'='*80}\n")

    # 按Alpha分组分析
    for alpha in alpha_values:
        df_alpha = df[df['Alpha'] == alpha]
        print(f"\nDirichlet α={alpha}:")
        print("-" * 60)

        for _, row in df_alpha.iterrows():
            status_mark = "✓" if row['Status'] == 'Success' else "✗"
            print(f"  {status_mark} {row['Method']:12s}: "
                  f"Test={row['Test_Acc']:5.1f}%, "
                  f"Forget={row['Forget_Acc']:5.1f}%, "
                  f"Forgetting={row['Forgetting']:5.1f}%, "
                  f"ASR={row['ASR']:5.1f}%")

        # FedForget vs Retrain
        fedforget_row = df_alpha[df_alpha['Method'] == 'FedForget'].iloc[0]
        retrain_row = df_alpha[df_alpha['Method'] == 'Retrain'].iloc[0]

        if retrain_row['Status'] == 'Success':
            forgetting_ratio = (fedforget_row['Forgetting'] / retrain_row['Forgetting']) * 100
            print(f"\n  FedForget遗忘效果: {forgetting_ratio:.1f}% of Retrain")
            print(f"  FedForget隐私保护: ASR={fedforget_row['ASR']:.1f}% (理想值50%)")

    print(f"\n{'='*80}")
    print("实验完成!")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
