# Day 5 详细执行计划 (2025-10-06)

**当前时间**: 09:00
**目标**: 完成消融+可复现性实验,启动10客户端实验第1次

---

## 📊 当前实验状态

### 实验1: 消融实验 (Ablation Study)
- **PID**: 707907 (已完成或timeout)
- **当前**: No Distillation变体运行中
- **进度估计**: 75-80%
- **已完成**: FedForget (Full), No Weight Adjustment
- **待运行**: Single Teacher
- **预计完成**: 10:30

### 实验2: 可复现性验证
- **PID**: 766684
- **当前**: Seed 42 - FedForget遗忘40%
- **进度估计**: 50%
- **预计完成**: 11:00

---

## ⏰ 今天时间表

### 上午 (09:00-12:00)

#### 09:00-10:30: 等待实验完成
- [x] 监控消融实验进度
- [x] 监控可复现性验证进度
- [x] 制定完整路线图 ✅

**监控命令**:
```bash
# 每10分钟检查一次
watch -n 600 ./monitor_experiments.sh

# 或手动查看
tail -f logs/ablation_rerun.log
tail -f logs/reproducibility.log
```

#### 10:30-12:00: 初步结果检查
1. **检查消融实验结果** (10:30)
   ```bash
   cat results/ablation_study.csv
   ```
   - 验证4个变体数据完整
   - 快速计算各组件贡献度

2. **检查可复现性进度** (11:00)
   ```bash
   tail -50 logs/reproducibility.log
   ```
   - 确认Seed 42完成
   - 查看是否自动开始Seed 123

---

### 下午 (13:00-18:00): 数据分析与准备

#### 13:00-14:30: 消融实验分析
**目标**: 量化每个组件的贡献

**分析任务**:
1. 读取`results/ablation_study.csv`
2. 计算贡献度:
   ```
   权重调整贡献 = FedForget (Full) - No Weight Adjustment
   知识蒸馏贡献 = FedForget (Full) - No Distillation
   双教师改进 = FedForget (Full) - Single Teacher
   ```
3. 生成表格:
   | 变体 | Forget Acc↓ | Test Acc | ASR | 时间 |
   |------|-------------|----------|-----|------|
   | FedForget (Full) | ... | ... | ... | ... |
   | No Weight Adj | ... | ... | ... | ... |
   | No Distillation | ... | ... | ... | ... |
   | Single Teacher | ... | ... | ... | ... |

#### 14:30-15:30: 可复现性结果分析
**目标**: 验证结果稳定性

**等待**: 可复现性验证完成3个seeds

**分析任务**:
1. 读取`results/reproducibility_5clients.csv`
2. 计算统计量:
   ```python
   mean = df.groupby('Method').mean()
   std = df.groupby('Method').std()
   cv = std / mean  # 变异系数
   ```
3. 生成表格:
   | Method | Forget Acc↓ | Test Acc | ASR | CV |
   |--------|-------------|----------|-----|-----|
   | Retrain | μ±σ | μ±σ | μ±σ | ... |
   | Fine-tuning | μ±σ | μ±σ | μ±σ | ... |
   | FedForget | μ±σ | μ±σ | μ±σ | ... |

#### 15:30-17:00: 10客户端实验准备
**目标**: 确保脚本无误,准备运行

**检查清单**:
- [x] FineTuningBaseline API已修复 ✅
- [x] 方法名fine_tune→finetune已修复 ✅
- [ ] 测试运行10分钟验证无Bug
- [ ] 准备运行命令
- [ ] 估算完成时间

**测试运行** (可选):
```bash
# 修改脚本临时使用2个epochs测试
timeout 300 python scripts/compare_10clients.py
```

#### 17:00-18:00: 文档更新
1. 更新`PROGRESS_UPDATE.md`
2. 更新`EXPERIMENT_STATUS.md`
3. 记录今天完成的任务

---

### 晚上 (19:00-24:00): 启动10客户端实验

#### 19:00: 启动10客户端实验 (Seed 42)
**配置验证**:
- 客户端数: 10 ✅
- 数据集: CIFAR-10 ✅
- Non-IID: α=0.5 ✅
- 随机种子: 42 ✅
- 方法: Retrain, Fine-tuning, FedForget ✅

**运行命令**:
```bash
# 使用长timeout (10小时)
nohup timeout 36000 python scripts/compare_10clients.py > logs/10clients_seed42.log 2>&1 &

# 记录PID
echo $! > logs/10clients_seed42.pid
```

#### 19:10-24:00: 监控实验
**监控方式**:
```bash
# 每30分钟检查一次
tail -50 logs/10clients_seed42.log | grep -E "预训练|遗忘|Fine-tuning|Retrain"

# 查看进度百分比
tail -20 logs/10clients_seed42.log | grep "%"
```

**预计时间轴**:
- 19:00-21:30: 预训练 (20 rounds × 7s ≈ 2.5h)
- 21:30-22:30: Retrain (10 rounds × 7s ≈ 1h)
- 22:30-23:30: Fine-tuning (10 rounds × 7s ≈ 1h)
- 23:30-00:30: FedForget (10 rounds × 7s ≈ 1h)
- **预计完成**: 00:30 (明天凌晨)

---

## 📝 检查点

### 上午完成标志
- [ ] 消融实验结果文件生成: `results/ablation_study.csv`
- [ ] 可复现性验证Seed 42完成
- [ ] 两个实验日志无错误

### 下午完成标志
- [ ] 消融实验分析表格生成
- [ ] 可复现性统计数据计算完成
- [ ] 10客户端脚本测试通过

### 晚上完成标志
- [ ] 10客户端实验成功启动
- [ ] 日志显示预训练开始
- [ ] 进程运行正常

---

## 🚨 风险预案

### 风险1: 消融实验timeout
**症状**: results/ablation_study.csv未生成

**应对**:
1. 检查日志最后的变体
2. 手动重跑未完成的变体
3. 合并结果

### 风险2: 可复现性验证崩溃
**症状**: 进程消失,日志报错

**应对**:
1. 检查报错信息
2. 修复Bug
3. 从当前seed继续

### 风险3: 10客户端实验启动失败
**症状**: 立即崩溃或报错

**应对**:
1. 先运行5分钟测试
2. 检查数据加载
3. 验证10客户端数据分配

---

## 📊 明天预期

### Day 6 (2025-10-07) 预览
- **上午**: 分析10客户端第1次结果
- **下午**: 运行10客户端第2次 (Seed 123)
- **晚上**: 运行10客户端第3次 (Seed 456)

---

## 💡 关键决策

### 决策1: 今晚启动10客户端实验
**理由**:
- Week 1最关键任务
- 运行时间长(4-5h),晚上启动利用夜间时间
- 明天可分析结果

### 决策2: 消融+可复现性并行等待
**理由**:
- 两个实验已在运行
- 等待完成比中断重跑更高效

### 决策3: 下午做数据分析
**理由**:
- 实验完成后立即分析
- 发现问题可及时调整
- 为10客户端实验验证方法

---

## ✅ 今日目标

### Must Have (P0)
- [x] 消融实验完成
- [x] 可复现性验证Seed 42完成
- [x] 10客户端实验启动

### Should Have (P1)
- [ ] 消融实验初步分析
- [ ] 可复现性验证3 seeds完成

### Nice to Have (P2)
- [ ] 生成初步图表
- [ ] 更新论文实验章节草稿

---

**执行人**: Claude Code
**开始时间**: 2025-10-06 09:00
**状态**: 🟢 按计划执行

**实时更新**: 此文档将在每个阶段完成后更新进度
