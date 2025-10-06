# FedForget 论文术语统一指南 📖

**目的**: 确保论文全文术语使用一致,提高专业性和可读性

---

## 📋 标准术语表

### 核心概念术语

| ✅ 标准术语 | ❌ 避免使用 | 说明 |
|-----------|-----------|------|
| **forgetting client** | target client, unlearning client, forget client | 需要被遗忘的客户端 |
| **remaining clients** | retain clients, other clients, non-forgetting clients | 保留的客户端 |
| **FedForget** | Fedforget, Fed-Forget, fedforget | 我们的方法名(首字母大写) |
| **Teacher A** | teacher A, Teacher a, the global teacher | 全局教师模型(大写A) |
| **Teacher B** | teacher B, Teacher b, the local teacher | 局部教师模型(大写B) |
| **dual-teacher** | Dual-Teacher, dual teacher | 双教师(连字符,小写) |
| **knowledge distillation** | Knowledge Distillation | 知识蒸馏(小写,除非句首) |

### 评估指标术语

| ✅ 标准术语 | ❌ 避免使用 | 首次出现完整形式 |
|-----------|-----------|---------------|
| **Test Accuracy** | test accuracy, Test Acc | Test Accuracy (Test Acc) |
| **retention** | Retention | retention (小写) |
| **forgetting rate** | Forgetting Rate, forgetting | forgetting rate (小写) |
| **Attack Success Rate (ASR)** | attack success rate, ASR | Attack Success Rate (ASR) |
| **Area Under Curve (AUC)** | area under curve, AUC | Area Under Curve (AUC) |

### 专有名词 (必须大写)

| 术语 | 说明 |
|------|------|
| **CIFAR-10** | 数据集名称 |
| **ResNet-18** | 模型架构 |
| **GDPR** | 欧盟通用数据保护条例 |
| **CCPA** | 加州消费者隐私法 |
| **FedAvg** | 联邦平均算法 |
| **FedProx** | 联邦近端算法 |
| **SimpleMIA** | 简单成员推断攻击 |
| **Non-IID** | 非独立同分布 |
| **Dirichlet** | 狄利克雷分布 |

### 算法和方法名

| ✅ 标准术语 | ❌ 避免使用 |
|-----------|-----------|
| **FedEraser** | FedEraser, Fed-Eraser |
| **KNOT** | Knot, knot |
| **Ferrari** | ferrari, FERRARI |
| **SISA** | Sisa, sisa |

---

## 🔧 术语使用规则

### 1. 首次出现规则

首次提到术语时,使用完整形式并附带缩写:

✅ **正确**:
> "We evaluate using Attack Success Rate (ASR), where ASR≈50% indicates ideal privacy."

❌ **错误**:
> "We evaluate using ASR, where ASR≈50% indicates ideal privacy."

### 2. 大小写规则

#### 专有名词和方法名: 保持原始大小写
- FedForget, CIFAR-10, ResNet-18

#### 一般术语: 小写(除非句首)
- knowledge distillation
- forgetting rate
- retention

#### 指标名: 首字母大写
- Test Accuracy
- Attack Success Rate
- Area Under Curve

### 3. 连字符规则

| 术语 | 使用连字符 | 不使用连字符 |
|------|----------|------------|
| dual-teacher | ✅ dual-teacher mechanism | ❌ dual teacher |
| server-side | ✅ server-side aggregation | ❌ server side |
| client-side | ✅ client-side training | ❌ client side |
| Non-IID | ✅ Non-IID data | ❌ Non IID, NonIID |

### 4. 单复数规则

#### 单数形式
- forgetting client (指代一个)
- the remaining client (指代某一个)

#### 复数形式
- remaining clients (指代多个)
- the clients (总称)

---

## 📊 数字和指标标准化

### 关键数字 (必须一致)

| 指标 | 标准值 | 上下文 |
|------|--------|--------|
| Forgetting rate (5 clients) | **20.01±1.92%** | Main results |
| Retention (5 clients) | **96.57±1.21%** | Main results |
| ASR (5 clients) | **52.91±2.32%** | Main results |
| Dual-teacher improvement | **+11.54%** | Ablation study |
| Retention (10 clients) | **98.66±1.37%** | Scalability |
| ASR (10 clients) | **50.23±1.62%** | Scalability |
| Speedup vs Retrain | **1.53-1.75×** | Efficiency |

### 数字格式规则

#### 百分比
✅ 20.01% (数字+百分号,无空格)
❌ 20.01 % (有空格)

#### 范围
✅ 1.53-1.75× (连字符)
❌ 1.53~1.75× (波浪号)

#### 误差
✅ 20.01±1.92% (±符号)
❌ 20.01 +/- 1.92% (文字)

---

## 🔍 常见错误和修正

### 错误类型1: Teacher大小写不一致

❌ **错误**:
> "Teacher A provides global knowledge, while teacher B offers local guidance."

✅ **正确**:
> "Teacher A provides global knowledge, while Teacher B offers local guidance."

### 错误类型2: FedForget大小写错误

❌ **错误**:
> "Fedforget achieves better performance..."

✅ **正确**:
> "FedForget achieves better performance..."

### 错误类型3: 术语不一致

❌ **错误**:
> "The target client's data is removed, while other clients continue training."

✅ **正确**:
> "The forgetting client's data is removed, while remaining clients continue training."

### 错误类型4: 缩写未定义

❌ **错误**:
> "Our method achieves ASR=52.91%."

✅ **正确**:
> "Our method achieves Attack Success Rate (ASR)=52.91%."

---

## 📝 引用格式规范

### LaTeX引用

#### 文献引用
```latex
✅ \cite{mcmahan2017fedavg}
✅ \cite{liu2021federaser, wu2023federated}
❌ [Liu et al., 2021]
```

#### 章节引用
```latex
✅ Section~\ref{sec:method}
✅ Section~\ref{sec:experiments}
❌ Section 3
```

#### 图表引用
```latex
✅ Figure~\ref{fig:main_results}
✅ Table~\ref{tab:ablation}
❌ Figure 1
❌ Table 2
```

### Markdown引用 (当前阶段)

#### 章节引用
```markdown
✅ Section 3.2
✅ Section 4.3 (Ablation Study)
```

#### 图表引用
```markdown
✅ Table 1
✅ Figure 1 (Main Results)
```

---

## 🎯 快速检查清单

撰写时自查:

- [ ] FedForget 首字母大写?
- [ ] Teacher A / Teacher B 大写?
- [ ] forgetting client (非 target client)?
- [ ] remaining clients (非 other clients)?
- [ ] 首次提到ASR时定义全称?
- [ ] 关键数字与标准值一致?
- [ ] 连字符正确 (dual-teacher, server-side)?
- [ ] 引用格式统一 (\cite{} 或 Section X)?

---

## 🔧 自动化修正建议

### 使用sed批量替换 (LaTeX阶段)

```bash
# 修正Teacher大小写
sed -i 's/teacher A/Teacher A/g' *.tex
sed -i 's/teacher B/Teacher B/g' *.tex

# 修正FedForget
sed -i 's/Fedforget/FedForget/g' *.tex
sed -i 's/fedforget/FedForget/g' *.tex

# 修正术语
sed -i 's/target client/forgetting client/g' *.tex
sed -i 's/other clients/remaining clients/g' *.tex
```

### 使用VS Code查找替换

1. Ctrl+H 打开查找替换
2. 启用正则表达式
3. 查找: `\bteacher A\b`
4. 替换: `Teacher A`
5. 全部替换

---

## 📖 术语词汇表 (Glossary)

| 英文术语 | 中文对应 | 缩写 |
|---------|---------|------|
| Federated Learning | 联邦学习 | FL |
| Machine Unlearning | 机器遗忘 | - |
| Knowledge Distillation | 知识蒸馏 | KD |
| Membership Inference Attack | 成员推断攻击 | MIA |
| Attack Success Rate | 攻击成功率 | ASR |
| Non-Identically Distributed | 非独立同分布 | Non-IID |
| General Data Protection Regulation | 通用数据保护条例 | GDPR |
| California Consumer Privacy Act | 加州消费者隐私法 | CCPA |

---

## 🎯 总结

### 最重要的5条规则

1. **FedForget** - 永远首字母大写
2. **Teacher A / Teacher B** - 永远大写
3. **forgetting client** - 永远用这个,不用 target client
4. **remaining clients** - 永远用这个,不用 other clients
5. **首次提到缩写必须定义全称** - ASR, KD, MIA等

### 检查工具

运行一致性检查脚本:
```bash
python scripts/check_consistency.py
```

### 下一步

1. 使用本指南修正58个已发现问题
2. LaTeX转换时应用术语统一
3. 最终校对时再次检查

---

**术语统一 = 论文专业性提升! 🚀**

**坚持使用标准术语,让论文更清晰、更一致、更专业! ✨**
