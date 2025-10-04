"""
遗忘算法实现
包含多种遗忘策略
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
import copy
from abc import ABC, abstractmethod
from typing import Dict, Optional


class UnlearningMethod(ABC):
    """遗忘方法基类"""

    @abstractmethod
    def unlearn(
        self,
        model: nn.Module,
        forget_loader: DataLoader,
        retain_loader: Optional[DataLoader],
        **kwargs
    ) -> nn.Module:
        """
        执行遗忘

        Args:
            model: 待遗忘的模型
            forget_loader: 需要遗忘的数据加载器
            retain_loader: 需要保留的数据加载器 (可选)
            **kwargs: 其他参数

        Returns:
            遗忘后的模型
        """
        pass


class NegativeKDUnlearning(UnlearningMethod):
    """
    负权重知识蒸馏遗忘
    改进版: 增加多种损失项
    """

    def __init__(
        self,
        device: str = 'cuda',
        lr: float = 0.01,
        epochs: int = 5,
        distill_temp: float = 2.0,
        lambda_negative: float = 5.0,  # 增大负权重
        lambda_retain: float = 1.0,    # 保留数据损失权重
        use_gradient_ascent: bool = True  # 是否在遗忘数据上使用梯度上升
    ):
        self.device = device
        self.lr = lr
        self.epochs = epochs
        self.distill_temp = distill_temp
        self.lambda_negative = lambda_negative
        self.lambda_retain = lambda_retain
        self.use_gradient_ascent = use_gradient_ascent

    def unlearn(
        self,
        model: nn.Module,
        forget_loader: DataLoader,
        retain_loader: Optional[DataLoader] = None,
        global_model: Optional[nn.Module] = None,
        **kwargs
    ) -> nn.Module:
        """
        执行负权重知识蒸馏遗忘

        Args:
            model: 待遗忘的模型
            forget_loader: 遗忘数据加载器
            retain_loader: 保留数据加载器
            global_model: 全局模型 (用于正向蒸馏)

        Returns:
            遗忘后的模型
        """
        model = model.to(self.device)
        model.train()

        optimizer = torch.optim.SGD(model.parameters(), lr=self.lr, momentum=0.9)
        criterion = nn.CrossEntropyLoss()
        kl_loss_fn = nn.KLDivLoss(reduction='batchmean')

        for epoch in range(self.epochs):
            epoch_loss = 0.0
            num_batches = 0

            # 遗忘数据上的训练
            for images, labels in forget_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                optimizer.zero_grad()

                # 学生模型输出
                outputs = model(images)

                if self.use_gradient_ascent:
                    # 策略1: 梯度上升 - 最大化损失
                    loss_forget = -criterion(outputs, labels)
                else:
                    # 策略2: 随机标签 - 打乱正确关联
                    random_labels = torch.randint(0, outputs.size(1), labels.size(), device=self.device)
                    loss_forget = criterion(outputs, random_labels)

                loss = self.lambda_negative * loss_forget

                # 如果有全局模型,添加正向蒸馏约束
                if global_model is not None:
                    global_model.eval()
                    with torch.no_grad():
                        global_outputs = global_model(images)
                        global_probs = F.softmax(global_outputs / self.distill_temp, dim=1)

                    student_log_probs = F.log_softmax(outputs / self.distill_temp, dim=1)
                    kd_loss = kl_loss_fn(student_log_probs, global_probs)

                    # 平衡遗忘和保留全局知识
                    loss = loss + 0.5 * kd_loss

                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                num_batches += 1

            # 在保留数据上微调(如果提供)
            if retain_loader is not None:
                for images, labels in retain_loader:
                    images, labels = images.to(self.device), labels.to(self.device)

                    optimizer.zero_grad()
                    outputs = model(images)
                    loss_retain = criterion(outputs, labels)

                    loss = self.lambda_retain * loss_retain
                    loss.backward()
                    optimizer.step()

                    epoch_loss += loss.item()
                    num_batches += 1

            avg_loss = epoch_loss / num_batches if num_batches > 0 else 0
            print(f"  Unlearning Epoch {epoch+1}/{self.epochs} | Loss: {avg_loss:.4f}")

        return model


class GradientAscentUnlearning(UnlearningMethod):
    """
    梯度上升遗忘
    在遗忘数据上最大化损失
    """

    def __init__(
        self,
        device: str = 'cuda',
        lr: float = 0.001,
        epochs: int = 5,
        max_loss_threshold: float = 3.0  # 最大损失阈值,防止过度遗忘
    ):
        self.device = device
        self.lr = lr
        self.epochs = epochs
        self.max_loss_threshold = max_loss_threshold

    def unlearn(
        self,
        model: nn.Module,
        forget_loader: DataLoader,
        retain_loader: Optional[DataLoader] = None,
        **kwargs
    ) -> nn.Module:
        """
        执行梯度上升遗忘

        Args:
            model: 待遗忘的模型
            forget_loader: 遗忘数据加载器
            retain_loader: 保留数据加载器 (可选,用于交替训练)

        Returns:
            遗忘后的模型
        """
        model = model.to(self.device)
        model.train()

        optimizer = torch.optim.SGD(model.parameters(), lr=self.lr, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        for epoch in range(self.epochs):
            # 在遗忘数据上梯度上升
            for images, labels in forget_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)

                # 梯度上升: 最大化损失
                if loss.item() < self.max_loss_threshold:
                    (-loss).backward()  # 负梯度
                    optimizer.step()

            # 在保留数据上正常训练(如果提供)
            if retain_loader is not None:
                for images, labels in retain_loader:
                    images, labels = images.to(self.device), labels.to(self.device)

                    optimizer.zero_grad()
                    outputs = model(images)
                    loss = criterion(outputs, labels)

                    loss.backward()
                    optimizer.step()

            print(f"  GradientAscent Epoch {epoch+1}/{self.epochs}")

        return model


class FinetuningUnlearning(UnlearningMethod):
    """
    微调遗忘
    在保留数据上重新训练
    """

    def __init__(
        self,
        device: str = 'cuda',
        lr: float = 0.01,
        epochs: int = 10
    ):
        self.device = device
        self.lr = lr
        self.epochs = epochs

    def unlearn(
        self,
        model: nn.Module,
        forget_loader: DataLoader,
        retain_loader: DataLoader,
        **kwargs
    ) -> nn.Module:
        """
        执行微调遗忘

        Args:
            model: 待遗忘的模型
            forget_loader: 遗忘数据加载器 (不使用)
            retain_loader: 保留数据加载器

        Returns:
            遗忘后的模型
        """
        if retain_loader is None:
            raise ValueError("Fine-tuning requires retain_loader")

        model = model.to(self.device)
        model.train()

        optimizer = torch.optim.SGD(model.parameters(), lr=self.lr, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        for epoch in range(self.epochs):
            for images, labels in retain_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)

                loss.backward()
                optimizer.step()

            print(f"  Finetuning Epoch {epoch+1}/{self.epochs}")

        return model


class ScrubUnlearning(UnlearningMethod):
    """
    Scrub遗忘 (最大化遗忘数据损失 + 保持保留数据性能)
    """

    def __init__(
        self,
        device: str = 'cuda',
        lr: float = 0.001,
        epochs: int = 5,
        alpha: float = 0.5  # 遗忘和保留的权衡
    ):
        self.device = device
        self.lr = lr
        self.epochs = epochs
        self.alpha = alpha

    def unlearn(
        self,
        model: nn.Module,
        forget_loader: DataLoader,
        retain_loader: DataLoader,
        **kwargs
    ) -> nn.Module:
        """
        执行Scrub遗忘

        Args:
            model: 待遗忘的模型
            forget_loader: 遗忘数据加载器
            retain_loader: 保留数据加载器

        Returns:
            遗忘后的模型
        """
        if retain_loader is None:
            raise ValueError("Scrub requires retain_loader")

        model = model.to(self.device)
        model.train()

        optimizer = torch.optim.SGD(model.parameters(), lr=self.lr, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        for epoch in range(self.epochs):
            # 合并遗忘和保留数据的batch
            forget_iter = iter(forget_loader)
            retain_iter = iter(retain_loader)

            num_batches = max(len(forget_loader), len(retain_loader))

            for _ in range(num_batches):
                optimizer.zero_grad()
                total_loss = 0.0

                # 遗忘数据: 最大化损失
                try:
                    forget_images, forget_labels = next(forget_iter)
                    forget_images = forget_images.to(self.device)
                    forget_labels = forget_labels.to(self.device)

                    forget_outputs = model(forget_images)
                    loss_forget = -criterion(forget_outputs, forget_labels)  # 负损失
                    total_loss += self.alpha * loss_forget
                except StopIteration:
                    pass

                # 保留数据: 最小化损失
                try:
                    retain_images, retain_labels = next(retain_iter)
                    retain_images = retain_images.to(self.device)
                    retain_labels = retain_labels.to(self.device)

                    retain_outputs = model(retain_images)
                    loss_retain = criterion(retain_outputs, retain_labels)
                    total_loss += (1 - self.alpha) * loss_retain
                except StopIteration:
                    pass

                if total_loss != 0.0:
                    total_loss.backward()
                    optimizer.step()

            print(f"  Scrub Epoch {epoch+1}/{self.epochs}")

        return model


if __name__ == '__main__':
    # 测试遗忘方法
    print("测试遗忘方法...")

    import sys
    sys.path.append('/home/featurize/work/GJC/fedforget')
    from src.models import ConvNet
    from torchvision import datasets, transforms
    from torch.utils.data import Subset

    # 准备测试数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    train_data = datasets.MNIST(root='/home/featurize/data', train=True,
                                download=True, transform=transform)

    # 模拟遗忘数据和保留数据
    forget_data = Subset(train_data, list(range(1000)))
    retain_data = Subset(train_data, list(range(1000, 2000)))

    forget_loader = DataLoader(forget_data, batch_size=32, shuffle=True)
    retain_loader = DataLoader(retain_data, batch_size=32, shuffle=True)

    # 创建模型
    model = ConvNet(num_classes=10, num_channels=1)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 测试NegativeKD遗忘
    print("\n测试负权重知识蒸馏遗忘...")
    neg_kd = NegativeKDUnlearning(device=device, epochs=2, lambda_negative=5.0)
    model_neg_kd = neg_kd.unlearn(model, forget_loader, retain_loader)
    print("✓ 负权重知识蒸馏测试通过")

    # 测试梯度上升遗忘
    print("\n测试梯度上升遗忘...")
    model = ConvNet(num_classes=10, num_channels=1)
    grad_ascent = GradientAscentUnlearning(device=device, epochs=2)
    model_grad = grad_ascent.unlearn(model, forget_loader, retain_loader)
    print("✓ 梯度上升遗忘测试通过")

    # 测试Scrub遗忘
    print("\n测试Scrub遗忘...")
    model = ConvNet(num_classes=10, num_channels=1)
    scrub = ScrubUnlearning(device=device, epochs=2, alpha=0.5)
    model_scrub = scrub.unlearn(model, forget_loader, retain_loader)
    print("✓ Scrub遗忘测试通过")

    print("\n✓ 所有遗忘方法测试通过!")
