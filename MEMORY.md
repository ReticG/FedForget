# FedForget 项目工作记忆

## 项目信息
- **项目名称**: FedForget - 基于权重调整的联邦遗忘框架
- **GitHub**: https://github.com/ReticG/FedForget
- **服务器**: Featurize.cn RTX 4090
- **工作目录**: `/home/featurize/fedforget`
- **开始日期**: 2025-10-04

---

## 当前状态 (2025-10-04 08:30 UTC)

### ✅ 已完成
1. **环境配置**
   - ✓ SSH连接测试成功
   - ✓ GPU确认: NVIDIA GeForce RTX 4090 (24GB)
   - ✓ Python 3.11.8 + PyTorch 2.2.2 (CUDA 12.1)
   - ✓ 依赖包: NumPy, Pandas, Matplotlib已安装
   - ✓ 磁盘空间: 657GB 可用

2. **项目结构**
   - ✓ 从GitHub克隆代码
   - ✓ 创建目录结构: src/, results/, checkpoints/, logs/, scripts/, configs/

3. **文档准备**
   - ✓ spec.md - 核心idea和技术方案
   - ✓ experiment.md - 完整实验设计
   - ✓ deployment.md - 4服务器部署方案
   - ✓ README.md - 项目文档

### 🚧 进行中
- **实现核心代码**: 准备开始编写FedForget算法

### ⏳ 待办事项
1. 下载MNIST数据集
2. 实现联邦学习基础框架
3. 实现FedForget核心算法
4. 运行第一个MNIST快速验证实验
5. 参数预筛选
6. Day 2决策：是否扩展到4台服务器

---

## 实验计划

### 阶段1: 快速验证 (Day 1-2, 当前)
**目标**: 验证FedForget基本可行性
**预算**: 1台服务器 × 48小时 = ¥90
**关键指标**: MIA ASR < 60%, Test Acc > 85%

**任务列表**:
- [x] 环境配置
- [x] 项目结构创建
- [ ] 实现核心代码模块
  - [ ] `src/data/datasets.py` - 数据加载器
  - [ ] `src/models/cnn.py` - 模型定义
  - [ ] `src/federated/client.py` - 联邦客户端
  - [ ] `src/federated/server.py` - 联邦服务器
  - [ ] `src/unlearning/fedforget.py` - FedForget核心算法
  - [ ] `src/utils/metrics.py` - 评估指标（MIA）
- [ ] MNIST快速实验
- [ ] 参数预筛选 (λ ∈ {2,3,5,10}, T ∈ {1,2,5})

### 阶段2: 主实验并行 (Day 3-7)
**条件**: 阶段1验证成功后
**预算**: 4台服务器 × 120小时 = ¥898

### 阶段3: 补充验证 (Day 8-10)
**预算**: 2台服务器 × 72小时 = ¥269

---

## 技术方案核心要点

### FedForget算法
1. **客户端侧**: 负权重知识蒸馏
   - 正向学习: 从全局模型学习其他客户端知识
   - 反向学习: 移除自身历史贡献
   - 参数: λ_forget (遗忘权重), T (蒸馏温度)

2. **服务器侧**: 动态权重调整
   - 遗忘客户端权重 = 基础权重 × 遗忘因子 × 质量因子
   - 权重约束: w_max (单客户端上限)
   - 渐进调整: γ (调整率)

3. **评估指标**:
   - MIA ASR (成员推断攻击成功率): 目标 ≈ 50%
   - Test Accuracy: 目标 > 95% × Retrain
   - Speedup: 目标 ≥ 5×

---

## 代码实现优先级

### P0 (最高优先级 - 今天完成)
1. **数据加载** (`src/data/datasets.py`)
   - MNIST数据集下载和分割
   - 联邦数据分布（IID）
   
2. **基础模型** (`src/models/cnn.py`)
   - ConvNet (2 conv + 1 fc)
   
3. **联邦学习框架** (`src/federated/`)
   - FedAvg基线实现
   - 客户端本地训练
   - 服务器聚合
   
4. **快速验证脚本** (`scripts/quick_test.py`)
   - 10个客户端 × 10轮训练
   - 验证基础功能

### P1 (高优先级 - Day 1-2)
5. **FedForget核心** (`src/unlearning/fedforget.py`)
   - 负权重蒸馏
   - 动态权重调整
   
6. **评估指标** (`src/utils/metrics.py`)
   - MIA实现（影子模型）
   - Test Accuracy

7. **主实验脚本** (`scripts/exp1_baseline.py`)
   - 参数网格搜索
   - 结果保存

### P2 (中优先级 - 后续)
8. 基线方法实现 (FedEraser, Fine-tuning)
9. 可视化工具
10. W&B集成

---

## 关键参数配置

### 联邦学习配置
```python
num_clients = 10
participation_rate = 0.1  # 每轮10%客户端
local_epochs = 5
batch_size = 32
learning_rate = 0.01
total_rounds = 50  # 快速验证用50轮
```

### FedForget参数
```python
lambda_forget = 3.0  # 遗忘权重系数 (待调优)
distill_temp = 2.0   # 蒸馏温度 (待调优)
weight_max = 0.5     # 单客户端权重上限
gamma = 0.2          # 渐进调整率
```

### 遗忘场景
```python
unlearn_client_id = 5  # 遗忘第5个客户端
unlearn_ratio = 0.2    # 遗忘20%数据
unlearn_at_round = 30  # 第30轮开始遗忘
```

---

## 数据集信息

### MNIST
- Train: 60,000 samples
- Test: 10,000 samples
- Classes: 10
- 每客户端: 6,000 samples (10个客户端)
- 遗忘比例: 10% = 600 samples

### 下载命令
```python
from torchvision import datasets
datasets.MNIST(root=./data, train=True, download=True)
datasets.MNIST(root=./data, train=False, download=True)
```

---

## 预期结果 (快速验证)

### 成功标准
- MIA ASR < 60% (遗忘效果显著)
- Test Acc > 85% (模型效用保持)
- 训练时间 < 3小时 (效率验证)

### 决策点 (Day 2)
- ✅ 若达标 → 扩展到4台服务器，进入阶段2
- ❌ 若不达标 → 调整算法或终止项目

---

## 文件路径速查

### 核心代码
- `~/fedforget/src/data/datasets.py` - 数据加载
- `~/fedforget/src/models/cnn.py` - 模型定义
- `~/fedforget/src/federated/client.py` - 客户端
- `~/fedforget/src/federated/server.py` - 服务器
- `~/fedforget/src/unlearning/fedforget.py` - FedForget算法
- `~/fedforget/src/utils/metrics.py` - 评估指标

### 实验脚本
- `~/fedforget/scripts/quick_test.py` - 快速验证
- `~/fedforget/scripts/download_data.py` - 数据下载
- `~/fedforget/scripts/exp1_baseline.py` - 实验1

### 结果输出
- `~/fedforget/results/` - 实验结果
- `~/fedforget/checkpoints/` - 模型检查点
- `~/fedforget/logs/` - 训练日志

---

## 下一步行动 (立即执行)

1. **创建数据下载脚本** → `scripts/download_data.py`
2. **实现数据加载器** → `src/data/datasets.py`
3. **实现CNN模型** → `src/models/cnn.py`
4. **实现FedAvg** → `src/federated/{client,server}.py`
5. **运行快速测试** → `scripts/quick_test.py`

---

## 注意事项

### 资源管理
- 当前服务器: 1台 RTX 4090
- 成本: ¥1.87/小时
- 已运行时间: ~0.5小时
- 剩余预算: ~47.5小时 (Day 1-2)

### 重要提醒
- 每小时保存checkpoint
- 定期同步代码到GitHub
- 监控GPU利用率 (应 > 90%)
- 记录所有实验超参数

### 联系信息
- GitHub: ReticG
- Email: 332982539@qq.com

---

**最后更新**: 2025-10-04 08:30 UTC
**更新人**: Claude (初始化)
**下次更新**: 实现完核心代码后
