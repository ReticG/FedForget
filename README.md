# FedForget: 基于权重调整的联邦遗忘框架

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)

> **Weight-Aware Federated Unlearning: 通过智能权重调整实现高效联邦遗忘**

## 📖 简介

FedForget 是一个创新的联邦遗忘框架，通过**动态权重调整**实现高效的知识移除，无需额外训练轮次或历史梯度存储。

### 核心创新

- 🎯 **权重调整范式**: 首次通过聚合权重调整实现联邦遗忘
- 🚀 **高效实用**: 5×加速（相比重训练），存储节省90%（相比FedEraser）
- 🔒 **隐私保护**: MIA攻击成功率≈50%（接近重训练水平）
- 💪 **鲁棒性强**: 在Non-IID场景和大规模客户端下稳定有效

## 🏗️ 项目结构

```
FedForget/
├── spec.md              # 核心idea和技术方案
├── experiment.md        # 完整实验设计（对齐SOTA）
├── deployment.md        # 4服务器并行部署方案
├── README.md           # 本文件
├── src/                # 源代码（待实现）
│   ├── federated/      # 联邦学习核心
│   ├── unlearning/     # 遗忘算法
│   ├── models/         # 模型定义
│   ├── data/           # 数据加载
│   └── utils/          # 工具函数
├── scripts/            # 实验脚本
├── configs/            # 配置文件
└── requirements.txt    # 依赖包
```

## 📋 文档说明

### [spec.md](spec.md)
论文核心思路和技术方案，包括：
- 基本理念：重新分配模型贡献度实现遗忘
- 客户端侧：负权重知识蒸馏
- 服务器侧：动态权重调整策略
- 质量保障体系和风险应对

### [experiment.md](experiment.md)
完整的实验设计方案（对齐顶会标准），包括：
- 6个核心实验（基线对比、消融、持续遗忘、Non-IID、规模扩展、MIA评估）
- 10个基线方法对比（FedEraser, FedAU, SFU等SOTA）
- 11个可视化图表设计
- 预期实验结果和成功标准

### [deployment.md](deployment.md)
4服务器并行部署方案，包括：
- Featurize.cn云服务器配置（RTX 4090 × 4台）
- 总预算：¥1,200-1,500，总时间：7-10天
- 自动化脚本和监控方案
- Checkpoint管理和故障恢复

## 🎯 研究目标

### 核心研究问题（RQs）
1. **RQ1**: 权重调整策略能否有效实现遗忘？
2. **RQ2**: 相比SOTA方法，性能和效率如何？
3. **RQ3**: 在不同场景下的鲁棒性如何？
4. **RQ4**: 多客户端并发遗忘的可行性？

### 预期贡献
- **方法创新**: 提出基于权重调整的联邦遗忘新范式
- **效率提升**: 5×加速，存储节省90%
- **理论分析**: 收敛性分析或遗忘保证证明（目标）
- **实验验证**: 6数据集 × 4场景 × 10基线的全面评估

## 📊 预期实验结果

| 指标 | FedForget | FedEraser | Retrain |
|------|-----------|-----------|---------|
| MIA ASR ↓ | **51.5%** | 52.1% | 50.2% |
| Test Acc ↑ | **85.0%** | 84.9% | 85.3% |
| Speedup ↑ | **5×** | 4× | 1× |
| Storage | **Low** | High | Low |

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PyTorch 2.0+
- CUDA 11.8+ (GPU训练)
- 60GB+ RAM (大规模实验)

### 安装依赖
```bash
# 克隆仓库
git clone https://github.com/YourUsername/FedForget.git
cd FedForget

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行示例（待实现）
```bash
# 快速验证实验（MNIST）
python train.py --exp quick_test --dataset mnist --method fedforget

# 完整实验1：基线对比
python train.py --exp exp1_baseline --dataset cifar10 --method fedforget

# 消融实验
python train.py --exp exp2_ablation --variant complete
```

## 📈 实验计划

### 阶段1: 快速验证（Day 1-2）
- [x] 文档准备完成
- [ ] 代码实现
- [ ] MNIST快速验证
- [ ] 参数预筛选

### 阶段2: 主实验并行（Day 3-7）
- [ ] 实验1: 基线对比（CIFAR-10, Fashion-MNIST）
- [ ] 实验2: 消融实验
- [ ] 实验3: 持续遗忘
- [ ] 实验4: Non-IID鲁棒性
- [ ] 实验5: 规模扩展
- [ ] 实验6: MIA评估

### 阶段3: 补充验证（Day 8-10）
- [ ] 重复实验（可复现性）
- [ ] 统计显著性检验
- [ ] 生成所有图表
- [ ] 论文撰写

## 📚 数据集

实验使用以下数据集：
- **MNIST** / **Fashion-MNIST**: 基础验证
- **CIFAR-10** / **CIFAR-100**: 主要实验
- **FEMNIST**: 联邦场景（天然Non-IID）
- **Purchase-100**: 隐私遗忘评估

## 🔬 基线方法

对比的SOTA方法：
- **FedEraser** (NeurIPS): 历史梯度校准
- **FedAU** (IJCAI 2024): 辅助遗忘模块
- **SFU** (2024): 多教师知识蒸馏
- **Exact-Fun**: 精确联邦遗忘
- **SISA**: 数据分片
- **Fine-tuning**: 简单微调
- **Gradient Ascent**: 梯度上升遗忘

## 📊 可视化

计划生成的图表：
- **Table 1**: 核心结果对比（MIA/Acc/Time/Storage）
- **Figure 1**: Trade-off分析（遗忘效果 vs 模型效用）
- **Figure 2**: 遗忘进度曲线
- **Figure 3**: 消融实验柱状图
- **Figure 4**: 参数敏感性热力图
- **Figure 5**: 权重演化曲线
- **Figure 6**: MIA攻击ROC曲线
- **Figure 7-11**: 更多分析图表

## 💰 成本估算

基于 [Featurize.cn](https://featurize.cn) RTX 4090云服务器：
- 单价: ¥1.87/小时
- 4服务器并行: ¥7.48/小时
- **总预算**: ¥1,200-1,500（7-10天）

详见 [deployment.md](deployment.md)

## 🤝 贡献

欢迎贡献！请查看贡献指南（待添加）。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 作者: Retic
- 项目链接: [https://github.com/YourUsername/FedForget](https://github.com/YourUsername/FedForget)

## 🙏 致谢

感谢以下工作的启发：
- **FedEraser**: Liu et al., NeurIPS 2021
- **FedAU**: IJCAI 2024
- **SFU**: Streamlined Federated Unlearning, 2024

## 📖 引用

如果本项目对你的研究有帮助，请引用（论文发表后）：

```bibtex
@article{fedforget2024,
  title={FedForget: Weight-Aware Federated Unlearning Framework},
  author={Your Name},
  journal={arXiv preprint arXiv:XXXX.XXXXX},
  year={2024}
}
```

---

**状态**: 🚧 文档准备完成，代码实现中...

**更新日期**: 2025-10-04
