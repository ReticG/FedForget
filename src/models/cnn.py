"""
CNN模型定义
- ConvNet: 2层卷积 + 1层全连接 (FedEraser标准配置)
- LeNet5: 经典卷积网络
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvNet(nn.Module):
    """
    简单卷积网络: 2个卷积层 + 1个全连接层
    用于MNIST, Fashion-MNIST, CIFAR-10等数据集
    """

    def __init__(self, num_classes=10, num_channels=1):
        """
        Args:
            num_classes: 类别数量
            num_channels: 输入通道数 (MNIST:1, CIFAR-10:3)
        """
        super(ConvNet, self).__init__()

        self.conv1 = nn.Conv2d(num_channels, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.25)

        # 计算全连接层输入维度
        # MNIST: 28x28 -> 14x14 -> 7x7
        # CIFAR: 32x32 -> 16x16 -> 8x8
        if num_channels == 1:  # MNIST
            fc_input_dim = 64 * 7 * 7
        else:  # CIFAR
            fc_input_dim = 64 * 8 * 8

        self.fc1 = nn.Linear(fc_input_dim, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        # Conv block 1
        x = self.pool(F.relu(self.conv1(x)))

        # Conv block 2
        x = self.pool(F.relu(self.conv2(x)))

        # Flatten
        x = torch.flatten(x, 1)

        # Fully connected
        x = self.dropout(x)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)

        return x


class LeNet5(nn.Module):
    """
    LeNet-5经典卷积网络
    适用于MNIST和Fashion-MNIST
    """

    def __init__(self, num_classes=10, num_channels=1):
        super(LeNet5, self).__init__()

        self.conv1 = nn.Conv2d(num_channels, 6, kernel_size=5)
        self.conv2 = nn.Conv2d(6, 16, kernel_size=5)
        self.pool = nn.MaxPool2d(2, 2)

        # MNIST: 28x28 -> 24x24 -> 12x12 -> 8x8 -> 4x4
        if num_channels == 1:
            fc1_input_dim = 16 * 4 * 4
        else:  # CIFAR
            fc1_input_dim = 16 * 5 * 5

        self.fc1 = nn.Linear(fc1_input_dim, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def get_model(model_name: str, num_classes: int = 10, num_channels: int = 1):
    """
    模型工厂函数

    Args:
        model_name: 模型名称 ('convnet', 'lenet5')
        num_classes: 类别数量
        num_channels: 输入通道数

    Returns:
        模型实例
    """
    model_name = model_name.lower()

    if model_name == 'convnet':
        return ConvNet(num_classes=num_classes, num_channels=num_channels)
    elif model_name in ['lenet5', 'lenet']:
        return LeNet5(num_classes=num_classes, num_channels=num_channels)
    else:
        raise ValueError(f"Unsupported model: {model_name}")


if __name__ == '__main__':
    # 测试模型
    print("测试CNN模型...")

    # 测试ConvNet - MNIST
    model_mnist = ConvNet(num_classes=10, num_channels=1)
    x_mnist = torch.randn(2, 1, 28, 28)
    out_mnist = model_mnist(x_mnist)
    print(f"ConvNet (MNIST): 输入 {x_mnist.shape} -> 输出 {out_mnist.shape}")

    # 测试ConvNet - CIFAR10
    model_cifar = ConvNet(num_classes=10, num_channels=3)
    x_cifar = torch.randn(2, 3, 32, 32)
    out_cifar = model_cifar(x_cifar)
    print(f"ConvNet (CIFAR10): 输入 {x_cifar.shape} -> 输出 {out_cifar.shape}")

    # 测试LeNet5
    model_lenet = LeNet5(num_classes=10, num_channels=1)
    out_lenet = model_lenet(x_mnist)
    print(f"LeNet5: 输入 {x_mnist.shape} -> 输出 {out_lenet.shape}")

    # 计算参数量
    def count_parameters(model):
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    print(f"\nConvNet参数量: {count_parameters(model_mnist):,}")
    print(f"LeNet5参数量: {count_parameters(model_lenet):,}")

    print("\n✓ 模型测试通过!")
