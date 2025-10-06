"""
Non-IID鲁棒性可视化 - 4图综合展示
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 设置样式
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.grid'] = True

# 读取数据
df = pd.read_csv('results/noniid_robustness.csv')

# 创建4子图
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FedForget Non-IID Robustness Analysis (CIFAR-10)',
             fontsize=16, fontweight='bold')

# 1. 遗忘率 vs Alpha
ax1 = axes[0, 0]
for method in ['Retrain', 'Fine-tuning', 'FedForget']:
    data = df[df['Method'] == method]
    ax1.plot(data['Alpha'], data['Forgetting'],
             marker='o', linewidth=2, markersize=8, label=method)

ax1.set_xlabel('Dirichlet Alpha (Non-IID Degree)', fontsize=12)
ax1.set_ylabel('Forgetting Rate (%)', fontsize=12)
ax1.set_title('(a) Forgetting Effectiveness vs Data Distribution', fontsize=13, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='Target: 30%')

# 2. 保持率 vs Alpha
ax2 = axes[0, 1]
for method in ['Retrain', 'Fine-tuning', 'FedForget']:
    data = df[df['Method'] == method]
    ax2.plot(data['Alpha'], data['Retention'],
             marker='s', linewidth=2, markersize=8, label=method)

ax2.set_xlabel('Dirichlet Alpha', fontsize=12)
ax2.set_ylabel('Retention Rate (%)', fontsize=12)
ax2.set_title('(b) Model Performance Retention', fontsize=13, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.axhline(y=95, color='green', linestyle='--', alpha=0.5, label='Target: >95%')

# 3. 隐私保护 (ASR距离50%) vs Alpha
ax3 = axes[1, 0]
for method in ['Retrain', 'Fine-tuning', 'FedForget']:
    data = df[df['Method'] == method]
    privacy_score = np.abs(data['ASR'] - 50.0)  # 距离50%越近隐私越好
    ax3.plot(data['Alpha'], privacy_score,
             marker='^', linewidth=2, markersize=8, label=method)

ax3.set_xlabel('Dirichlet Alpha', fontsize=12)
ax3.set_ylabel('Privacy Leakage (|ASR - 50%|)', fontsize=12)
ax3.set_title('(c) Privacy Protection (Lower is Better)', fontsize=13, fontweight='bold')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.axhline(y=5, color='green', linestyle='--', alpha=0.5, label='Excellent: <5%')

# 4. 综合评分散点图
ax4 = axes[1, 1]
methods = ['Retrain', 'Fine-tuning', 'FedForget']
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
markers = ['o', 's', '^']

for method, color, marker in zip(methods, colors, markers):
    data = df[df['Method'] == method]
    # X轴: 遗忘效果 (Forgetting)
    # Y轴: 综合分数 = Retention - |ASR-50|
    composite_score = data['Retention'] - np.abs(data['ASR'] - 50.0)

    ax4.scatter(data['Forgetting'], composite_score,
               s=200, c=[color], marker=marker, label=method, alpha=0.7, edgecolors='black')

    # 添加alpha标签
    for idx, row in data.iterrows():
        score = row['Retention'] - np.abs(row['ASR'] - 50.0)
        ax4.annotate(f'α={row["Alpha"]:.1f}',
                    (row['Forgetting'], score),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)

ax4.set_xlabel('Forgetting Rate (%)', fontsize=12)
ax4.set_ylabel('Quality Score (Retention - Privacy Leak)', fontsize=12)
ax4.set_title('(d) Overall Performance Trade-off', fontsize=13, fontweight='bold')
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/noniid_robustness_analysis.png', dpi=300, bbox_inches='tight')
print("✅ 已生成: results/noniid_robustness_analysis.png")

# 生成热力图
fig2, axes2 = plt.subplots(1, 3, figsize=(16, 5))
fig2.suptitle('Non-IID Robustness Heatmap', fontsize=14, fontweight='bold')

metrics = ['Forgetting', 'Retention', 'ASR']
titles = ['(a) Forgetting Rate (%)', '(b) Retention Rate (%)', '(c) ASR (%)']

for idx, (metric, title) in enumerate(zip(metrics, titles)):
    pivot = df.pivot(index='Method', columns='Alpha', values=metric)

    if metric == 'ASR':
        # ASR: 越接近50越好
        cmap = 'RdYlGn_r'
        center = 50
    elif metric == 'Retention':
        # Retention: 越高越好
        cmap = 'RdYlGn'
        center = None
    else:
        # Forgetting: 越高越好
        cmap = 'RdYlGn'
        center = None

    im = axes2[idx].imshow(pivot, cmap=cmap, aspect='auto')

    # 添加数值标注
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            text = axes2[idx].text(j, i, f'{pivot.iloc[i, j]:.1f}',
                                 ha="center", va="center", color="black", fontsize=10)

    # 设置刻度
    axes2[idx].set_xticks(range(len(pivot.columns)))
    axes2[idx].set_xticklabels(pivot.columns)
    axes2[idx].set_yticks(range(len(pivot.index)))
    axes2[idx].set_yticklabels(pivot.index)

    axes2[idx].set_title(title, fontsize=12, fontweight='bold')
    axes2[idx].set_xlabel('Dirichlet Alpha', fontsize=11)
    axes2[idx].set_ylabel('Method', fontsize=11)

    plt.colorbar(im, ax=axes2[idx], label=metric)

plt.tight_layout()
plt.savefig('results/noniid_heatmap.png', dpi=300, bbox_inches='tight')
print("✅ 已生成: results/noniid_heatmap.png")

# 打印关键发现
print("\n" + "="*60)
print("📊 Non-IID鲁棒性关键发现")
print("="*60)

for alpha in sorted(df['Alpha'].unique()):
    print(f"\n🔹 Alpha = {alpha} ({'极端Non-IID' if alpha==0.1 else '中度Non-IID' if alpha==0.5 else '接近IID' if alpha==1.0 else 'Non-IID'}):")
    alpha_data = df[df['Alpha'] == alpha]

    for idx, row in alpha_data.iterrows():
        privacy_leak = abs(row['ASR'] - 50.0)
        quality_score = row['Retention'] - privacy_leak

        print(f"  {row['Method']:12s}: "
              f"遗忘={row['Forgetting']:5.1f}%, "
              f"保持={row['Retention']:5.1f}%, "
              f"ASR={row['ASR']:5.1f}%, "
              f"隐私泄露={privacy_leak:4.1f}%, "
              f"综合={quality_score:5.1f}")

    # 找最佳方法
    best_privacy = alpha_data.loc[(alpha_data['ASR'] - 50.0).abs().idxmin()]
    best_forgetting = alpha_data.loc[alpha_data['Forgetting'].idxmax()]

    print(f"  ⭐ 最优隐私: {best_privacy['Method']} (ASR={best_privacy['ASR']:.1f}%)")
    print(f"  ⭐ 最强遗忘: {best_forgetting['Method']} (遗忘率={best_forgetting['Forgetting']:.1f}%)")

print("\n" + "="*60)
print("✅ 可视化完成")
print("="*60)
