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
│   ├── data/                      ← 数据加载
│   ├── models/                    ← 模型定义
│   ├── federated/                 ← 联邦学习框架
│   ├── unlearning/                ← 遗忘算法
│   └── utils/                     ← 工具函数
├── scripts/                       ← 实验脚本
├── results/                       ← 重要实验结果（持久保存）
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

## 当前状态 (2025-10-04 Day 2)

### ✅ 已完成（Day 1-2）

#### 1. 核心框架实现
- ✓ **数据加载器** (src/data/datasets.py)
  - IID和Non-IID (Dirichlet)数据分割
  - 支持MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100

- ✓ **模型定义** (src/models/cnn.py)
  - ConvNet: 2 conv layers + 1 FC layer
  - LeNet5: Classic CNN

- ✓ **联邦学习框架** (src/federated/)
  - Client: 标准本地训练
  - UnlearningClient: 双教师知识蒸馏 + 梯度上升
  - Server: FedAvg聚合
  - FedForgetServer: 动态权重调整

- ✓ **基线方法** (src/unlearning/baselines.py)
  - RetrainBaseline: 从头重新训练（理想基线）
  - FineTuningBaseline: 在剩余数据上继续训练

- ✓ **评估工具** (src/utils/metrics.py)
  - evaluate_model: 整体准确率
  - compute_class_accuracy: 各类别准确率
  - compute_forgetting_score: 遗忘效果评分

#### 2. 测试脚本 (scripts/)
- ✓ quick_test.py - 初始测试（发现模型崩溃问题）
- ✓ param_search.py - 网格搜索参数
- ✓ test_corrected_fedforget.py - 修正教师A实现
- ✓ test_aggressive.py - 激进参数测试
- ✓ test_high_weight.py - 高权重策略测试
- ✓ compare_all_methods.py - IID设置下的完整对比
- ✓ compare_noniid.py - Non-IID设置测试（发现Retrain崩溃）
- ✓ compare_noniid_balanced.py - 平衡Non-IID设置（alpha=0.5）

---

## 🔬 实验发现

### Day 2关键发现

#### 发现1: IID设置无法评估遗忘效果 ⚠️
**实验**: compare_all_methods.py (IID, alpha=均匀分布)

**结果**:
- 预训练: Test 99.32%, Forget 99.74%
- **Retrain (理想基线)**: Test 99.16%, Forget **99.15%**
- Fine-tuning: Test 99.38%, Forget 99.81%
- FedForget (保守): Test 99.34%, Forget 99.55%
- FedForget (中等/激进): **模型崩溃** (9.80%)

**结论**:
> **即使是理想的Retrain基线,遗忘数据准确率也只从99.74%降到99.15% (下降0.59%)**
>
> 这说明IID数据分布下,客户端之间数据高度重合,即使完全排除客户端0重新训练,
> 模型仍能从其他客户端学到客户端0的知识。**这个设置无法评估遗忘效果!**

#### 发现2: Non-IID极端设置导致Retrain崩溃 ❌
**实验**: compare_noniid.py (Non-IID, alpha=0.1)

**结果**:
- 预训练: Test 98.60%, Forget 99.41%
- **Retrain: Test 10.09%, Forget 0.00%** ← 完全崩溃
- Fine-tuning: Test 98.81%, Forget 98.71%
- FedForget: Test 97.94%, Forget 98.43%

**原因**:
- Dirichlet alpha=0.1太小,导致数据分布极度不平衡
- 客户端0在类别1、4、9完全没有数据
- 排除客户端0后,某些类别数据严重不足,导致Retrain无法收敛

#### 发现3: 平衡Non-IID设置有效 ✅
**实验**: compare_noniid_balanced.py (Non-IID, alpha=0.5)

**结果**:
```
预训练基线:
  测试准确率: 99.07%
  遗忘数据准确率: 99.75%

方法              测试准确率   遗忘准确率   保持率   遗忘率
Retrain           98.74%      98.18%      99.7%    1.6%
Fine-tuning       99.30%      99.40%     100.2%    0.4%
FedForget         98.92%      99.12%      99.8%    0.6%
```

**各类别遗忘效果** (客户端0数据):
```
类别  预训练    Retrain   Fine-tune  FedForget
0    100.00%   99.86%    100.00%    100.00%
1    100.00%  100.00%    100.00%    100.00%
5     99.75%   96.98%     99.17%     99.10%  ← 明显下降
9     99.20%   96.25%     98.93%     96.92%  ← 明显下降
```

**结论**:
> ✅ **Retrain基线正常工作**: Test保持99.7%, Forget下降1.6%
>
> ✅ **FedForget效果接近Fine-tuning**: 保持99.8%, 遗忘0.6%
>
> ⚠️ **遗忘效果仍然不足**: 所有方法的遗忘率都<2%,远未达到目标(<60%准确率)

---

## 🎯 核心技术挑战

### 挑战1: FedForget参数极难平衡 ⚖️

**参数空间探索**:
- alpha (正向vs负向学习权衡):
  - alpha < 0.5 → **模型崩溃** (9.8% test acc)
  - alpha > 0.9 → **遗忘不足** (99%+ forget acc)
  - 甜蜜点: 0.7-0.9 之间（尚未找到）

- lambda_neg (负向遗忘强度):
  - lambda_neg < 1.0 → 遗忘不足
  - lambda_neg > 5.0 → 容易崩溃（结合低alpha）

- lambda_forget (服务器端权重调整):
  - lambda_forget = 1.5 → 遗忘客户端权重~42%
  - lambda_forget = 10.0 → **仍导致崩溃**

**核心矛盾**:
```
需要强遗忘 → 增大lambda_neg或降低alpha
    ↓
模型崩溃  ← 负向学习过强破坏模型
```

### 挑战2: 双教师知识蒸馏实现细节 🎓

**当前实现** (src/federated/client.py:199-311):
```python
def unlearning_train(epochs, method='dual_teacher', alpha=0.5, lambda_neg=1.0):
    # 教师A: 旧全局模型 (固定,在prepare_unlearning时设置)
    # 教师B: 本地历史模型 (可选)

    if method == 'dual_teacher':
        # 正向蒸馏: 学习教师A (全局模型)
        loss_positive = KL(student || teacher_A)

        # 负向遗忘:
        if teacher_B is not None:
            # 有教师B: 远离教师B
            loss_negative = KL(student || teacher_B)
        else:
            # 无教师B: 梯度上升
            loss_negative = CrossEntropy(student, labels)

        loss = alpha * loss_positive - (1-alpha) * lambda_neg * loss_negative
```

**关键修正** (Day 1用户反馈):
> "教师A是旧的全局模型" - **在整个遗忘过程中固定不变**
>
> 之前的错误实现: 每轮更新教师A为当前全局模型 ❌
> 正确实现: 只在遗忘开始时设置教师A,之后固定 ✅

### 挑战3: 数据分布对遗忘效果的影响 📊

**IID vs Non-IID**:

| 数据分布 | Retrain遗忘效果 | FedForget可行性 | 适用场景 |
|---------|----------------|-----------------|---------|
| IID     | 几乎无效 (0.6%) | 无意义          | ❌ 不适合遗忘评估 |
| Non-IID (α=0.1) | 完美但崩溃 (100%) | Retrain失败 | ❌ 过于极端 |
| Non-IID (α=0.5) | 有效 (1.6%) | 可评估 | ✅ **推荐使用** |

**推荐设置**:
```python
fed_data = load_federated_data(
    dataset_name='mnist',
    num_clients=5,
    data_dist='noniid',  # 必须Non-IID
    dirichlet_alpha=0.5,  # 平衡的不平衡
    data_root='/home/featurize/data'
)
```

---

## 📝 待解决问题

### 高优先级 🔴

#### 问题1: 遗忘效果普遍不足
**现象**: 所有方法（包括Retrain）遗忘率都<2%

**可能原因**:
1. MNIST太简单,泛化性太强
2. Non-IID alpha=0.5仍然不够不平衡
3. 客户端数量太少(5个),数据仍有重合
4. 需要更难的数据集(CIFAR-10)

**下一步尝试**:
- [ ] 增加客户端数量到10个
- [ ] 降低dirichlet_alpha到0.3
- [ ] 测试CIFAR-10数据集
- [ ] 实现类别特定遗忘(class forgetting)

#### 问题2: FedForget参数搜索空间过大
**现象**: 手动调参效率低,容易崩溃

**需要**:
- [ ] 实现自动超参数搜索 (Optuna)
- [ ] 添加早停机制(检测崩溃)
- [ ] 记录所有参数组合的结果

#### 问题3: 缺少MIA评估
**现象**: 只用准确率评估遗忘,不够全面

**需要**:
- [ ] 实现成员推断攻击(MIA)
- [ ] 计算ASR (Attack Success Rate)
- [ ] 实现隐私指标评估

### 中优先级 🟡

- [ ] 实现更多遗忘方法对比 (SCRUB, FedEraser)
- [ ] 添加实验结果可视化
- [ ] 优化训练速度(当前单个实验~5分钟)
- [ ] 实现checkpoint保存和恢复

---

## 🚀 下一步计划

### 立即执行（Day 2晚上）

1. **测试CIFAR-10数据集** (可能更难遗忘)
   ```python
   fed_data = load_federated_data(
       dataset_name='cifar10',
       num_clients=10,
       data_dist='noniid',
       dirichlet_alpha=0.3
   )
   ```

2. **系统化参数搜索**
   - 创建脚本: scripts/systematic_search.py
   - 搜索空间:
     - alpha: [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.92, 0.95]
     - lambda_neg: [1.0, 2.0, 3.0, 5.0]
     - lambda_forget: [1.0, 1.5, 2.0]
   - 早停: 检测test_acc < 50%则跳过
   - 记录所有结果到CSV

3. **提交Day 2工作到Git**
   ```bash
   git add .
   git commit -m "Day 2: 基线方法实现,IID vs Non-IID对比实验"
   git push
   ```

### Day 3计划

1. 分析Day 2参数搜索结果
2. 实现MIA评估
3. 测试CIFAR-10数据集
4. 如果参数仍未找到,考虑算法改进:
   - 尝试纯梯度上升(不用双教师)
   - 实现分层遗忘(layer-wise unlearning)
   - 参考SCRUB方法

---

## 📊 实验结果汇总

### IID设置 (compare_all_methods.py)

| 方法 | 测试准确率 | 遗忘准确率 | 保持率 | 遗忘率 | 耗时 |
|-----|----------|----------|-------|-------|-----|
| No Unlearning | 99.32% | 99.74% | 100.0% | 0.0% | 0.0s |
| Retrain | 99.16% | 99.15% | 99.8% | 0.6% | 60.2s |
| Fine-tuning | 99.38% | 99.81% | 100.1% | -0.1% | 29.4s |
| FedForget (α=0.95) | 99.34% | 99.55% | 100.0% | 0.2% | 46.5s |
| FedForget (α=0.90) | **9.80%** | 9.79% | 9.9% | 90.2% | 45.3s |

**结论**: IID设置无法有效评估遗忘

### Non-IID平衡设置 (compare_noniid_balanced.py, α=0.5)

| 方法 | 测试准确率 | 遗忘准确率 | 保持率 | 遗忘率 |
|-----|----------|----------|-------|-------|
| 预训练 | 99.07% | 99.75% | - | - |
| Retrain | 98.74% | 98.18% | 99.7% | 1.6% |
| Fine-tuning | 99.30% | 99.40% | 100.2% | 0.4% |
| FedForget | 98.92% | 99.12% | 99.8% | 0.6% |

**结论**:
- ✅ Retrain正常工作
- ⚠️ 遗忘效果仍然不足(<2%)
- ✅ FedForget性能介于Retrain和Fine-tuning之间

---

## 关键参数配置

### 当前最佳配置

**数据设置**:
```python
dataset_name = 'mnist'
num_clients = 5
data_dist = 'noniid'
dirichlet_alpha = 0.5  # 平衡的Non-IID
```

**预训练**:
```python
pretrain_rounds = 10
local_epochs = 2
learning_rate = 0.05
batch_size = 64
```

**FedForget**:
```python
# 遗忘客户端
unlearn_lr = 0.01
unlearn_epochs = 2
alpha = 0.95  # 正向学习权重
lambda_pos = 1.0
lambda_neg = 3.0  # 负向遗忘强度
distill_temp = 2.0

# 服务器聚合
lambda_forget = 1.5  # 遗忘客户端权重提升
unlearn_rounds = 10
```

### 文件路径
```python
# 数据
DATA_ROOT = '/home/featurize/data'

# 代码
PROJECT_ROOT = '/home/featurize/work/GJC/fedforget'

# 输出（快速磁盘）
CHECKPOINT_DIR = '/home/featurize/checkpoints'
LOG_DIR = '/home/featurize/logs'

# 重要结果（持久保存）
RESULTS_DIR = f'{PROJECT_ROOT}/results'
```

---

## Git提交历史

1. `da7f379` - Initial commit: FedForget project documentation
2. (Day 1) - 核心框架实现 + 初步测试
3. (Day 2) - 基线方法 + IID vs Non-IID对比实验

---

**最后更新**: 2025-10-04 Day 2
**更新人**: Claude
**工作目录**: /home/featurize/work/GJC/fedforget

**Day 2总结**:
- ✅ 实现了完整的基线方法(Retrain, Fine-tuning)
- ✅ 发现IID设置无法评估遗忘效果
- ✅ 确定平衡Non-IID设置(alpha=0.5)有效
- ⚠️ FedForget参数平衡仍是核心挑战
- ⚠️ 遗忘效果普遍不足,需要更难的设置
- 🎯 下一步: 系统化参数搜索 + CIFAR-10测试
