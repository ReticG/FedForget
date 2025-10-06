# 补充实验脚本说明

## 📁 已创建脚本

### ✅ 1. compare_10clients.py
- **目的**: 对齐顶会标准 (ConDa, SIFU使用10 clients)
- **配置**: 10 clients, CIFAR-10, α=0.5
- **方法**: Retrain, Fine-tuning, FedForget
- **重复**: 3次 (种子: 42, 123, 456)
- **预计时间**: 12小时
- **输出**:
  - `results/compare_10clients.csv`
  - `results/compare_10clients_stats.csv`

### ✅ 2. compare_20clients.py
- **目的**: 验证可扩展性
- **配置**: 20 clients, CIFAR-10, α=0.5
- **方法**: Retrain, FedForget
- **重复**: 1次 (种子: 42)
- **预计时间**: 6小时
- **输出**: `results/compare_20clients.csv`

## 📋 待创建脚本

### 3. femnist_experiment.py
**目的**: 真实Non-IID验证

```python
# 关键配置
- 数据集: FEMNIST (62类手写字符)
- 客户端: 10个
- 特点: 真实设备数据分布
- 方法: Retrain, FedForget
- 预计时间: 8-10小时

# 数据下载
需要先下载FEMNIST数据集:
- 来源: LEAF benchmark
- 大小: ~1GB
- 位置: /home/featurize/data/femnist
```

### 4. multi_client_unlearning.py
**目的**: 多客户端遗忘验证

```python
# 实验设计
实验1: 2/5客户端遗忘 (Client 0 + Client 1)
实验2: 3/5客户端遗忘 (Client 0 + Client 1 + Client 2)
实验3: 顺序 vs 同时遗忘对比

# 关键修改
- FedForgetServer支持多个遗忘客户端
- 权重分配策略调整
- 预计时间: 6小时
```

### 5. federated_eraser_baseline.py
**目的**: 实现FedEraser基线对比

```python
# FedEraser算法要点
1. 存储所有历史参数更新
2. 基于影响函数计算遗忘效果
3. 选择性重训练部分轮次

# 实现复杂度: 高
- 需要存储机制
- 需要影响函数计算
- 预计时间: 2-3天实现 + 1天实验
```

### 6. hyperparameter_sensitivity.py
**目的**: 整理超参数敏感性分析

```python
# 使用已有参数搜索结果
- results/final_param_search.csv
- results/fedforget_optimization_cifar10.csv

# 生成分析
1. α sensitivity (retention vs forgetting trade-off)
2. λ_neg sensitivity (negative learning strength)
3. λ_forget sensitivity (weight amplification)

# 可视化
- 3个subplot图表
- 预计时间: 2小时
```

### 7. scalability_analysis.py
**目的**: 客户端规模对比

```python
# 整合结果
- 5 clients: results/cifar10_comparison.csv
- 10 clients: results/compare_10clients.csv
- 20 clients: results/compare_20clients.csv

# 分析维度
- 遗忘率 vs 客户端数
- 时间 vs 客户端数
- ASR vs 客户端数

# 可视化
- 可扩展性曲线图
- 预计时间: 1小时
```

## 🗓️ 建议执行顺序

### Phase 1: Week 1 (必需实验)
**Day 5-6**:
1. ✅ 等待消融实验完成
2. ✅ 等待Shadow MIA完成
3. ⏳ 运行 `reproducibility_test.py` (已有)
4. ⏳ 运行 `compare_10clients.py` (新建)

**Day 7**:
5. ⏳ 运行 `compare_20clients.py` (新建)
6. ⏳ 创建 `hyperparameter_sensitivity.py`
7. ⏳ 创建 `scalability_analysis.py`

**Day 8-9**:
- 分析所有结果
- 更新论文draft

**Day 10-11**:
- LaTeX排版
- 论文润色

**Week 1完成后论文就绪度**: 85%

---

### Phase 2: Week 2 (强烈建议)
**Day 12**:
1. 下载FEMNIST数据集
2. 创建 `femnist_experiment.py`

**Day 13**:
3. 运行FEMNIST实验

**Day 14**:
4. 创建 `multi_client_unlearning.py`
5. 运行多客户端遗忘实验

**Day 15-16**:
- 分析结果
- 更新论文

**Day 17-18**:
- 论文润色
- 内部审阅

**Week 2完成后论文就绪度**: 95%

---

### Phase 3: Week 3-4 (可选增强)
**Day 19-21**:
1. 实现FedEraser基线
2. 运行对比实验

**Day 22-23**:
- (可选) 更多数据集
- Tiny-ImageNet或CelebA

**Day 24-25**:
- 最终润色
- 准备投稿

**Week 3-4完成后论文就绪度**: 100%

---

## 🚀 立即执行

**今晚-明天**:
1. 等待当前实验完成
2. 开始10客户端实验

**命令**:
```bash
# 10客户端实验 (3次重复)
python scripts/compare_10clients.py

# 预计12小时，建议后台运行
nohup python scripts/compare_10clients.py > logs/compare_10clients.log 2>&1 &
```

## 📊 预期成果

完成所有实验后，论文将包含:

**表格** (9个):
- Table 1: 主要结果 (10 clients)
- Table 2: Non-IID鲁棒性 (5种α)
- Table 3: 客户端规模对比 (5/10/20)
- Table 4: CIFAR-100扩展性
- Table 5: SimpleMIA评估
- Table 6: Shadow MIA评估
- Table 7: 消融实验
- Table 8: 可复现性验证
- Table 9: FEMNIST真实Non-IID

**图表** (6-8个):
- Figure 1: Non-IID分析 (4 subplots)
- Figure 2: Non-IID热力图
- Figure 3: MIA评估 (6 subplots)
- Figure 4: 可扩展性曲线
- Figure 5: 超参数敏感性
- Figure 6: 多客户端遗忘
- Figure 7: FEMNIST结果
- Figure 8: 消融实验对比

**实验完整性**: 100%
**顶会竞争力**: 70-80% (NeurIPS/ICML)
**期刊接受率**: 95%+ (TIFS/TDSC)
