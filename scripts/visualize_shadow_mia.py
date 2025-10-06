"""
可视化Shadow Model Attack vs SimpleMIA对比结果
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 设置绘图风格
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['legend.fontsize'] = 12
plt.rcParams['figure.titlesize'] = 18

# 读取结果
df = pd.DataFrame(pd.read_csv('/home/featurize/work/GJC/fedforget/results/shadow_mia_evaluation.csv'))

# 创建图表
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Shadow Model Attack vs SimpleMIA对比分析', fontsize=20, fontweight='bold')

# 1. ASR对比 (左上)
ax1 = axes[0, 0]
x = np.arange(len(df))
width = 0.35

bars1 = ax1.bar(x - width/2, df['Shadow_ASR'], width, label='Shadow MIA', color='#FF6B6B', alpha=0.8)
bars2 = ax1.bar(x + width/2, df['Simple_ASR'], width, label='SimpleMIA', color='#4ECDC4', alpha=0.8)

# 添加理想线 (50%)
ax1.axhline(y=50, color='gray', linestyle='--', linewidth=2, label='理想值 (50%)')

ax1.set_xlabel('方法')
ax1.set_ylabel('ASR (%)')
ax1.set_title('攻击成功率 (ASR) 对比\n越接近50%越好')
ax1.set_xticks(x)
ax1.set_xticklabels(df['Method'], rotation=15, ha='right')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# 在柱子上添加数值
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=10)

# 2. AUC对比 (右上)
ax2 = axes[0, 1]
bars3 = ax2.bar(x - width/2, df['Shadow_AUC'], width, label='Shadow MIA', color='#FF6B6B', alpha=0.8)
bars4 = ax2.bar(x + width/2, df['Simple_AUC'], width, label='SimpleMIA', color='#4ECDC4', alpha=0.8)

# 添加理想线 (0.5)
ax2.axhline(y=0.5, color='gray', linestyle='--', linewidth=2, label='理想值 (0.5)')

ax2.set_xlabel('方法')
ax2.set_ylabel('AUC')
ax2.set_title('ROC AUC对比\n越接近0.5越好')
ax2.set_xticks(x)
ax2.set_xticklabels(df['Method'], rotation=15, ha='right')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# 添加数值
for bars in [bars3, bars4]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}',
                ha='center', va='bottom', fontsize=10)

# 3. 距离50%的差距 (左下)
ax3 = axes[1, 0]
df['Shadow_Distance'] = abs(df['Shadow_ASR'] - 50)
df['Simple_Distance'] = abs(df['Simple_ASR'] - 50)

bars5 = ax3.bar(x - width/2, df['Shadow_Distance'], width, label='Shadow MIA', color='#FF6B6B', alpha=0.8)
bars6 = ax3.bar(x + width/2, df['Simple_Distance'], width, label='SimpleMIA', color='#4ECDC4', alpha=0.8)

ax3.set_xlabel('方法')
ax3.set_ylabel('距离50%的差距 (%)')
ax3.set_title('隐私保护效果\n差距越小越好')
ax3.set_xticks(x)
ax3.set_xticklabels(df['Method'], rotation=15, ha='right')
ax3.legend()
ax3.grid(axis='y', alpha=0.3)

# 添加数值
for bars in [bars5, bars6]:
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=10)

# 4. 测试准确率vs隐私保护散点图 (右下)
ax4 = axes[1, 1]

# Shadow MIA
ax4.scatter(df['Shadow_Distance'], df['Test_Acc'], s=200, c='#FF6B6B',
           alpha=0.6, edgecolors='black', linewidth=2, label='Shadow MIA', marker='o')

# SimpleMIA
ax4.scatter(df['Simple_Distance'], df['Test_Acc'], s=200, c='#4ECDC4',
           alpha=0.6, edgecolors='black', linewidth=2, label='SimpleMIA', marker='s')

# 添加方法标签
for i, method in enumerate(df['Method']):
    # Shadow MIA位置
    ax4.annotate(method,
                (df['Shadow_Distance'].iloc[i], df['Test_Acc'].iloc[i]),
                xytext=(5, 5), textcoords='offset points', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', fc='#FF6B6B', alpha=0.3))
    # SimpleMIA位置 (稍微偏移以避免重叠)
    ax4.annotate(method,
                (df['Simple_Distance'].iloc[i], df['Test_Acc'].iloc[i]),
                xytext=(5, -15), textcoords='offset points', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', fc='#4ECDC4', alpha=0.3))

ax4.set_xlabel('距离50%的差距 (%) → 更好的隐私')
ax4.set_ylabel('测试准确率 (%)')
ax4.set_title('准确率 vs 隐私保护权衡\n左上角为最优')
ax4.legend(loc='lower right')
ax4.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('/home/featurize/work/GJC/fedforget/results/shadow_mia_comparison.png',
            dpi=300, bbox_inches='tight')
print("可视化已保存到: results/shadow_mia_comparison.png")

# 打印分析总结
print(f"\n{'='*60}")
print("Shadow Model Attack vs SimpleMIA 对比分析")
print(f"{'='*60}\n")

print("1. 攻击强度对比:")
print("-" * 60)
for _, row in df.iterrows():
    print(f"{row['Method']:15s} | Shadow ASR: {row['Shadow_ASR']:5.2f}% | Simple ASR: {row['Simple_ASR']:5.2f}%")

print(f"\n2. 隐私保护排名 (Shadow MIA):")
print("-" * 60)
df_sorted_shadow = df.sort_values('Shadow_Distance')
for i, (_, row) in enumerate(df_sorted_shadow.iterrows(), 1):
    print(f"{i}. {row['Method']:15s} | 距离50%: {row['Shadow_Distance']:5.2f}% | ASR: {row['Shadow_ASR']:5.2f}%")

print(f"\n3. 隐私保护排名 (SimpleMIA):")
print("-" * 60)
df_sorted_simple = df.sort_values('Simple_Distance')
for i, (_, row) in enumerate(df_sorted_simple.iterrows(), 1):
    print(f"{i}. {row['Method']:15s} | 距离50%: {row['Simple_Distance']:5.2f}% | ASR: {row['Simple_ASR']:5.2f}%")

print(f"\n4. 关键发现:")
print("-" * 60)

# 找出两种方法都认为最好的
shadow_best = df_sorted_shadow.iloc[0]
simple_best = df_sorted_simple.iloc[0]

if shadow_best['Method'] == simple_best['Method']:
    print(f"✓ 两种MIA方法一致认为 {shadow_best['Method']} 隐私保护最优")
else:
    print(f"✗ 两种方法结论不一致:")
    print(f"  - Shadow MIA认为: {shadow_best['Method']} 最优")
    print(f"  - SimpleMIA认为: {simple_best['Method']} 最优")

# FedForget分析
fedforget_row = df[df['Method'] == 'FedForget'].iloc[0]
print(f"\n5. FedForget性能:")
print("-" * 60)
print(f"测试准确率: {fedforget_row['Test_Acc']:.2f}%")
print(f"Shadow MIA:")
print(f"  - ASR: {fedforget_row['Shadow_ASR']:.2f}% (距离50%: {fedforget_row['Shadow_Distance']:.2f}%)")
print(f"  - AUC: {fedforget_row['Shadow_AUC']:.4f}")
print(f"SimpleMIA:")
print(f"  - ASR: {fedforget_row['Simple_ASR']:.2f}% (距离50%: {fedforget_row['Simple_Distance']:.2f}%)")
print(f"  - AUC: {fedforget_row['Simple_AUC']:.4f}")

print(f"\n{'='*60}\n")
