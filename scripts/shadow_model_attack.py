"""
Shadow Model Attack MIA评估

完整流程:
1. 训练5个影子模型 (模拟目标模型训练过程)
2. 从影子模型提取成员/非成员特征
3. 训练MIA攻击分类器
4. 评估所有遗忘方法的隐私保护效果
5. 对比SimpleMIA vs ShadowMIA
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
import numpy as np
import pandas as pd
from tqdm import tqdm
import copy

from src.data.datasets import load_federated_data
from src.models.cnn import ConvNet
from src.federated.server import Server, FedForgetServer
from src.federated.client import Client, UnlearningClient
from src.unlearning.baselines import RetrainBaseline, FineTuningBaseline
from src.utils.metrics import evaluate_model
from src.utils.mia import ShadowModelAttack, SimpleMIA


def train_shadow_model(shadow_id, dataset_name='cifar10', num_clients=5,
                       data_dist='noniid', dirichlet_alpha=0.5, device='cuda'):
    """
    训练单个影子模型

    使用与目标模型相同的训练过程，但使用不同的数据子集
    """
    print(f"\n{'='*60}")
    print(f"训练影子模型 #{shadow_id}")
    print(f"{'='*60}")

    # 设置随机种子 (每个影子模型使用不同种子)
    import random
    seed = 42 + shadow_id * 100
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    # 加载数据
    fed_data = load_federated_data(
        dataset_name=dataset_name,
        num_clients=num_clients,
        data_dist=data_dist,
        dirichlet_alpha=dirichlet_alpha,
        data_root='/home/featurize/data'
    )

    # 创建模型
    if dataset_name == 'cifar10':
        model = ConvNet(num_classes=10, num_channels=3).to(device)
    else:
        raise ValueError(f"Unsupported dataset: {dataset_name}")

    # 创建客户端和服务器
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

    server = Server(
        model=model,
        device=device
    )

    # 联邦训练
    print(f"影子模型 #{shadow_id}: 开始预训练...")
    for round_idx in tqdm(range(20), desc=f"Shadow #{shadow_id} Training"):
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

    # 评估
    test_loader = fed_data.get_test_loader(batch_size=256)
    test_result = evaluate_model(model, test_loader, device)
    test_acc = test_result['accuracy']
    print(f"影子模型 #{shadow_id} 测试准确率: {test_acc:.2f}%")

    return {
        'model': model,
        'fed_data': fed_data,
        'test_acc': test_acc
    }


def collect_shadow_features(shadow_models, attack_mia, device='cuda'):
    """
    从影子模型收集成员/非成员特征

    对每个影子模型:
    - 成员数据: 训练数据
    - 非成员数据: 测试数据
    """
    print(f"\n{'='*60}")
    print("从影子模型提取特征...")
    print(f"{'='*60}")

    all_member_features = []
    all_non_member_features = []

    for i, shadow_info in enumerate(shadow_models):
        model = shadow_info['model']
        fed_data = shadow_info['fed_data']

        print(f"\n提取影子模型 #{i} 的特征...")

        # 成员数据: 客户端0的训练数据
        member_loader = fed_data.get_client_loader(0, batch_size=64)
        member_features = attack_mia.extract_features(model, member_loader, device)

        # 非成员数据: 测试数据的一部分
        test_dataset = fed_data.test_data
        # 使用1000个测试样本作为非成员
        test_indices = np.random.choice(len(test_dataset), 1000, replace=False)
        non_member_loader = DataLoader(
            Subset(test_dataset, test_indices),
            batch_size=64,
            shuffle=False
        )
        non_member_features = attack_mia.extract_features(model, non_member_loader, device)

        all_member_features.append(member_features)
        all_non_member_features.append(non_member_features)

        print(f"  成员特征: {member_features.shape}")
        print(f"  非成员特征: {non_member_features.shape}")

    # 合并所有影子模型的特征
    member_features = np.vstack(all_member_features)
    non_member_features = np.vstack(all_non_member_features)

    print(f"\n总计:")
    print(f"  成员特征: {member_features.shape}")
    print(f"  非成员特征: {non_member_features.shape}")

    return member_features, non_member_features


def evaluate_target_model(target_model, fed_data, attack_mia, device='cuda'):
    """
    使用训练好的攻击模型评估目标模型

    重要: 这里评估的是遗忘场景下的隐私风险
    - forget数据: 理想情况应该被识别为"非成员"
    - test数据: 本来就是非成员
    - ASR = 攻击模型将forget数据识别为成员的比例 (越低越好)
    """
    # 提取forget数据特征 (客户端0的数据,应该被遗忘)
    forget_loader = fed_data.get_client_loader(0, batch_size=64)
    forget_features = attack_mia.extract_features(target_model, forget_loader, device)

    # 提取测试数据特征 (真正的非成员)
    test_dataset = fed_data.test_data
    test_indices = np.random.choice(len(test_dataset), 1000, replace=False)
    test_loader = DataLoader(
        Subset(test_dataset, test_indices),
        batch_size=64,
        shuffle=False
    )
    test_features = attack_mia.extract_features(target_model, test_loader, device)

    # 使用攻击模型预测
    if attack_mia.attack_model is None:
        raise ValueError("攻击模型未训练")

    # 预测forget数据
    forget_probs = attack_mia.attack_model.predict_proba(forget_features)[:, 1]  # P(member=1)
    forget_preds = attack_mia.attack_model.predict(forget_features)

    # 预测test数据
    test_probs = attack_mia.attack_model.predict_proba(test_features)[:, 1]
    test_preds = attack_mia.attack_model.predict(test_features)

    # Debug: 打印预测分布
    print(f"\n  Debug - Forget预测分布:")
    print(f"    预测为成员(1): {np.sum(forget_preds == 1)} / {len(forget_preds)} = {np.mean(forget_preds == 1)*100:.1f}%")
    print(f"    预测为非成员(0): {np.sum(forget_preds == 0)} / {len(forget_preds)} = {np.mean(forget_preds == 0)*100:.1f}%")
    print(f"    平均概率: {np.mean(forget_probs):.3f} (std={np.std(forget_probs):.3f})")

    print(f"\n  Debug - Test预测分布:")
    print(f"    预测为成员(1): {np.sum(test_preds == 1)} / {len(test_preds)} = {np.mean(test_preds == 1)*100:.1f}%")
    print(f"    预测为非成员(0): {np.sum(test_preds == 0)} / {len(test_preds)} = {np.mean(test_preds == 0)*100:.1f}%")
    print(f"    平均概率: {np.mean(test_probs):.3f} (std={np.std(test_probs):.3f})")

    # 计算ASR: forget被识别为成员的比例 (越低说明遗忘效果越好)
    asr = np.mean(forget_preds == 1) * 100

    # 计算AUC: 使用forget和test的概率分布
    from sklearn.metrics import roc_auc_score
    y_true = np.hstack([
        np.ones(len(forget_features)),  # forget应该被遗忘(标签1表示攻击应该失败)
        np.zeros(len(test_features))    # test本来就是非成员(标签0)
    ])
    y_scores = np.hstack([forget_probs, test_probs])

    # AUC计算: 能否区分forget和test
    # AUC接近0.5说明无法区分,隐私保护好
    try:
        auc = roc_auc_score(y_true, y_scores)
    except:
        auc = 0.5

    return {
        'accuracy': asr,  # ASR: 攻击成功率
        'auc': auc,
        'forget_member_rate': asr,  # forget被识别为成员的比例
        'test_member_rate': np.mean(test_preds == 1) * 100  # test被误判为成员的比例
    }


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")

    # ========== 步骤1: 训练影子模型 ==========
    num_shadow_models = 5
    shadow_models = []

    for shadow_id in range(num_shadow_models):
        shadow_info = train_shadow_model(
            shadow_id=shadow_id,
            dataset_name='cifar10',
            num_clients=5,
            data_dist='noniid',
            dirichlet_alpha=0.5,
            device=device
        )
        shadow_models.append(shadow_info)

    # ========== 步骤2: 提取影子模型特征并训练攻击模型 ==========
    attack_mia = ShadowModelAttack(device=device)

    member_features, non_member_features = collect_shadow_features(
        shadow_models, attack_mia, device
    )

    print(f"\n{'='*60}")
    print("训练MIA攻击模型...")
    print(f"{'='*60}")
    train_acc = attack_mia.train_attack_model(member_features, non_member_features)
    print(f"攻击模型训练准确率: {train_acc*100:.2f}%")

    # ========== 步骤3: 准备目标模型实验 ==========
    print(f"\n{'='*60}")
    print("准备目标模型实验...")
    print(f"{'='*60}")

    # 重置随机种子为标准值
    import random
    seed = 42
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    # 加载数据 (使用标准种子)
    fed_data = load_federated_data(
        dataset_name='cifar10',
        num_clients=5,
        data_dist='noniid',
        dirichlet_alpha=0.5,
        data_root='/home/featurize/data'
    )

    # 创建目标模型
    model = ConvNet(num_classes=10, num_channels=3).to(device)

    # 预训练
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

    print("\n预训练目标模型...")
    for round_idx in tqdm(range(20), desc="Pretrain"):
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
    test_loader = fed_data.get_test_loader(batch_size=256)
    pretrain_result = evaluate_model(pretrain_model, test_loader, device)
    pretrain_test_acc = pretrain_result['accuracy']
    print(f"预训练测试准确率: {pretrain_test_acc:.2f}%")

    # ========== 步骤4: 评估所有遗忘方法 ==========
    results = []

    # 4.1 预训练基线
    print(f"\n{'='*60}")
    print("评估: 预训练模型 (No Unlearning)")
    print(f"{'='*60}")

    pretrain_shadow_results = evaluate_target_model(
        pretrain_model, fed_data, attack_mia, device
    )
    forget_loader = fed_data.get_client_loader(0, batch_size=64)
    test_loader_mia = fed_data.get_test_loader(batch_size=64)
    pretrain_simple_results = SimpleMIA.evaluate_threshold_attack(
        pretrain_model, forget_loader, test_loader_mia, device
    )

    results.append({
        'Method': 'Pretrain',
        'Shadow_ASR': pretrain_shadow_results['accuracy'],
        'Shadow_AUC': pretrain_shadow_results['auc'],
        'Simple_ASR': pretrain_simple_results['accuracy'],
        'Simple_AUC': pretrain_simple_results['auc'],
        'Test_Acc': pretrain_test_acc
    })

    # 4.2 Retrain
    print(f"\n{'='*60}")
    print("评估: Retrain")
    print(f"{'='*60}")

    # 创建retain_loaders (排除客户端0)
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
    retrain_model = retrain_baseline.model

    retrain_result = evaluate_model(retrain_model, test_loader, device)
    retrain_test_acc = retrain_result['accuracy']
    retrain_shadow_results = evaluate_target_model(retrain_model, fed_data, attack_mia, device)
    retrain_simple_results = SimpleMIA.evaluate_threshold_attack(
        retrain_model, forget_loader, test_loader_mia, device
    )

    results.append({
        'Method': 'Retrain',
        'Shadow_ASR': retrain_shadow_results['accuracy'],
        'Shadow_AUC': retrain_shadow_results['auc'],
        'Simple_ASR': retrain_simple_results['accuracy'],
        'Simple_AUC': retrain_simple_results['auc'],
        'Test_Acc': retrain_test_acc
    })

    # 4.3 Fine-tuning
    print(f"\n{'='*60}")
    print("评估: Fine-tuning")
    print(f"{'='*60}")

    # 创建retain_loaders (排除客户端0)
    retain_loaders = [fed_data.get_client_loader(i, batch_size=64) for i in range(1, 5)]

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

    finetune_result = evaluate_model(finetune_model, test_loader, device)
    finetune_test_acc = finetune_result['accuracy']
    finetune_shadow_results = evaluate_target_model(finetune_model, fed_data, attack_mia, device)
    finetune_simple_results = SimpleMIA.evaluate_threshold_attack(
        finetune_model, forget_loader, test_loader_mia, device
    )

    results.append({
        'Method': 'Fine-tuning',
        'Shadow_ASR': finetune_shadow_results['accuracy'],
        'Shadow_AUC': finetune_shadow_results['auc'],
        'Simple_ASR': finetune_simple_results['accuracy'],
        'Simple_AUC': finetune_simple_results['auc'],
        'Test_Acc': finetune_test_acc
    })

    # 4.4 FedForget (最佳配置)
    print(f"\n{'='*60}")
    print("评估: FedForget (alpha=0.93, lambda_neg=3.5)")
    print(f"{'='*60}")

    # 重新创建客户端 (因为之前的已被修改)
    clients = []
    for i in range(5):
        client_loader = fed_data.get_client_loader(i, batch_size=64)
        if i == 0:
            # 遗忘客户端
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
    print("FedForget遗忘训练...")
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

    fedforget_model = fedforget_server.model
    fedforget_result = evaluate_model(fedforget_model, test_loader, device)
    fedforget_test_acc = fedforget_result['accuracy']
    fedforget_shadow_results = evaluate_target_model(fedforget_model, fed_data, attack_mia, device)
    fedforget_simple_results = SimpleMIA.evaluate_threshold_attack(
        fedforget_model, forget_loader, test_loader_mia, device
    )

    results.append({
        'Method': 'FedForget',
        'Shadow_ASR': fedforget_shadow_results['accuracy'],
        'Shadow_AUC': fedforget_shadow_results['auc'],
        'Simple_ASR': fedforget_simple_results['accuracy'],
        'Simple_AUC': fedforget_simple_results['auc'],
        'Test_Acc': fedforget_test_acc
    })

    # ========== 步骤5: 保存和显示结果 ==========
    df = pd.DataFrame(results)

    print(f"\n{'='*60}")
    print("Shadow Model Attack MIA评估结果")
    print(f"{'='*60}")
    print(df.to_string(index=False))

    # 保存结果
    results_dir = '/home/featurize/work/GJC/fedforget/results'
    os.makedirs(results_dir, exist_ok=True)
    df.to_csv(f'{results_dir}/shadow_mia_evaluation.csv', index=False)
    print(f"\n结果已保存到: {results_dir}/shadow_mia_evaluation.csv")

    # 分析
    print(f"\n{'='*60}")
    print("关键发现:")
    print(f"{'='*60}")

    # 找出隐私保护最好的方法 (ASR最接近50%)
    df['Shadow_Distance_to_50'] = abs(df['Shadow_ASR'] - 50)
    best_privacy_idx = df['Shadow_Distance_to_50'].idxmin()
    best_method = df.loc[best_privacy_idx]

    print(f"\n1. Shadow Model Attack:")
    print(f"   最佳隐私保护: {best_method['Method']}")
    print(f"   ASR = {best_method['Shadow_ASR']:.2f}% (距离50%: {best_method['Shadow_Distance_to_50']:.2f}%)")
    print(f"   AUC = {best_method['Shadow_AUC']:.4f}")

    # SimpleMIA对比
    df['Simple_Distance_to_50'] = abs(df['Simple_ASR'] - 50)
    best_simple_idx = df['Simple_Distance_to_50'].idxmin()
    best_simple_method = df.loc[best_simple_idx]

    print(f"\n2. SimpleMIA:")
    print(f"   最佳隐私保护: {best_simple_method['Method']}")
    print(f"   ASR = {best_simple_method['Simple_ASR']:.2f}% (距离50%: {best_simple_method['Simple_Distance_to_50']:.2f}%)")
    print(f"   AUC = {best_simple_method['Simple_AUC']:.4f}")

    # FedForget分析
    fedforget_row = df[df['Method'] == 'FedForget'].iloc[0]
    print(f"\n3. FedForget性能:")
    print(f"   测试准确率: {fedforget_row['Test_Acc']:.2f}%")
    print(f"   Shadow ASR: {fedforget_row['Shadow_ASR']:.2f}% (SimpleMIA: {fedforget_row['Simple_ASR']:.2f}%)")
    print(f"   Shadow AUC: {fedforget_row['Shadow_AUC']:.4f} (SimpleMIA: {fedforget_row['Simple_AUC']:.4f})")

    print(f"\n{'='*60}")
    print("实验完成!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
