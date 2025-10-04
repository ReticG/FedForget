"""
联邦学习客户端
实现本地训练和模型更新
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import copy
from typing import Dict, Optional


class Client:
    """联邦学习客户端"""

    def __init__(
        self,
        client_id: int,
        model: nn.Module,
        data_loader: DataLoader,
        device: str = 'cuda',
        lr: float = 0.01,
        momentum: float = 0.9,
        weight_decay: float = 0.0
    ):
        """
        Args:
            client_id: 客户端ID
            model: 模型架构
            data_loader: 本地数据加载器
            device: 设备 ('cuda' or 'cpu')
            lr: 学习率
            momentum: 动量
            weight_decay: 权重衰减
        """
        self.client_id = client_id
        self.model = model.to(device)
        self.data_loader = data_loader
        self.device = device

        # 优化器
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.optimizer = optim.SGD(
            self.model.parameters(),
            lr=lr,
            momentum=momentum,
            weight_decay=weight_decay
        )

        # 损失函数
        self.criterion = nn.CrossEntropyLoss()

        # 统计信息
        self.num_samples = len(data_loader.dataset)

    def local_train(self, epochs: int = 5, verbose: bool = False) -> Dict:
        """
        本地训练

        Args:
            epochs: 训练轮数
            verbose: 是否打印训练信息

        Returns:
            训练统计信息字典
        """
        self.model.train()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_correct = 0
            epoch_samples = 0

            for images, labels in self.data_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                # 前向传播
                self.optimizer.zero_grad()
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                # 反向传播
                loss.backward()
                self.optimizer.step()

                # 统计
                epoch_loss += loss.item() * labels.size(0)
                _, predicted = outputs.max(1)
                epoch_correct += predicted.eq(labels).sum().item()
                epoch_samples += labels.size(0)

            epoch_loss /= epoch_samples
            epoch_acc = 100.0 * epoch_correct / epoch_samples

            if verbose:
                print(f"  Client {self.client_id} | Epoch {epoch+1}/{epochs} | "
                      f"Loss: {epoch_loss:.4f} | Acc: {epoch_acc:.2f}%")

            total_loss += epoch_loss
            total_correct += epoch_correct
            total_samples += epoch_samples

        avg_loss = total_loss / epochs
        avg_acc = 100.0 * total_correct / total_samples

        return {
            'loss': avg_loss,
            'accuracy': avg_acc,
            'num_samples': self.num_samples
        }

    def get_model_parameters(self) -> Dict[str, torch.Tensor]:
        """获取模型参数"""
        return copy.deepcopy(self.model.state_dict())

    def set_model_parameters(self, parameters: Dict[str, torch.Tensor]):
        """设置模型参数"""
        self.model.load_state_dict(parameters)

    def evaluate(self, test_loader: DataLoader) -> Dict:
        """
        评估模型

        Args:
            test_loader: 测试数据加载器

        Returns:
            评估结果字典
        """
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

        avg_loss = total_loss / total_samples
        accuracy = 100.0 * total_correct / total_samples

        return {
            'loss': avg_loss,
            'accuracy': accuracy
        }


class UnlearningClient(Client):
    """
    支持遗忘的客户端
    实现负权重知识蒸馏
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_unlearning = False
        self.global_model = None
        self.local_model = None  # 本地历史模型

    def prepare_unlearning(
        self,
        global_model_params: Dict[str, torch.Tensor],
        local_model_params: Optional[Dict[str, torch.Tensor]] = None
    ):
        """
        准备遗忘: 保存全局模型和本地模型

        Args:
            global_model_params: 全局模型参数
            local_model_params: 本地历史模型参数 (可选)
        """
        self.is_unlearning = True

        # 保存全局模型 (正向知识蒸馏的教师)
        self.global_model = copy.deepcopy(self.model)
        self.global_model.load_state_dict(global_model_params)
        self.global_model.eval()

        # 保存本地模型 (反向知识蒸馏的教师)
        if local_model_params is not None:
            self.local_model = copy.deepcopy(self.model)
            self.local_model.load_state_dict(local_model_params)
            self.local_model.eval()

    def unlearning_train(
        self,
        epochs: int = 5,
        method: str = 'dual_teacher',  # 'dual_teacher' or 'gradient_ascent'
        distill_temp: float = 2.0,
        alpha: float = 0.5,
        lambda_pos: float = 1.0,
        lambda_neg: float = 1.0,
        verbose: bool = False
    ) -> Dict:
        """
        遗忘训练: 支持两种策略
        1. dual_teacher: 双教师知识蒸馏 (需要教师A和B)
        2. gradient_ascent: 梯度上升遗忘 (直接最大化损失)

        Args:
            epochs: 训练轮数
            method: 遗忘方法
            distill_temp: 蒸馏温度
            alpha: 双教师权衡系数
            lambda_pos: 正向蒸馏权重
            lambda_neg: 负向遗忘强度
            verbose: 是否打印信息

        Returns:
            训练统计信息
        """
        if not self.is_unlearning:
            raise ValueError("Must call prepare_unlearning() first")

        self.model.train()

        total_loss = 0.0
        total_samples = 0

        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_samples = 0

            for images, labels in self.data_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                self.optimizer.zero_grad()

                outputs = self.model(images)

                if method == 'gradient_ascent':
                    # 方法1: 梯度上升 - 直接最大化损失
                    loss_forget = self.criterion(outputs, labels)
                    loss = -lambda_neg * loss_forget  # 负损失 = 梯度上升

                elif method == 'dual_teacher':
                    # 方法2: 双教师知识蒸馏
                    if self.global_model is None:
                        raise ValueError("Global model (Teacher A) is required")

                    kl_loss_fn = nn.KLDivLoss(reduction='batchmean')

                    student_log_probs = torch.nn.functional.log_softmax(
                        outputs / distill_temp, dim=1
                    )

                    # 正向蒸馏: 学习全局模型
                    with torch.no_grad():
                        global_logits = self.global_model(images)
                        global_probs = torch.nn.functional.softmax(
                            global_logits / distill_temp, dim=1
                        )

                    loss_positive = kl_loss_fn(student_log_probs, global_probs)

                    # 负向遗忘
                    if self.local_model is not None:
                        # 如果有教师B,远离教师B
                        with torch.no_grad():
                            local_logits = self.local_model(images)
                            local_probs = torch.nn.functional.softmax(
                                local_logits / distill_temp, dim=1
                            )
                        loss_negative = kl_loss_fn(student_log_probs, local_probs)
                        loss = alpha * lambda_pos * loss_positive + \
                               (1 - alpha) * (-lambda_neg) * loss_negative
                    else:
                        # 如果没有教师B,结合梯度上升
                        loss_forget = self.criterion(outputs, labels)
                        loss = alpha * lambda_pos * loss_positive + \
                               (1 - alpha) * (-lambda_neg) * loss_forget

                else:
                    raise ValueError(f"Unknown unlearning method: {method}")

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()

                epoch_loss += loss.item() * images.size(0)
                epoch_samples += images.size(0)

            epoch_loss /= epoch_samples

            if verbose:
                print(f"  UnlearningClient {self.client_id} | Epoch {epoch+1}/{epochs} | "
                      f"Loss: {epoch_loss:.4f}")

            total_loss += epoch_loss
            total_samples += epoch_samples

        avg_loss = total_loss / epochs

        return {
            'loss': avg_loss,
            'num_samples': self.num_samples
        }


if __name__ == '__main__':
    # 测试客户端
    print("测试联邦客户端...")

    from torchvision import datasets, transforms
    from torch.utils.data import DataLoader, Subset
    import sys
    sys.path.append('/home/featurize/work/GJC/fedforget')
    from src.models import ConvNet

    # 准备测试数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    train_data = datasets.MNIST(root='/home/featurize/data', train=True,
                                download=True, transform=transform)

    # 模拟客户端数据
    client_data = Subset(train_data, list(range(1000)))
    client_loader = DataLoader(client_data, batch_size=32, shuffle=True)

    # 创建客户端
    model = ConvNet(num_classes=10, num_channels=1)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    client = Client(
        client_id=0,
        model=model,
        data_loader=client_loader,
        device=device,
        lr=0.01
    )

    # 测试本地训练
    print("测试本地训练...")
    stats = client.local_train(epochs=2, verbose=True)
    print(f"训练完成: Loss={stats['loss']:.4f}, Acc={stats['accuracy']:.2f}%")

    # 测试参数获取和设置
    params = client.get_model_parameters()
    print(f"获取参数成功, 参数数量: {len(params)}")

    client.set_model_parameters(params)
    print("设置参数成功")

    print("\n✓ 客户端测试通过!")
