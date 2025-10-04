"""
联邦学习服务器
实现FedAvg聚合和模型分发
"""

import torch
import torch.nn as nn
from typing import List, Dict, Optional
import copy
import numpy as np


class Server:
    """联邦学习服务器"""

    def __init__(
        self,
        model: nn.Module,
        device: str = 'cuda'
    ):
        """
        Args:
            model: 全局模型架构
            device: 设备 ('cuda' or 'cpu')
        """
        self.model = model.to(device)
        self.device = device

        # 客户端权重记录
        self.client_weights = {}
        self.unlearning_clients = set()  # 正在遗忘的客户端集合

    def aggregate(
        self,
        client_models: List[Dict[str, torch.Tensor]],
        client_weights: Optional[List[float]] = None,
        client_ids: Optional[List[int]] = None
    ) -> Dict[str, torch.Tensor]:
        """
        FedAvg聚合: 加权平均客户端模型

        Args:
            client_models: 客户端模型参数列表
            client_weights: 客户端权重列表 (默认使用均匀权重)
            client_ids: 客户端ID列表 (用于记录权重)

        Returns:
            聚合后的全局模型参数
        """
        if len(client_models) == 0:
            raise ValueError("No client models to aggregate")

        # 默认使用均匀权重
        if client_weights is None:
            client_weights = [1.0 / len(client_models)] * len(client_models)
        else:
            # 归一化权重
            total_weight = sum(client_weights)
            client_weights = [w / total_weight for w in client_weights]

        # 记录权重
        if client_ids is not None:
            for cid, weight in zip(client_ids, client_weights):
                self.client_weights[cid] = weight

        # 初始化聚合模型
        aggregated_params = {}

        # 对每个参数进行加权平均
        for param_name in client_models[0].keys():
            # 收集所有客户端的该参数
            param_list = [model[param_name] for model in client_models]

            # 加权求和
            weighted_sum = torch.zeros_like(param_list[0])
            for param, weight in zip(param_list, client_weights):
                weighted_sum += param * weight

            aggregated_params[param_name] = weighted_sum

        return aggregated_params

    def set_model_parameters(self, parameters: Dict[str, torch.Tensor]):
        """设置全局模型参数"""
        self.model.load_state_dict(parameters)

    def get_model_parameters(self) -> Dict[str, torch.Tensor]:
        """获取全局模型参数"""
        return copy.deepcopy(self.model.state_dict())

    def evaluate(self, test_loader, criterion=None) -> Dict:
        """
        评估全局模型

        Args:
            test_loader: 测试数据加载器
            criterion: 损失函数 (默认使用交叉熵)

        Returns:
            评估结果字典
        """
        if criterion is None:
            criterion = nn.CrossEntropyLoss()

        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                outputs = self.model(images)
                loss = criterion(outputs, labels)

                total_loss += loss.item() * labels.size(0)
                _, predicted = outputs.max(1)
                total_correct += predicted.eq(labels).sum().item()
                total_samples += labels.size(0)

        avg_loss = total_loss / total_samples
        accuracy = 100.0 * total_correct / total_samples

        return {
            'loss': avg_loss,
            'accuracy': accuracy
        }


class FedForgetServer(Server):
    """
    支持FedForget的服务器
    实现动态权重调整策略
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # FedForget特定参数
        self.lambda_forget = 3.0  # 遗忘权重系数
        self.weight_max = 0.5     # 单客户端权重上限
        self.gamma = 0.2          # 渐进调整率

        # 状态跟踪
        self.unlearning_clients = {}  # {client_id: unlearning_round}
        self.unlearning_progress = {}  # {client_id: progress_ratio}

    def compute_fedforget_weights(
        self,
        client_ids: List[int],
        client_num_samples: List[int],
        current_round: int
    ) -> List[float]:
        """
        计算FedForget权重: 动态调整遗忘客户端的聚合权重

        Args:
            client_ids: 参与本轮的客户端ID列表
            client_num_samples: 各客户端的样本数量
            current_round: 当前训练轮次

        Returns:
            调整后的聚合权重列表
        """
        num_clients = len(client_ids)

        # 基础权重: 按样本数量比例
        total_samples = sum(client_num_samples)
        base_weights = [n / total_samples for n in client_num_samples]

        # 调整遗忘客户端的权重
        adjusted_weights = []

        for i, cid in enumerate(client_ids):
            if cid in self.unlearning_clients:
                # 遗忘客户端: 增加权重
                unlearn_start_round = self.unlearning_clients[cid]
                rounds_since_unlearn = current_round - unlearn_start_round

                # 遗忘进度 (0 -> 1)
                progress = min(1.0, rounds_since_unlearn / 10)  # 假设10轮完成遗忘
                self.unlearning_progress[cid] = progress

                # 遗忘权重: 初期高，后期逐渐降低
                forget_boost = self.lambda_forget * (1.0 - progress)
                weight = base_weights[i] * (1.0 + forget_boost)

                # 应用权重上限约束
                weight = min(weight, self.weight_max)

                adjusted_weights.append(weight)
            else:
                # 常规客户端: 保持基础权重
                adjusted_weights.append(base_weights[i])

        # 归一化权重
        total_weight = sum(adjusted_weights)
        adjusted_weights = [w / total_weight for w in adjusted_weights]

        return adjusted_weights

    def register_unlearning_client(self, client_id: int, current_round: int):
        """
        注册遗忘客户端

        Args:
            client_id: 客户端ID
            current_round: 当前轮次
        """
        self.unlearning_clients[client_id] = current_round
        self.unlearning_progress[client_id] = 0.0
        print(f"[Server] 注册遗忘客户端 {client_id} at round {current_round}")

    def unregister_unlearning_client(self, client_id: int):
        """
        取消注册遗忘客户端 (遗忘完成)

        Args:
            client_id: 客户端ID
        """
        if client_id in self.unlearning_clients:
            del self.unlearning_clients[client_id]
            print(f"[Server] 遗忘客户端 {client_id} 完成遗忘")

    def aggregate_with_fedforget(
        self,
        client_models: List[Dict[str, torch.Tensor]],
        client_ids: List[int],
        client_num_samples: List[int],
        current_round: int
    ) -> Dict[str, torch.Tensor]:
        """
        FedForget聚合: 使用动态权重调整

        Args:
            client_models: 客户端模型参数列表
            client_ids: 客户端ID列表
            client_num_samples: 各客户端样本数量列表
            current_round: 当前训练轮次

        Returns:
            聚合后的全局模型参数
        """
        # 计算FedForget权重
        weights = self.compute_fedforget_weights(
            client_ids,
            client_num_samples,
            current_round
        )

        # 打印权重信息
        print(f"\n[Round {current_round}] 聚合权重:")
        for cid, weight in zip(client_ids, weights):
            status = " (遗忘中)" if cid in self.unlearning_clients else ""
            print(f"  Client {cid}: {weight:.4f}{status}")

        # 使用计算的权重进行聚合
        return self.aggregate(client_models, weights, client_ids)


if __name__ == '__main__':
    # 测试服务器
    print("测试联邦服务器...")

    import sys
    sys.path.append('/home/featurize/work/GJC/fedforget')
    from src.models import ConvNet

    # 创建服务器
    model = ConvNet(num_classes=10, num_channels=1)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    server = Server(model=model, device=device)

    # 模拟客户端模型
    client_models = [
        copy.deepcopy(model.state_dict()),
        copy.deepcopy(model.state_dict()),
        copy.deepcopy(model.state_dict())
    ]

    # 测试聚合
    print("\n测试FedAvg聚合...")
    aggregated = server.aggregate(
        client_models,
        client_weights=[0.3, 0.5, 0.2],
        client_ids=[0, 1, 2]
    )
    print(f"聚合成功, 参数数量: {len(aggregated)}")

    # 测试FedForgetServer
    print("\n测试FedForget服务器...")
    fedforget_server = FedForgetServer(model=model, device=device)

    # 注册遗忘客户端
    fedforget_server.register_unlearning_client(client_id=1, current_round=50)

    # 计算FedForget权重
    weights = fedforget_server.compute_fedforget_weights(
        client_ids=[0, 1, 2],
        client_num_samples=[1000, 1000, 1000],
        current_round=50
    )
    print(f"FedForget权重: {weights}")

    # 使用FedForget聚合
    aggregated_fedforget = fedforget_server.aggregate_with_fedforget(
        client_models,
        client_ids=[0, 1, 2],
        client_num_samples=[1000, 1000, 1000],
        current_round=50
    )
    print(f"FedForget聚合成功")

    print("\n✓ 服务器测试通过!")
