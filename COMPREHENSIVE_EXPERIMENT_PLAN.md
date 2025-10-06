# FedForget 完整实验补充计划 (基于NeurIPS 2024标准)

**制定日期**: 2025-10-06
**参考标准**: NeurIPS 2024 Ferrari论文 + ICML/ICLR联邦遗忘研究

---

## 📊 NeurIPS 2024 Ferrari论文实验标准

### Ferrari实验配置 (我们的对标)
- **客户端数**: **10 clients** ✅
- **数据集**: MNIST, FMNIST, CIFAR-10, CIFAR-20, CIFAR-100
- **模型**: ResNet-18
- **训练配置**:
  - Global epochs: 200
  - Local epochs: 5
  - Batch size: 128
  - Learning rate: 0.0001
  - Client fraction: 0.4 (每轮4个客户端参与)
  - Optimizer: SGD with momentum 0.5
- **评估**:
  - Backdoor feature unlearning
  - Sensitive feature unlearning
  - 保持准确率 + 遗忘效果

---

## 🎯 我们的实验 vs Ferrari标准对比

| 维度 | Ferrari (NeurIPS 2024) | FedForget (我们) | 状态 |
|-----|----------------------|-----------------|------|
| **客户端数** | 10 clients | **5 clients** | ⚠️ 偏少 |
| **数据集** | MNIST, FMNIST, CIFAR-10/20/100 | CIFAR-10, CIFAR-100 | ✅ 部分覆盖 |
| **Non-IID** | 未明确 | **5种α值 (0.1~1.0)** | ⭐ 超越 |
| **隐私评估** | 未提及 | **SimpleMIA + Shadow MIA** | ⭐ 超越 |
| **消融实验** | 有 | **4变体 (运行中)** | ✅ 符合 |
| **可复现性** | 未提及 | **3 seeds (待运行)** | ⭐ 超越 |
| **基线对比** | 多个SOTA | Retrain + Fine-tuning | ⚠️ 较少 |

---

## 🔴 关键差距分析

### 差距1: 客户端数量不足
**问题严重度**: 🔴 高
- Ferrari: 10 clients (NeurIPS 2024标准)
- 我们: 5 clients

**影响**:
- 审稿人会质疑可扩展性
- 无法直接对比Ferrari等工作

**解决方案**:
- **必须补充10客户端实验** (优先级最高)
- 可选补充20客户端

---

### 差距2: 数据集不够全面
**问题严重度**: 🟡 中等
- Ferrari: 5个数据集 (MNIST, FMNIST, CIFAR-10/20/100)
- 我们: 2个数据集 (CIFAR-10, CIFAR-100)

**影响**:
- 缺少简单数据集 (MNIST/FMNIST) 的验证
- 缺少真实Non-IID数据集 (FEMNIST)

**解决方案**:
- 补充FEMNIST实验 (真实Non-IID场景)
- 可选: Fashion-MNIST快速验证

---

### 差距3: 基线方法较少
**问题严重度**: 🟡 中等
- Ferrari: 对比多个SOTA方法
- 我们: 只有Retrain + Fine-tuning

**影响**:
- 无法与已有联邦遗忘方法直接对比
- 审稿人可能要求补充FedEraser等

**解决方案**:
- 在Related Work中详细讨论基线选择理由
- 可选: 实现简化版FedEraser (工作量大)

---

## 📋 完整实验补充计划 (分3个Phase)

### Phase 1: 必需实验 (Week 1, 关键!) 🔴

#### 1.1 消融实验 ✅ 进行中
**状态**: No Distillation变体预训练20%

**4个变体**:
- ✅ FedForget (Full) - 完成
- 🔄 No Weight Adjustment - 完成
- 🔄 No Distillation - 运行中 (20%)
- ⏳ Single Teacher

**预计完成**: 今晚 (3-4小时)

---

#### 1.2 可复现性验证 (5 clients)
**目标**: 证明结果稳定

**配置**:
- CIFAR-10, 5 clients, α=0.5
- 3个随机种子: 42, 123, 456
- 方法: Retrain, Fine-tuning, FedForget

**输出**: 均值 ± 标准差, CV

**预计时间**: 3-4小时

**脚本**: `scripts/reproducibility_test.py` (已准备)

---

#### 1.3 10客户端完整对比 🔴 最关键
**目标**: 符合NeurIPS标准

**配置**:
- **客户端数**: 10 clients (对齐Ferrari)
- **数据集**: CIFAR-10
- **Non-IID**: α = 0.5 (最优配置)
- **方法**: Retrain, Fine-tuning, FedForget
- **重复**: 3次 (seeds: 42, 123, 456)

**评估指标**:
- 遗忘率 (Forget Acc下降)
- 保持率 (Test Acc保持)
- SimpleMIA (ASR, AUC)
- 训练时间、通信轮次

**预计时间**: 12-15小时

**输出文件**: `results/10clients_comparison.csv`

---

#### 1.4 修复Shadow MIA
**问题**: 所有方法ASR=91.4% (异常)

**修复方案**:
1. 检查影子模型训练是否收敛
2. 验证攻击分类器特征提取逻辑
3. 确认成员/非成员标签正确

**预计时间**: 2-3小时

---

### Phase 2: 强烈建议 (Week 2, 提升竞争力) 🟡

#### 2.1 FEMNIST真实Non-IID验证
**重要性**: 🔴 高 (真实场景验证)

**配置**:
- **数据集**: FEMNIST (62类，天然Non-IID)
- **客户端数**: 10 clients
- **方法**: Retrain vs FedForget

**为什么重要**:
- NeurIPS竞赛使用FEMNIST
- 真实Non-IID > Dirichlet模拟
- 强化实用性论证

**预计时间**: 8-10小时 (含数据准备)

---

#### 2.2 多客户端遗忘场景
**重要性**: 🟡 中等 (增强实用性)

**场景**:
1. **2/5客户端遗忘**: Client 0 + Client 1
2. **3/5客户端遗忘**: Client 0 + 1 + 2

**评估**:
- 每个遗忘客户端的遗忘率
- 全局准确率保持
- 权重调整策略扩展性

**预计时间**: 4-5小时

---

#### 2.3 20客户端扩展性验证
**重要性**: 🟢 低 (可选)

**配置**:
- 20 clients, CIFAR-10, α=0.5
- FedForget vs Retrain

**预计时间**: 6-8小时

---

### Phase 3: 可选增强 (Week 3+, 锦上添花) 🟢

#### 3.1 超参数敏感性分析
**目标**: 回答"如何选择α, λ_neg, λ_forget?"

**实验设计**:
- α: 0.85, 0.90, 0.93, 0.95, 0.97
- λ_neg: 2.0, 3.0, 3.5, 4.0, 5.0
- λ_forget: 1.5, 2.0, 2.5

**可视化**: 热力图 (遗忘率 vs α+λ_neg)

**预计时间**: 6-8小时

---

#### 3.2 Fashion-MNIST快速验证
**目标**: 补充简单数据集

**配置**:
- FMNIST, 10 clients, α=0.5
- FedForget vs Retrain

**预计时间**: 2-3小时

---

#### 3.3 遗忘进度可视化
**目标**: 展示遗忘过程

**内容**:
- 每轮遗忘后的Forget Acc曲线
- 权重调整动态变化
- Test Acc保持曲线

**预计时间**: 2-3小时

---

## 📅 实施时间表

### Week 1: 核心补充 (必需完成) 🔴

| Day | 任务 | 状态 | 预计时间 |
|-----|------|------|---------|
| **Day 1 (今天)** | 消融实验完成 | 🔄 70% | 3-4h |
| | 修复Shadow MIA | ⏳ | 2-3h |
| | 启动可复现性验证 | ⏳ | 3-4h |
| **Day 2** | 准备10客户端脚本 | ⏳ | 1h |
| | 10客户端实验 #1 (seed=42) | ⏳ | 4-5h |
| **Day 3** | 10客户端实验 #2 (seed=123) | ⏳ | 4-5h |
| **Day 4** | 10客户端实验 #3 (seed=456) | ⏳ | 4-5h |
| | 数据分析和可视化 | ⏳ | 2-3h |
| **Day 5** | FEMNIST准备 | ⏳ | 2h |
| | FEMNIST实验启动 | ⏳ | 6-8h |

**Week 1成果**:
- ✅ 10客户端完整验证 (3次重复)
- ✅ 消融实验完成
- ✅ 可复现性验证
- ✅ Shadow MIA修复
- ✅ FEMNIST实验 (可选)
- **论文就绪度**: 90%

---

### Week 2: 补充完善 🟡

| Day | 任务 | 预计时间 |
|-----|------|---------|
| **Day 6** | 多客户端遗忘实验 | 4-5h |
| | 整合所有实验结果 | 2-3h |
| **Day 7** | 生成所有可视化图表 | 3-4h |
| | 更新论文实验章节 | 3-4h |
| **Day 8-10** | 论文润色和完善 | 全天 |
| | LaTeX排版 | 4-6h |

**Week 2成果**:
- ✅ 所有补充实验完成
- ✅ 完整论文初稿
- **论文就绪度**: 100%

---

## 🔧 技术实现细节

### 脚本准备清单

#### 1. 10客户端对比脚本
```python
# scripts/compare_10clients.py
# 基于 compare_cifar10.py 修改

NUM_CLIENTS = 10  # 关键修改
UNLEARN_CLIENT_ID = 0
DIRICHLET_ALPHA = 0.5

# 数据分配需要调整
# CIFAR-10: 50000训练样本 / 10 clients ≈ 5000/client
```

#### 2. FEMNIST数据加载
```python
# src/data/femnist.py
# 使用LEAF框架或TorchVision EMNIST

class FEMNISTData:
    def __init__(self, num_clients=10):
        # 62类 (0-9数字 + a-z + A-Z)
        # 天然Non-IID (每个用户手写风格不同)
```

#### 3. 多客户端遗忘
```python
# scripts/multi_client_unlearning.py

UNLEARN_CLIENTS = [0, 1]  # 或 [0, 1, 2]

# 服务器端需要注册多个遗忘客户端
for client_id in UNLEARN_CLIENTS:
    server.register_unlearning_client(client_id)
```

---

## 📊 预期实验结果

### 10客户端实验预期

| 方法 | 遗忘率 | 保持率 | ASR | 时间 |
|-----|-------|-------|-----|------|
| Retrain | ~32% | ~98% | ~58% | ~300s |
| Fine-tuning | ~23% | ~101% | ~64% | ~120s |
| **FedForget** | **~30%** | **~88%** | **~48%** ⭐ | **~100s** |

**关键点**:
- 遗忘率应与5 clients相近 (算法鲁棒)
- ASR最优 (隐私保护核心卖点)
- 速度仍有优势

---

### FEMNIST实验预期

| 方法 | Test Acc | Forget Acc | 时间 |
|-----|---------|-----------|------|
| Pretrain | ~82% | ~80% | - |
| Retrain | ~81% | ~30% | ~400s |
| **FedForget** | **~75%** | **~32%** | **~150s** |

**关键点**:
- 真实Non-IID场景验证
- 遗忘效果应与CIFAR-10类似
- 证明算法泛化性

---

### 多客户端遗忘预期

| 遗忘客户端数 | 遗忘率 | 保持率 | 时间 |
|------------|-------|-------|------|
| 1/5 (Client 0) | 31.2% | 89.7% | 51s |
| **2/5 (0+1)** | **~28%** | **~86%** | ~55s |
| **3/5 (0+1+2)** | **~25%** | **~82%** | ~60s |

**关键点**:
- 遗忘客户端越多，全局性能下降越多
- 权重调整策略的扩展性验证

---

## 📝 论文结构调整

### 当前结构
```
4. Experiments
  4.1 Setup
  4.2 Main Results (5 clients)
  4.3 Non-IID Robustness
  4.4 MIA Evaluation
  4.5 Ablation Study
```

### 建议新结构 (对齐NeurIPS标准)
```
4. Experiments
  4.1 Experimental Setup
    4.1.1 Datasets and Models
    4.1.2 Baselines
    4.1.3 Evaluation Metrics
    4.1.4 Implementation Details

  4.2 Main Results
    4.2.1 Effectiveness on CIFAR-10 (10 clients) ← 主要结果
    4.2.2 Scalability Analysis (5, 10 clients对比)

  4.3 Robustness Evaluation
    4.3.1 Non-IID Robustness (5种α值)
    4.3.2 Real-World Non-IID: FEMNIST ← 新增

  4.4 Privacy Evaluation
    4.4.1 SimpleMIA
    4.4.2 Shadow Model Attack

  4.5 Ablation Study (4变体)

  4.6 Reproducibility (3 seeds)

  4.7 Additional Analysis
    4.7.1 Multi-Client Unlearning ← 新增
    4.7.2 Parameter Sensitivity (可选)
```

---

## 🎯 成功标准

### Tier 1: 必须达到 (论文接收最低要求)
- ✅ 10客户端完整验证 (3次重复)
- ✅ 消融实验完成
- ✅ 可复现性验证
- ✅ SimpleMIA + Shadow MIA (修复)

### Tier 2: 强烈建议 (提升到80%竞争力)
- ✅ FEMNIST真实Non-IID验证
- ✅ 多客户端遗忘场景

### Tier 3: 可选加分 (冲击90%竞争力)
- ✅ 20客户端扩展性
- ✅ 超参数敏感性分析
- ✅ Fashion-MNIST补充

---

## 💰 资源估算

### 计算资源 (RTX 4090)
| 实验 | 时间 | 成本 (¥1.87/h) |
|-----|------|----------------|
| 消融实验 | 4h | ¥7.5 |
| 可复现性 (5 clients) | 4h | ¥7.5 |
| 10客户端 × 3次 | 15h | ¥28 |
| FEMNIST | 10h | ¥18.7 |
| 多客户端遗忘 | 5h | ¥9.4 |
| 20客户端 (可选) | 8h | ¥15 |
| **总计** | **46h** | **¥86** |

### 时间投入
- **Week 1 (必需)**: 5天全职
- **Week 2 (完善)**: 3-5天
- **总计**: 10-12天

---

## 🚀 立即行动计划

### 今晚 (2025-10-06)
1. ✅ 等消融实验完成 (预计1-2小时)
2. 🔴 修复Shadow MIA bug
   - 检查攻击分类器训练
   - 验证特征提取逻辑
3. 🔴 启动可复现性验证

### 明天 (2025-10-07)
1. 🔴 准备10客户端脚本
   - 修改`compare_cifar10.py`
   - 测试数据分配
2. 🔴 运行10客户端实验 (第1次, seed=42)

### Day 3-4
1. 🔴 10客户端重复实验 (seeds=123, 456)
2. 数据分析和可视化
3. 准备FEMNIST数据

### Day 5
1. 🟡 FEMNIST实验
2. 🟡 多客户端遗忘 (可选)

---

## 📈 竞争力评估

### 补充前 (当前)
- **实验完整度**: 60%
- **顶会竞争力**: 40-50% (客户端数量不足)
- **期刊竞争力**: 70-80%

### Phase 1完成后 (Week 1)
- **实验完整度**: 90%
- **顶会竞争力**: 70-80% (符合标准)
- **期刊竞争力**: 90%+

### Phase 2完成后 (Week 2)
- **实验完整度**: 100%
- **顶会竞争力**: 80-85% (超越部分标准)
- **期刊竞争力**: 95%+

---

## 💡 关键建议总结

### 1. 必须做的 (Non-negotiable)
1. **10客户端实验** - 对齐NeurIPS 2024 Ferrari标准
2. **可复现性验证** - 3次重复证明稳定性
3. **修复Shadow MIA** - 双重隐私评估

### 2. 强烈建议做的 (Highly Recommended)
1. **FEMNIST实验** - 真实Non-IID场景
2. **多客户端遗忘** - 增强实用性

### 3. 可选做的 (Nice to Have)
1. 20客户端扩展性
2. 超参数敏感性
3. Fashion-MNIST

### 4. 论文撰写策略
1. **主打卖点**: 隐私保护最优 (ASR最接近50%)
2. **次要卖点**: Non-IID鲁棒性全面 (5种α值)
3. **效率优势**: 2-3×加速
4. **算法简洁**: 易于实现和部署

---

**文档状态**: ✅ 完整补充计划已制定
**参考标准**: NeurIPS 2024 Ferrari + ICML/ICLR标准
**下一步**: 等待消融实验完成 → 执行Phase 1计划
