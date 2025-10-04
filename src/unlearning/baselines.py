"""
机器遗忘基线方法

实现两种基线:
1. Retrain - 从头重新训练 (理想的遗忘效果)
2. Fine-tuning - 在剩余数据上继续训练
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, ConcatDataset
from typing import Dict, List, Optional
import copy


class RetrainBaseline:
    """
    Retrain基线: 从头重新训练,排除遗忘客户端
    这是理想的遗忘效果(完全没有遗忘数据的影响)
    """

    def __init__(
        self,
        model: nn.Module,
        device: str = 'cuda',
        lr: float = 0.01,
        momentum: float = 0.9
    ):
        """
        Args:
            model: 模型架构(会被重新初始化)
            device: 设备
            lr: 学习率
            momentum: 动量
        """
        self.model = model.to(device)
        self.device = device
        self.lr = lr
        self.momentum = momentum

        # 重新初始化模型
        self._reset_model()

        self.optimizer = optim.SGD(
            self.model.parameters(),
            lr=lr,
            momentum=momentum
        )
        self.criterion = nn.CrossEntropyLoss()

    def _reset_model(self):
        """重新初始化模型参数"""
        def init_weights(m):
            if isinstance(m, (nn.Conv2d, nn.Linear)):
                nn.init.kaiming_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

        self.model.apply(init_weights)

    def retrain(
        self,
        retain_loaders: List[DataLoader],
        rounds: int = 10,
        local_epochs: int = 2,
        verbose: bool = False
    ) -> Dict:
        """
        在保留数据上重新训练

        Args:
            retain_loaders: 保留客户端的数据加载器列表
            rounds: 联邦学习轮数
            local_epochs: 每轮本地训练epoch数
            verbose: 是否打印信息

        Returns:
            训练统计信息
        """
        for round_idx in range(rounds):
            round_loss = 0.0
            round_samples = 0

            # 每个保留客户端本地训练
            client_models = []
            client_weights = []

            for client_id, loader in enumerate(retain_loaders):
                # 创建本地模型副本
                local_model = copy.deepcopy(self.model)
                local_optimizer = optim.SGD(
                    local_model.parameters(),
                    lr=self.lr,
                    momentum=self.momentum
                )

                # 本地训练
                local_model.train()
                for epoch in range(local_epochs):
                    for images, labels in loader:
                        images, labels = images.to(self.device), labels.to(self.device)

                        local_optimizer.zero_grad()
                        outputs = local_model(images)
                        loss = self.criterion(outputs, labels)
                        loss.backward()
                        local_optimizer.step()

                        round_loss += loss.item() * labels.size(0)
                        round_samples += labels.size(0)

                client_models.append(local_model.state_dict())
                client_weights.append(len(loader.dataset))

            # FedAvg聚合
            self._fedavg_aggregate(client_models, client_weights)

            if verbose:
                avg_loss = round_loss / round_samples
                print(f"Retrain Round {round_idx+1}/{rounds} | Loss: {avg_loss:.4f}")

        return {'method': 'retrain'}

    def _fedavg_aggregate(
        self,
        client_models: List[Dict[str, torch.Tensor]],
        client_weights: List[int]
    ):
        """FedAvg聚合"""
        total_samples = sum(client_weights)
        aggregated = {}

        for key in client_models[0].keys():
            aggregated[key] = sum(
                w * client_models[i][key] for i, w in enumerate(client_weights)
            ) / total_samples

        self.model.load_state_dict(aggregated)

    def get_model_parameters(self) -> Dict[str, torch.Tensor]:
        """获取模型参数"""
        return copy.deepcopy(self.model.state_dict())

    def evaluate(self, test_loader: DataLoader) -> Dict:
        """评估模型"""
        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                total_loss += loss.item() * labels.size(0)
                _, predicted = outputs.max(1)
                total_correct += predicted.eq(labels).sum().item()
                total_samples += labels.size(0)

        return {
            'loss': total_loss / total_samples,
            'accuracy': 100.0 * total_correct / total_samples
        }


class FineTuningBaseline:
    """
    Fine-tuning基线: 在保留数据上继续训练
    使用预训练模型,在排除遗忘客户端后的数据上fine-tune
    """

    def __init__(
        self,
        model: nn.Module,
        pretrained_params: Dict[str, torch.Tensor],
        device: str = 'cuda',
        lr: float = 0.001,  # 通常fine-tuning使用更小的学习率
        momentum: float = 0.9
    ):
        """
        Args:
            model: 模型架构
            pretrained_params: 预训练模型参数
            device: 设备
            lr: 学习率(建议比预训练小)
            momentum: 动量
        """
        self.model = model.to(device)
        self.device = device
        self.lr = lr
        self.momentum = momentum

        # 加载预训练参数
        self.model.load_state_dict(pretrained_params)

        self.optimizer = optim.SGD(
            self.model.parameters(),
            lr=lr,
            momentum=momentum
        )
        self.criterion = nn.CrossEntropyLoss()

    def finetune(
        self,
        retain_loaders: List[DataLoader],
        rounds: int = 5,
        local_epochs: int = 2,
        verbose: bool = False
    ) -> Dict:
        """
        在保留数据上fine-tune

        Args:
            retain_loaders: 保留客户端的数据加载器列表
            rounds: 联邦学习轮数
            local_epochs: 每轮本地训练epoch数
            verbose: 是否打印信息

        Returns:
            训练统计信息
        """
        for round_idx in range(rounds):
            round_loss = 0.0
            round_samples = 0

            # 每个保留客户端本地训练
            client_models = []
            client_weights = []

            for client_id, loader in enumerate(retain_loaders):
                # 创建本地模型副本
                local_model = copy.deepcopy(self.model)
                local_optimizer = optim.SGD(
                    local_model.parameters(),
                    lr=self.lr,
                    momentum=self.momentum
                )

                # 本地训练
                local_model.train()
                for epoch in range(local_epochs):
                    for images, labels in loader:
                        images, labels = images.to(self.device), labels.to(self.device)

                        local_optimizer.zero_grad()
                        outputs = local_model(images)
                        loss = self.criterion(outputs, labels)
                        loss.backward()
                        local_optimizer.step()

                        round_loss += loss.item() * labels.size(0)
                        round_samples += labels.size(0)

                client_models.append(local_model.state_dict())
                client_weights.append(len(loader.dataset))

            # FedAvg聚合
            self._fedavg_aggregate(client_models, client_weights)

            if verbose:
                avg_loss = round_loss / round_samples
                print(f"Fine-tune Round {round_idx+1}/{rounds} | Loss: {avg_loss:.4f}")

        return {'method': 'finetune'}

    def _fedavg_aggregate(
        self,
        client_models: List[Dict[str, torch.Tensor]],
        client_weights: List[int]
    ):
        """FedAvg聚合"""
        total_samples = sum(client_weights)
        aggregated = {}

        for key in client_models[0].keys():
            aggregated[key] = sum(
                w * client_models[i][key] for i, w in enumerate(client_weights)
            ) / total_samples

        self.model.load_state_dict(aggregated)

    def get_model_parameters(self) -> Dict[str, torch.Tensor]:
        """获取模型参数"""
        return copy.deepcopy(self.model.state_dict())

    def evaluate(self, test_loader: DataLoader) -> Dict:
        """评估模型"""
        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                total_loss += loss.item() * labels.size(0)
                _, predicted = outputs.max(1)
                total_correct += predicted.eq(labels).sum().item()
                total_samples += labels.size(0)

        return {
            'loss': total_loss / total_samples,
            'accuracy': 100.0 * total_correct / total_samples
        }


if __name__ == '__main__':
    print("测试机器遗忘基线方法...")

    import sys
    sys.path.append('/home/featurize/work/GJC/fedforget')

    from src.data import load_federated_data
    from src.models import ConvNet

    # 加载数据
    fed_data = load_federated_data(
        dataset_name='mnist',
        num_clients=5,
        data_dist='iid',
        data_root='/home/featurize/data'
    )

    test_loader = fed_data.get_test_loader(batch_size=256)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 测试Retrain
    print("\n测试Retrain基线...")
    model = ConvNet(num_classes=10, num_channels=1)
    retrain = RetrainBaseline(model, device=device, lr=0.05)

    retain_loaders = [
        fed_data.get_client_loader(i, batch_size=64)
        for i in [1, 2, 3, 4]  # 排除客户端0
    ]

    retrain.retrain(retain_loaders, rounds=3, local_epochs=2, verbose=True)
    results = retrain.evaluate(test_loader)
    print(f"Retrain结果: Acc={results['accuracy']:.2f}%")

    # 测试Fine-tuning
    print("\n测试Fine-tuning基线...")
    # 先预训练一个模型
    from src.federated import Server, Client
    import numpy as np

    np.random.seed(42)
    torch.manual_seed(42)

    pretrain_model = ConvNet(num_classes=10, num_channels=1)
    server = Server(model=pretrain_model, device=device)

    clients = []
    for i in range(5):
        client_loader = fed_data.get_client_loader(i, batch_size=64)
        client = Client(i, ConvNet(num_classes=10, num_channels=1), client_loader, device, lr=0.05)
        clients.append(client)

    print("预训练5轮...")
    for r in range(5):
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
    print(f"预训练完成: Acc={pretrain_results['accuracy']:.2f}%")

    # Fine-tuning
    pretrained_params = server.get_model_parameters()
    finetune_model = ConvNet(num_classes=10, num_channels=1)
    finetune = FineTuningBaseline(finetune_model, pretrained_params, device=device, lr=0.01)

    finetune.finetune(retain_loaders, rounds=3, local_epochs=2, verbose=True)
    results = finetune.evaluate(test_loader)
    print(f"Fine-tuning结果: Acc={results['accuracy']:.2f}%")

    print("\n✓ 基线方法测试通过!")
