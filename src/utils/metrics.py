"""
评估指标计算
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Optional
import numpy as np


def evaluate_model(
    model: nn.Module,
    test_loader: DataLoader,
    device: str = 'cuda',
    criterion: Optional[nn.Module] = None
) -> Dict:
    """
    评估模型性能

    Args:
        model: 待评估模型
        test_loader: 测试数据加载器
        device: 设备
        criterion: 损失函数

    Returns:
        包含loss和accuracy的字典
    """
    if criterion is None:
        criterion = nn.CrossEntropyLoss()

    model.eval()
    model = model.to(device)

    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item() * labels.size(0)
            _, predicted = outputs.max(1)
            total_correct += predicted.eq(labels).sum().item()
            total_samples += labels.size(0)

    avg_loss = total_loss / total_samples
    accuracy = 100.0 * total_correct / total_samples

    return {
        'loss': avg_loss,
        'accuracy': accuracy,
        'num_samples': total_samples
    }


def compute_accuracy(
    model: nn.Module,
    data_loader: DataLoader,
    device: str = 'cuda'
) -> float:
    """
    计算模型准确率

    Args:
        model: 待评估模型
        data_loader: 数据加载器
        device: 设备

    Returns:
        准确率 (百分比)
    """
    model.eval()
    model = model.to(device)

    total_correct = 0
    total_samples = 0

    with torch.no_grad():
        for images, labels in data_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            _, predicted = outputs.max(1)
            total_correct += predicted.eq(labels).sum().item()
            total_samples += labels.size(0)

    return 100.0 * total_correct / total_samples


def compute_class_accuracy(
    model: nn.Module,
    data_loader: DataLoader,
    num_classes: int = 10,
    device: str = 'cuda'
) -> Dict[int, float]:
    """
    计算每个类别的准确率

    Args:
        model: 待评估模型
        data_loader: 数据加载器
        num_classes: 类别数量
        device: 设备

    Returns:
        {class_id: accuracy} 字典
    """
    model.eval()
    model = model.to(device)

    class_correct = np.zeros(num_classes)
    class_total = np.zeros(num_classes)

    with torch.no_grad():
        for images, labels in data_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            _, predicted = outputs.max(1)

            for label, pred in zip(labels, predicted):
                class_total[label] += 1
                if label == pred:
                    class_correct[label] += 1

    class_accuracy = {}
    for c in range(num_classes):
        if class_total[c] > 0:
            class_accuracy[c] = 100.0 * class_correct[c] / class_total[c]
        else:
            class_accuracy[c] = 0.0

    return class_accuracy


def compute_forgetting_score(
    acc_before: float,
    acc_after: float
) -> float:
    """
    计算遗忘分数 (Normalized Forgetting Score)

    Args:
        acc_before: 遗忘前准确率
        acc_after: 遗忘后准确率

    Returns:
        遗忘分数 (0-1之间, 越大表示遗忘越彻底)
    """
    if acc_before == 0:
        return 0.0

    nfs = (acc_before - acc_after) / acc_before
    return max(0.0, min(1.0, nfs))  # 限制在[0, 1]


if __name__ == '__main__':
    # 测试评估指标
    print("测试评估指标...")

    import sys
    sys.path.append('/home/featurize/work/GJC/fedforget')
    from src.models import ConvNet
    from torchvision import datasets, transforms

    # 准备测试数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    test_data = datasets.MNIST(
        root='/home/featurize/data',
        train=False,
        download=True,
        transform=transform
    )

    test_loader = DataLoader(test_data, batch_size=128, shuffle=False)

    # 创建模型
    model = ConvNet(num_classes=10, num_channels=1)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 测试评估
    print("\n测试模型评估...")
    results = evaluate_model(model, test_loader, device=device)
    print(f"Loss: {results['loss']:.4f}")
    print(f"Accuracy: {results['accuracy']:.2f}%")

    # 测试准确率计算
    print("\n测试准确率计算...")
    acc = compute_accuracy(model, test_loader, device=device)
    print(f"Accuracy: {acc:.2f}%")

    # 测试类别准确率
    print("\n测试类别准确率...")
    class_acc = compute_class_accuracy(model, test_loader, num_classes=10, device=device)
    for c, acc in class_acc.items():
        print(f"Class {c}: {acc:.2f}%")

    # 测试遗忘分数
    print("\n测试遗忘分数...")
    nfs = compute_forgetting_score(acc_before=85.0, acc_after=15.0)
    print(f"Forgetting Score: {nfs:.4f}")

    print("\n✓ 评估指标测试通过!")
