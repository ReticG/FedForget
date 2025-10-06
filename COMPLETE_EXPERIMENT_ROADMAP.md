# FedForget 完整实验路线图 (基于NeurIPS 2024标准)

**制定时间**: 2025-10-06 09:00
**目标**: NeurIPS/ICML 2025投稿就绪
**基准**: NeurIPS 2024 Ferrari论文标准

---

## 🎯 核心策略: 对齐顶会标准

### NeurIPS 2024 Ferrari关键配置
- ✅ **10 clients** (vs 我们目前5 clients)
- ✅ **消融实验** (验证每个组件贡献)
- ✅ **可复现性** (多随机种子)
- ✅ **真实Non-IID** (FEMNIST)

### 我们的优势
- ⭐ **隐私评估更全面**: SimpleMIA + Shadow MIA
- ⭐ **Non-IID鲁棒性**: 5种α值系统性验证
- ⭐ **双教师知识蒸馏**: 创新点明确

---

## 📊 Week 1: 必需实验 (P0 - 论文接收的必要条件)

### Day 5 (今天 2025-10-06) ✅ 进行中

#### ✅ 上午: 等待两个实验完成
- [90%] **消融实验** - No Distillation变体预训练中
  - 预计完成: 10:00
  - 结果文件: `results/ablation_study.csv`

- [Retrain] **可复现性验证** - Seed 42运行中
  - 预计完成: 11:30
  - 结果文件: `results/reproducibility_5clients.csv`

#### ⏳ 下午: 数据分析 (13:00-18:00)
1. **分析消融实验结果** (1小时)
   - 权重调整的贡献度
   - 知识蒸馏的贡献度
   - 双教师vs单教师对比
   - 生成表格和图表

2. **分析可复现性结果** (1小时)
   - 计算mean ± std
   - 计算变异系数 (CV)
   - 验证结果稳定性

3. **准备10客户端实验** (1小时)
   - 验证脚本配置 ✅
   - 准备运行命令
   - 估算资源需求

#### ⏳ 晚上: 启动10客户端实验第1次 (19:00-24:00)
- **配置**: 10 clients, CIFAR-10, α=0.5, seed=42
- **方法**: Retrain, Fine-tuning, FedForget
- **预计时间**: 4-5小时
- **脚本**: `scripts/compare_10clients.py`

---

### Day 6 (明天 2025-10-07) 🔴 关键日

#### 上午: 分析10客户端第1次结果 (9:00-12:00)
1. 检查结果完整性
2. 对比5 clients vs 10 clients
3. 验证可扩展性

#### 下午: 10客户端实验第2次 (13:00-18:00)
- **Seed**: 123
- **预计时间**: 4-5小时

#### 晚上: 10客户端实验第3次 (19:00-24:00)
- **Seed**: 456
- **预计时间**: 4-5小时

---

### Day 7 (2025-10-08)

#### 上午: 综合分析10客户端结果 (9:00-12:00)
1. 计算3次重复的mean ± std
2. 生成对比图表
3. 更新论文实验章节

#### 下午: Shadow MIA修复并重跑 (13:00-18:00)
1. 诊断ASR=91.4%异常原因
2. 修复攻击分类器
3. 重新运行Shadow MIA实验
4. 预计时间: 2-3小时

#### 晚上: 准备FEMNIST实验 (19:00-22:00)
1. 下载FEMNIST数据集
2. 实现数据加载器
3. 测试10 clients数据分配

---

## 📊 Week 2: 强烈建议实验 (P1 - 提升竞争力)

### Day 8-9 (2025-10-09~10): FEMNIST实验

#### Day 8: FEMNIST实验 (3次重复)
- **配置**: 10 clients, FEMNIST, seeds: 42/123/456
- **方法**: Retrain vs FedForget (简化对比)
- **预计时间**: 8-10小时

#### Day 9: FEMNIST结果分析
- 真实Non-IID vs 模拟Non-IID对比
- 更新论文实验章节

---

### Day 10-11 (2025-10-11~12): 数据整合与可视化

#### 核心图表制作
1. **Figure 1**: 主要结果对比 (10 clients)
   - Forget Rate vs Test Acc
   - 3个方法: Retrain, Fine-tuning, FedForget

2. **Figure 2**: 消融实验结果
   - 4个变体性能对比
   - 展示每个组件的贡献

3. **Figure 3**: Non-IID鲁棒性
   - 5种α值下的性能曲线
   - FedForget vs Baselines

4. **Figure 4**: 隐私评估
   - SimpleMIA + Shadow MIA结果
   - ASR对比

5. **Figure 5**: 可复现性
   - Error bars展示标准差
   - 3次重复的稳定性

6. **Figure 6**: FEMNIST真实场景
   - 真实Non-IID vs 模拟Non-IID

---

### Day 12-14 (2025-10-13~15): 论文完善

#### Day 12: 实验章节完整更新
- 所有表格和图表插入
- 实验设置详细描述
- 结果分析和讨论

#### Day 13: 相关工作和讨论章节
- 补充最新相关工作
- 深化讨论部分
- 强化创新点论述

#### Day 14: 全文润色
- 语言润色
- 逻辑检查
- 格式调整

---

## 📈 实验优先级矩阵

| 实验 | 重要性 | 紧急性 | 时间 | 优先级 |
|------|--------|--------|------|--------|
| **10客户端对比** | 🔴 极高 | 🔴 极高 | 12-15h | **P0** |
| **消融实验** | 🔴 极高 | 🟢 进行中 | 4h | **P0** |
| **可复现性验证** | 🔴 高 | 🟢 进行中 | 3h | **P0** |
| **Shadow MIA修复** | 🟡 中 | 🟡 中 | 2-3h | **P1** |
| **FEMNIST验证** | 🟡 中 | 🟡 中 | 8-10h | **P1** |
| **20客户端扩展** | 🟢 低 | 🟢 低 | 15h | **P2** |

---

## 🎯 关键里程碑

### Week 1结束 (2025-10-12)
- ✅ 消融实验完成
- ✅ 可复现性验证完成 (5 clients)
- ✅ **10客户端对比完成** (3次重复)
- ✅ Shadow MIA修复完成
- ✅ 核心实验100%完成

### Week 2结束 (2025-10-19)
- ✅ FEMNIST实验完成
- ✅ 所有图表制作完成
- ✅ 论文实验章节完成
- ✅ 论文初稿完成

### Week 3 (2025-10-20~26): 投稿准备
- ✅ 全文润色
- ✅ 内部审阅
- ✅ 投稿材料准备
- 🚀 **目标投稿**: NeurIPS 2025 / ICML 2025

---

## 📊 预期实验结果汇总

### 核心贡献验证
1. **遗忘效果**: Forget Acc ↓ 31.2% (CIFAR-10, 10 clients)
2. **保持性能**: Test Acc保持 > 95%
3. **隐私保护**: ASR ≈ 50% (理想隐私)
4. **效率提升**: 2-3× speedup vs Retrain

### 关键对比
| 方法 | Forget Acc↓ | Test Acc | ASR | Time (相对) |
|------|-------------|----------|-----|-------------|
| Retrain | 最低 | 基线 | ~50% | 1.0× |
| Fine-tuning | 中等 | 略降 | 高 | 0.5× |
| **FedForget** | **31.2%** | **保持** | **48.4%** | **0.4-0.5×** |

---

## 💾 实验结果文件清单

### Phase 1 (Week 1)
- ✅ `results/ablation_study.csv` - 消融实验
- ✅ `results/reproducibility_5clients.csv` - 可复现性 (5 clients)
- 🔄 `results/10clients_comparison_seed42.csv` - 10客户端 seed 42
- ⏳ `results/10clients_comparison_seed123.csv` - 10客户端 seed 123
- ⏳ `results/10clients_comparison_seed456.csv` - 10客户端 seed 456
- ⏳ `results/shadow_mia_fixed.csv` - Shadow MIA修复后

### Phase 2 (Week 2)
- ⏳ `results/femnist_10clients_seed42.csv`
- ⏳ `results/femnist_10clients_seed123.csv`
- ⏳ `results/femnist_10clients_seed456.csv`

---

## 🚀 执行策略

### 资源使用
- **单服务器策略**: 已验证足够 (成本<¥200)
- **并行策略**: 每次只运行1个大实验
- **监控**: 使用`monitor_experiments.sh`实时监控

### 风险控制
1. **每个实验完成后立即备份结果**
2. **关键实验运行前先小规模测试**
3. **保持文档实时更新**

### 质量保证
1. **每个实验完成后立即分析**
2. **异常结果立即诊断**
3. **代码版本控制 (Git commit)**

---

## 📝 论文章节对应

### 实验设置 (Section 4.1)
- 数据集: CIFAR-10, CIFAR-100, FEMNIST
- 配置: 10 clients, Non-IID (α=0.5)
- 基线: Retrain, Fine-tuning

### 主要结果 (Section 4.2)
- 10客户端对比实验
- 遗忘效果 + 保持性能 + 隐私

### 消融实验 (Section 4.3)
- 权重调整贡献
- 知识蒸馏贡献
- 双教师vs单教师

### 鲁棒性验证 (Section 4.4)
- Non-IID鲁棒性 (5种α)
- 真实Non-IID (FEMNIST)
- 可复现性 (3 seeds)

### 效率分析 (Section 4.5)
- 训练时间对比
- 通信轮次对比

---

## ✅ 成功标准

### 论文接收的必要条件
- ✅ 10客户端实验完成 (对齐NeurIPS标准)
- ✅ 消融实验完整 (4个变体)
- ✅ 可复现性验证 (3 seeds, std < 5%)
- ✅ 隐私评估完整 (SimpleMIA + Shadow MIA)

### 加分项
- ⭐ FEMNIST真实场景验证
- ⭐ 20客户端可扩展性
- ⭐ 多客户端同时遗忘

---

**状态**: 📍 Day 5, Week 1
**进度**: 60% → 目标100% (Week 1结束)
**信心**: 🟢 高 (路线清晰,资源充足)

**最后更新**: 2025-10-06 09:00
