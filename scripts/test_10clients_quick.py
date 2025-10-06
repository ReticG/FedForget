"""
快速测试10客户端实验是否能正常启动

只运行1个epoch的预训练来验证代码无bug
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
from src.data.datasets import load_federated_data
from src.models.cnn import ConvNet
from src.federated.client import Client

def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")

    # 设置随机种子
    seed = 42
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    print("\n加载数据...")
    fed_data = load_federated_data(
        dataset_name='cifar10',
        num_clients=10,  # 10个客户端
        data_dist='noniid',
        dirichlet_alpha=0.5,
        data_root='/home/featurize/data'
    )

    # 创建模型
    model = ConvNet(num_classes=10, num_channels=3).to(device)

    print("\n创建客户端...")
    clients = []
    for i in range(10):
        client_loader = fed_data.get_client_loader(i, batch_size=64)
        client = Client(
            client_id=i,
            model=model,
            data_loader=client_loader,
            device=device,
            lr=0.01
        )
        clients.append(client)
        print(f"  客户端 {i}: {client.num_samples} 样本")

    print("\n快速测试训练 (1个epoch)...")
    try:
        clients[0].local_train(epochs=1, verbose=True)
        print("\n✅ 测试成功! 10客户端实验可以正常运行")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
