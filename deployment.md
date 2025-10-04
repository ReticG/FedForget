# FedForget 服务器部署方案

## 1. 资源配置总览

### 1.1 硬件配置（Featurize.cn）
```
平台: https://featurize.cn/vm/available
GPU型号: NVIDIA RTX 4090 (24GB VRAM)
CPU: AMD EPYC 9354 16核
内存: 60GB
磁盘: 750GB
单价: ¥1.87/小时
```

### 1.2 并行方案
```
阶段1: 1台 × 48小时 = ¥90
阶段2: 4台 × 120小时 = ¥898
阶段3: 2台 × 72小时 = ¥269
--------------------------------------
总计: ¥1,257 (10天完成全部实验)
```

---

## 2. 服务器分工详细方案

### 服务器1: 基线对比实验
**职责**: 实验1 - 基本遗忘能力验证
**运行时间**: Day 3-7 (120小时)
**成本**: ¥224

#### 任务清单
```bash
# 数据集准备
datasets=("cifar10" "fashion_mnist")
models=("convnet" "lenet5")

# 基线方法
methods=(
  "retrain"
  "federaser"
  "fedau"
  "fedforget"
  "finetune"
  "no_unlearning"
)

# 主实验循环
for dataset in "${datasets[@]}"; do
  for model in "${models[@]}"; do
    for method in "${methods[@]}"; do
      for seed in 42 43 44; do
        python train.py \
          --exp exp1_baseline \
          --dataset $dataset \
          --model $model \
          --method $method \
          --seed $seed \
          --num_clients 10 \
          --unlearn_ratio 0.2 \
          --lambda_forget 3.0 \
          --distill_temp 2.0 \
          --save_dir ./results/exp1
      done
    done
  done
done
```

#### 预期产出
- `results/exp1/cifar10_*.json`: CIFAR-10所有方法结果
- `results/exp1/fmnist_*.json`: Fashion-MNIST结果
- `results/exp1/table1.csv`: 论文Table 1核心数据

---

### 服务器2: 消融与持续遗忘
**职责**: 实验2消融 + 实验3持续遗忘
**运行时间**: Day 3-7 (120小时)
**成本**: ¥224

#### 任务A: 消融实验
```bash
# 实验2: 权重调整策略消融
variants=(
  "complete"           # 完整FedForget
  "no_dynamic_weight"  # 固定权重
  "no_kd"              # 无知识蒸馏
  "no_weight_bound"    # 无权重约束
)

for variant in "${variants[@]}"; do
  for dataset in cifar10 fashion_mnist; do
    for seed in 42 43 44; do
      python train.py \
        --exp exp2_ablation \
        --variant $variant \
        --dataset $dataset \
        --seed $seed \
        --save_dir ./results/exp2
    done
  done
done
```

#### 任务B: 参数敏感性分析
```bash
# 网格搜索 λ × T
lambdas=(2 3 5 10)
temps=(1 2 5 10)

for lambda in "${lambdas[@]}"; do
  for temp in "${temps[@]}"; do
    python train.py \
      --exp exp2_sensitivity \
      --lambda_forget $lambda \
      --distill_temp $temp \
      --dataset cifar10 \
      --save_dir ./results/exp2/sensitivity
  done
done
```

#### 任务C: 持续遗忘
```bash
# 实验3: 训练期间持续遗忘
python train.py \
  --exp exp3_continuous \
  --unlearn_prob 0.2 \
  --total_rounds 200 \
  --methods federaser,fedforget,baseline \
  --save_dir ./results/exp3
```

#### 预期产出
- `results/exp2/ablation_*.json`: 消融实验数据
- `results/exp2/sensitivity_heatmap.csv`: 参数敏感性热力图数据
- `results/exp3/continuous_*.json`: 持续遗忘结果

---

### 服务器3: 鲁棒性与规模
**职责**: 实验4 Non-IID + 实验5规模扩展
**运行时间**: Day 3-6 (96小时)
**成本**: ¥180

#### 任务A: Non-IID鲁棒性
```bash
# 实验4: Dirichlet分布
alphas=(0.1 0.5 1.0 10.0)

for alpha in "${alphas[@]}"; do
  python train.py \
    --exp exp4_noniid \
    --data_dist dirichlet \
    --dirichlet_alpha $alpha \
    --methods federaser,fedforget,finetune \
    --dataset cifar10 \
    --save_dir ./results/exp4
done

# FEMNIST天然Non-IID
python train.py \
  --exp exp4_noniid \
  --dataset femnist \
  --methods federaser,fedforget \
  --save_dir ./results/exp4
```

#### 任务B: 规模扩展性
```bash
# 实验5: 大规模客户端
num_clients=(50 100)
participation_rates=(0.05 0.1)

for K in "${num_clients[@]}"; do
  for C in "${participation_rates[@]}"; do
    python train.py \
      --exp exp5_scale \
      --num_clients $K \
      --participation_rate $C \
      --methods federaser,fedforget \
      --dataset cifar10 \
      --save_dir ./results/exp5
  done
done
```

#### 预期产出
- `results/exp4/noniid_alpha_*.json`: 不同α下的结果
- `results/exp4/femnist_*.json`: FEMNIST结果
- `results/exp5/scale_K*.json`: 规模扩展数据

---

### 服务器4: 隐私评估与补充
**职责**: 实验6 MIA评估 + 补充实验
**运行时间**: Day 3-7 (120小时)
**成本**: ¥224

#### 任务A: 训练影子模型
```bash
# Step 1: 训练5个影子模型
for i in {1..5}; do
  python train_shadow.py \
    --shadow_id $i \
    --dataset purchase100 \
    --save_dir ./results/exp6/shadows
done
```

#### 任务B: 训练攻击分类器
```bash
# Step 2: 基于影子模型训练攻击者
python train_attacker.py \
  --shadow_dir ./results/exp6/shadows \
  --attack_model mlp \
  --save_dir ./results/exp6/attacker
```

#### 任务C: MIA评估
```bash
# Step 3: 评估各方法的MIA脆弱性
methods=("retrain" "federaser" "fedforget" "no_unlearning")

for method in "${methods[@]}"; do
  python eval_mia.py \
    --method $method \
    --attacker_path ./results/exp6/attacker/model.pt \
    --dataset purchase100 \
    --metrics asr,tpr_at_fpr,auc_roc \
    --save_dir ./results/exp6/eval
done
```

#### 任务D: 补充实验
```bash
# CIFAR-100复杂场景
python train.py \
  --exp exp6_supplement \
  --dataset cifar100 \
  --methods federaser,fedforget \
  --save_dir ./results/exp6

# 不同遗忘比例
for ratio in 0.1 0.2 0.3; do
  python train.py \
    --exp exp6_supplement \
    --unlearn_ratio $ratio \
    --dataset cifar10 \
    --save_dir ./results/exp6
done
```

#### 预期产出
- `results/exp6/shadows/`: 5个影子模型
- `results/exp6/attacker/`: 攻击分类器
- `results/exp6/eval/mia_*.json`: MIA评估结果
- `results/exp6/roc_curve_data.csv`: ROC曲线数据

---

## 3. 自动化部署脚本

### 3.1 环境准备脚本
```bash
#!/bin/bash
# setup_env.sh - 在每台服务器上运行

# 1. 更新系统包
apt-get update && apt-get upgrade -y

# 2. 安装Python依赖
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install numpy pandas matplotlib seaborn
pip install scikit-learn scipy
pip install wandb tensorboard
pip install tqdm pyyaml

# 3. 下载数据集
python scripts/download_datasets.py \
  --datasets mnist,fashion_mnist,cifar10,cifar100,purchase100 \
  --save_dir ./data

# 4. 测试GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# 5. 初始化W&B
wandb login  # 需要输入API key
```

### 3.2 统一启动脚本
```bash
#!/bin/bash
# launch_all.sh - 从本地机器启动所有服务器

# 服务器连接信息
servers=(
  "user@server1.featurize.cn"
  "user@server2.featurize.cn"
  "user@server3.featurize.cn"
  "user@server4.featurize.cn"
)

scripts=(
  "run_server1.sh"
  "run_server2.sh"
  "run_server3.sh"
  "run_server4.sh"
)

# 上传代码到所有服务器
for server in "${servers[@]}"; do
  echo "上传代码到 $server"
  rsync -avz --exclude 'results/' --exclude '*.pyc' \
    ./ $server:/workspace/fedforget/
done

# 启动所有实验
for i in {0..3}; do
  server=${servers[$i]}
  script=${scripts[$i]}

  echo "启动 $server - $script"
  ssh $server "cd /workspace/fedforget && nohup bash scripts/$script > logs/server$((i+1)).log 2>&1 &"
done

echo "所有服务器已启动，监控地址: https://wandb.ai/your-team/FedForget"
```

### 3.3 各服务器运行脚本

#### run_server1.sh
```bash
#!/bin/bash
# 服务器1: 基线对比实验

export CUDA_VISIBLE_DEVICES=0
export WANDB_PROJECT="FedForget"
export SERVER_ID=1

echo "=== 服务器1: 开始基线对比实验 ==="
date

# CIFAR-10 实验
for method in retrain federaser fedau fedforget finetune no_unlearning; do
  echo "运行方法: $method"
  for seed in 42 43 44; do
    python train.py \
      --exp exp1_baseline \
      --dataset cifar10 \
      --model convnet \
      --method $method \
      --seed $seed \
      --num_clients 10 \
      --unlearn_ratio 0.2 \
      --save_dir ./results/exp1 \
      --wandb_name "Server1-Exp1-CIFAR10-$method-seed$seed"
  done
done

# Fashion-MNIST 实验
for method in retrain federaser fedforget finetune; do
  echo "运行方法: $method"
  python train.py \
    --exp exp1_baseline \
    --dataset fashion_mnist \
    --model lenet5 \
    --method $method \
    --save_dir ./results/exp1 \
    --wandb_name "Server1-Exp1-FMNIST-$method"
done

echo "=== 服务器1: 实验完成 ==="
date
```

#### run_server2.sh
```bash
#!/bin/bash
# 服务器2: 消融 + 持续遗忘

export CUDA_VISIBLE_DEVICES=0
export WANDB_PROJECT="FedForget"
export SERVER_ID=2

echo "=== 服务器2: 开始消融与持续遗忘实验 ==="
date

# 实验2: 消融
for variant in complete no_dynamic_weight no_kd no_weight_bound; do
  for dataset in cifar10 fashion_mnist; do
    python train.py \
      --exp exp2_ablation \
      --variant $variant \
      --dataset $dataset \
      --save_dir ./results/exp2 \
      --wandb_name "Server2-Exp2-Ablation-$variant-$dataset"
  done
done

# 参数敏感性
for lambda in 2 3 5 10; do
  for temp in 1 2 5 10; do
    python train.py \
      --exp exp2_sensitivity \
      --lambda_forget $lambda \
      --distill_temp $temp \
      --dataset cifar10 \
      --save_dir ./results/exp2/sensitivity \
      --wandb_name "Server2-Exp2-Sensitivity-L${lambda}-T${temp}"
  done
done

# 实验3: 持续遗忘
python train.py \
  --exp exp3_continuous \
  --unlearn_prob 0.2 \
  --total_rounds 200 \
  --methods federaser,fedforget,baseline \
  --save_dir ./results/exp3 \
  --wandb_name "Server2-Exp3-Continuous"

echo "=== 服务器2: 实验完成 ==="
date
```

#### run_server3.sh
```bash
#!/bin/bash
# 服务器3: 鲁棒性 + 规模

export CUDA_VISIBLE_DEVICES=0
export WANDB_PROJECT="FedForget"
export SERVER_ID=3

echo "=== 服务器3: 开始鲁棒性与规模实验 ==="
date

# 实验4: Non-IID
for alpha in 0.1 0.5 1.0 10.0; do
  python train.py \
    --exp exp4_noniid \
    --data_dist dirichlet \
    --dirichlet_alpha $alpha \
    --methods federaser,fedforget,finetune \
    --dataset cifar10 \
    --save_dir ./results/exp4 \
    --wandb_name "Server3-Exp4-NonIID-alpha${alpha}"
done

# FEMNIST
python train.py \
  --exp exp4_noniid \
  --dataset femnist \
  --methods federaser,fedforget \
  --save_dir ./results/exp4 \
  --wandb_name "Server3-Exp4-FEMNIST"

# 实验5: 规模
for K in 50 100; do
  for C in 0.05 0.1; do
    python train.py \
      --exp exp5_scale \
      --num_clients $K \
      --participation_rate $C \
      --dataset cifar10 \
      --save_dir ./results/exp5 \
      --wandb_name "Server3-Exp5-Scale-K${K}-C${C}"
  done
done

echo "=== 服务器3: 实验完成 ==="
date
```

#### run_server4.sh
```bash
#!/bin/bash
# 服务器4: MIA评估 + 补充

export CUDA_VISIBLE_DEVICES=0
export WANDB_PROJECT="FedForget"
export SERVER_ID=4

echo "=== 服务器4: 开始MIA评估与补充实验 ==="
date

# 实验6: 训练影子模型
for i in {1..5}; do
  python train_shadow.py \
    --shadow_id $i \
    --dataset purchase100 \
    --save_dir ./results/exp6/shadows \
    --wandb_name "Server4-Exp6-Shadow${i}"
done

# 训练攻击分类器
python train_attacker.py \
  --shadow_dir ./results/exp6/shadows \
  --save_dir ./results/exp6/attacker \
  --wandb_name "Server4-Exp6-Attacker"

# MIA评估
for method in retrain federaser fedforget no_unlearning; do
  python eval_mia.py \
    --method $method \
    --attacker_path ./results/exp6/attacker/model.pt \
    --dataset purchase100 \
    --save_dir ./results/exp6/eval \
    --wandb_name "Server4-Exp6-MIA-$method"
done

# 补充实验
python train.py \
  --exp exp6_supplement \
  --dataset cifar100 \
  --save_dir ./results/exp6 \
  --wandb_name "Server4-Exp6-CIFAR100"

for ratio in 0.1 0.2 0.3; do
  python train.py \
    --exp exp6_supplement \
    --unlearn_ratio $ratio \
    --dataset cifar10 \
    --save_dir ./results/exp6 \
    --wandb_name "Server4-Exp6-Ratio${ratio}"
done

echo "=== 服务器4: 实验完成 ==="
date
```

---

## 4. 监控与管理

### 4.1 实时监控脚本
```bash
#!/bin/bash
# monitor.sh - 实时监控所有服务器

servers=(
  "user@server1.featurize.cn"
  "user@server2.featurize.cn"
  "user@server3.featurize.cn"
  "user@server4.featurize.cn"
)

while true; do
  clear
  echo "========================================="
  echo "FedForget 实验监控"
  echo "时间: $(date)"
  echo "========================================="

  for i in {0..3}; do
    server=${servers[$i]}
    echo ""
    echo "服务器 $((i+1)): $server"
    echo "-----------------------------------------"

    # GPU使用率
    ssh $server "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader" | \
      awk '{print "GPU利用率: " $1 ", 显存: " $2 " / " $3}'

    # 磁盘空间
    ssh $server "df -h /workspace | tail -1" | \
      awk '{print "磁盘使用: " $3 " / " $2 " (" $5 ")"}'

    # 最新日志
    echo "最新日志:"
    ssh $server "tail -n 2 /workspace/fedforget/logs/server$((i+1)).log"
  done

  echo ""
  echo "按Ctrl+C退出，30秒后刷新..."
  sleep 30
done
```

### 4.2 结果收集脚本
```bash
#!/bin/bash
# collect_results.sh - 收集所有服务器的结果

servers=(
  "user@server1.featurize.cn"
  "user@server2.featurize.cn"
  "user@server3.featurize.cn"
  "user@server4.featurize.cn"
)

mkdir -p ./collected_results

for i in {0..3}; do
  server=${servers[$i]}
  echo "从服务器$((i+1))下载结果..."

  rsync -avz --progress \
    $server:/workspace/fedforget/results/ \
    ./collected_results/server$((i+1))/
done

echo "结果收集完成: ./collected_results/"
```

---

## 5. Checkpoint管理

### 5.1 自动保存脚本
```python
# utils/checkpoint.py
import os
import torch
from datetime import datetime

class CheckpointManager:
    def __init__(self, save_dir, keep_last_n=3):
        self.save_dir = save_dir
        self.keep_last_n = keep_last_n
        os.makedirs(save_dir, exist_ok=True)

    def save(self, state, metric_value, step):
        """保存checkpoint"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ckpt_step{step}_metric{metric_value:.4f}_{timestamp}.pt"
        path = os.path.join(self.save_dir, filename)

        torch.save(state, path)
        print(f"Checkpoint saved: {path}")

        # 清理旧checkpoint
        self._cleanup_old_checkpoints()

    def _cleanup_old_checkpoints(self):
        """保留最新的N个checkpoint"""
        ckpts = sorted(
            [f for f in os.listdir(self.save_dir) if f.endswith('.pt')],
            key=lambda x: os.path.getmtime(os.path.join(self.save_dir, x)),
            reverse=True
        )

        for old_ckpt in ckpts[self.keep_last_n:]:
            os.remove(os.path.join(self.save_dir, old_ckpt))
            print(f"Removed old checkpoint: {old_ckpt}")

# 使用示例
ckpt_manager = CheckpointManager('./checkpoints', keep_last_n=3)

# 在训练循环中每小时保存
if step % 100 == 0:  # 假设每100步=1小时
    ckpt_manager.save({
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'step': step,
        'metric': current_metric
    }, metric_value=current_metric, step=step)
```

---

## 6. 成本控制建议

### 6.1 节省成本的技巧
```bash
# 1. 使用混合精度训练（加速30%）
python train.py --mixed_precision  # 节省¥90

# 2. 优化数据加载（减少IO等待）
python train.py --num_workers 4 --prefetch_factor 2

# 3. 批量实验（减少启动开销）
python batch_experiments.py --config configs/all_exp1.yaml

# 4. 提前终止不佳实验
python train.py --early_stopping --patience 10
```

### 6.2 预算跟踪
```python
# scripts/budget_tracker.py
import time
from datetime import datetime

class BudgetTracker:
    def __init__(self, hourly_rate=1.87, budget=1500):
        self.hourly_rate = hourly_rate
        self.budget = budget
        self.start_time = time.time()

    def get_current_cost(self, num_servers=4):
        hours = (time.time() - self.start_time) / 3600
        cost = hours * self.hourly_rate * num_servers
        return cost

    def get_remaining_budget(self, num_servers=4):
        return self.budget - self.get_current_cost(num_servers)

    def get_estimated_finish_time(self, progress, num_servers=4):
        """根据当前进度估算完成时间"""
        if progress == 0:
            return "无法估算"

        elapsed = time.time() - self.start_time
        total_time = elapsed / progress
        remaining_time = total_time - elapsed

        finish_time = datetime.fromtimestamp(time.time() + remaining_time)
        return finish_time.strftime("%Y-%m-%d %H:%M:%S")

# 使用
tracker = BudgetTracker()
print(f"当前花费: ¥{tracker.get_current_cost():.2f}")
print(f"剩余预算: ¥{tracker.get_remaining_budget():.2f}")
print(f"预计完成: {tracker.get_estimated_finish_time(progress=0.3)}")
```

---

## 7. 故障恢复

### 7.1 服务器中断恢复
```bash
#!/bin/bash
# recover.sh - 从checkpoint恢复实验

# 检查最新checkpoint
latest_ckpt=$(ls -t ./checkpoints/*.pt | head -1)

if [ -z "$latest_ckpt" ]; then
  echo "未找到checkpoint，从头开始"
  bash scripts/run_server1.sh
else
  echo "从checkpoint恢复: $latest_ckpt"
  python train.py \
    --resume_from $latest_ckpt \
    --exp exp1_baseline \
    --continue_training
fi
```

---

## 8. 最终清单

### 开始实验前检查
- [ ] 所有服务器已开通并可SSH连接
- [ ] 代码已上传到所有服务器
- [ ] 数据集已下载完成
- [ ] W&B已配置并测试
- [ ] 自动保存checkpoint已启用
- [ ] 监控脚本已运行
- [ ] 预算跟踪器已启动

### 实验期间检查（每日）
- [ ] 检查服务器运行状态
- [ ] 查看W&B Dashboard
- [ ] 验证结果保存正常
- [ ] 监控成本是否在预算内
- [ ] 检查GPU利用率

### 实验完成后
- [ ] 下载所有结果到本地
- [ ] 验证数据完整性
- [ ] 关闭所有服务器（避免持续计费）
- [ ] 生成最终成本报告
- [ ] 备份代码和数据

---

## 总结

采用4服务器并行方案，预计：
- **总时间**: 7-10天
- **总成本**: ¥1,200-1,500
- **成功率**: >95%（充分冗余）
- **数据质量**: 高（多次重复实验）

关键优势：
✅ 高度并行，快速完成
✅ 成本可控，实时监控
✅ 容错能力强，自动恢复
✅ 结果可复现，质量有保证
