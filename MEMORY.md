# FedForget 项目工作记忆

## 项目信息
- **项目名称**: FedForget - 基于权重调整的联邦遗忘框架
- **GitHub**: https://github.com/ReticG/FedForget
- **服务器**: Featurize.cn RTX 4090
- **工作目录**: `/home/featurize/work/GJC/fedforget` (云同步)
- **开始日期**: 2025-10-04

## 📂 目录结构（Featurize最佳实践）

### 云同步目录（慢但持久）
```
~/work/GJC/fedforget/              ← 主项目目录
├── src/                           ← 源代码
├── scripts/                       ← 实验脚本
├── configs/                       ← 配置文件
├── results/                       ← 重要实验结果（持久保存）
├── MEMORY.md                      ← 本文件
└── *.md                           ← 文档
```

### 本地高速磁盘（快但临时）
```
~/data/                            ← 数据集（用数据集功能自动下载）
~/checkpoints/                     ← 临时checkpoint
~/logs/                            ← 训练日志
```

### 软链接（方便访问）
```
~/work/GJC/fedforget/data_link -> ~/data/
~/work/GJC/fedforget/checkpoints_link -> ~/checkpoints/
~/work/GJC/fedforget/logs_link -> ~/logs/
```

**⚠️ 重要提醒**:
- ✅ 数据集放在 `~/data/`（快速IO）
- ✅ 代码放在 `~/work/GJC/fedforget/`（持久保存）
- ✅ 临时文件放在 `~/checkpoints/` 和 `~/logs/`
- ✅ 重要结果放在 `~/work/GJC/fedforget/results/`
- ⛔ 不要在work目录存放数据集（IO慢）

---

## 当前状态 (2025-10-04 08:35 UTC)

### ✅ 已完成
1. **环境配置**
   - ✓ SSH连接测试成功
   - ✓ GPU: NVIDIA GeForce RTX 4090 (24GB)
   - ✓ Python 3.11.8 + PyTorch 2.2.2 (CUDA 12.1)
   - ✓ 依赖包: NumPy, Pandas, Matplotlib已安装

2. **目录结构**
   - ✓ 项目移至 ~/work/GJC/fedforget/
   - ✓ 创建高速磁盘目录: ~/data/, ~/checkpoints/, ~/logs/
   - ✓ 创建软链接方便访问

3. **文档准备**
   - ✓ spec.md, experiment.md, deployment.md
   - ✓ README.md, MEMORY.md

### 🚧 进行中
- **准备开始编码**: 即将下载数据集和实现核心算法

### ⏳ 待办事项
1. 下载MNIST数据集到 ~/data/
2. 实现核心代码模块
3. 运行快速验证实验
4. 参数预筛选

---

## 实验计划

### 阶段1: 快速验证 (Day 1-2, 当前)
**目标**: 验证FedForget基本可行性  
**预算**: 1台 × 48小时 = ¥90  
**成功标准**: MIA ASR < 60%, Test Acc > 85%

**关键任务**:
- [ ] 下载MNIST → ~/data/mnist/
- [ ] 实现数据加载器 → src/data/datasets.py
- [ ] 实现CNN模型 → src/models/cnn.py
- [ ] 实现FedAvg → src/federated/{client,server}.py
- [ ] 实现FedForget → src/unlearning/fedforget.py
- [ ] 快速实验 → scripts/quick_test.py
- [ ] 参数调优 → λ ∈ {2,3,5,10}, T ∈ {1,2,5}

---

## 代码实现计划

### P0 - 今天完成
1. **数据下载** (~/data/)
   ```python
   # 使用Featurize数据集功能或torchvision
   from torchvision import datasets
   datasets.MNIST(root='~/data', download=True)
   ```

2. **数据加载器** (src/data/datasets.py)
   ```python
   def load_federated_data(num_clients=10):
       # 将MNIST分割给10个客户端
       # 支持IID和Non-IID分布
   ```

3. **CNN模型** (src/models/cnn.py)
   ```python
   class ConvNet(nn.Module):
       # 2 conv layers + 1 fc layer
   ```

4. **FedAvg框架** (src/federated/)
   ```python
   class Client:
       def local_train(self, model, data, epochs=5)
       
   class Server:
       def aggregate(self, client_models, weights)
   ```

5. **快速测试** (scripts/quick_test.py)
   ```bash
   python scripts/quick_test.py --clients 10 --rounds 50
   ```

### P1 - Day 1-2
6. **FedForget核心** (src/unlearning/fedforget.py)
7. **MIA评估** (src/utils/metrics.py)
8. **主实验脚本** (scripts/exp1_baseline.py)

---

## 关键参数

### 联邦学习配置
```python
num_clients = 10
participation_rate = 0.1
local_epochs = 5
batch_size = 32
learning_rate = 0.01
total_rounds = 50
```

### FedForget参数
```python
lambda_forget = 3.0    # 待调优
distill_temp = 2.0     # 待调优
weight_max = 0.5
gamma = 0.2
```

### 文件路径
```python
# 数据
DATA_ROOT = '/home/featurize/data'
MNIST_PATH = f'{DATA_ROOT}/mnist'

# 代码
PROJECT_ROOT = '/home/featurize/work/GJC/fedforget'
SRC_PATH = f'{PROJECT_ROOT}/src'

# 输出（快速磁盘）
CHECKPOINT_DIR = '/home/featurize/checkpoints'
LOG_DIR = '/home/featurize/logs'

# 重要结果（持久保存）
RESULTS_DIR = f'{PROJECT_ROOT}/results'
```

---

## 下一步行动

### 立即执行（按顺序）
1. ✅ 重组目录结构
2. ⏭️ 下载MNIST数据集
3. ⏭️ 创建数据加载脚本
4. ⏭️ 实现基础模型和FedAvg
5. ⏭️ 运行第一个测试

### 预计时间线
- 08:35-09:00: 下载数据 + 实现数据加载器
- 09:00-10:00: 实现CNN + FedAvg
- 10:00-11:00: 快速测试验证
- 11:00-13:00: 实现FedForget核心
- 13:00-15:00: 完整实验运行
- 15:00-18:00: 参数调优

---

## 注意事项

### 存储管理
- work目录配额: 检查 `du -sh ~/work/`
- 当前使用: 76GB
- 数据集存储: 使用 ~/data/（不计入work配额）

### 性能优化
- 数据加载: 从 ~/data/ 读取（快）
- Checkpoint: 保存到 ~/checkpoints/（快）
- 最终模型: 保存到 ~/work/GJC/fedforget/results/（持久）

### Git同步
- 定期提交代码到GitHub
- 仅同步代码和结果，不同步数据集

---

**最后更新**: 2025-10-04 08:35 UTC  
**更新人**: Claude  
**工作目录**: /home/featurize/work/GJC/fedforget
