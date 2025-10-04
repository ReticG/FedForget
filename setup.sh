#!/bin/bash
set -e

echo "=== FedForget 环境配置脚本 ==="
echo "开始时间: $(date)"

# 1. 安装PyTorch
echo ""
echo "[1/5] 安装PyTorch (CUDA 12.3)..."
pip3 install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 2. 安装其他依赖
echo "[2/5] 安装Python依赖..."
pip3 install --quiet numpy pandas matplotlib seaborn scikit-learn scipy tqdm pyyaml

# 3. 安装W&B (可选)
echo "[3/5] 安装Weights & Biases..."
pip3 install --quiet wandb

# 4. 验证PyTorch安装
echo "[4/5] 验证PyTorch..."
python3 << PYEOF
import torch
print(f"✓ PyTorch版本: {torch.__version__}")
print(f"✓ CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✓ 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
PYEOF

# 5. 创建项目结构
echo "[5/5] 创建项目结构..."
mkdir -p ~/fedforget/{src,data,results,checkpoints,logs,scripts,configs}
mkdir -p ~/fedforget/src/{federated,unlearning,models,data,utils}

echo ""
echo "=== 配置完成！ ==="
echo "结束时间: $(date)"
