"""
论文一致性检查脚本
检查术语使用、引用格式、拼写等
"""

import re
from pathlib import Path
from collections import defaultdict

# 定义标准术语
STANDARD_TERMS = {
    # 正确 -> 可能的错误变体
    "forgetting client": ["target client", "unlearning client", "forget client"],
    "remaining clients": ["retain clients", "other clients"],
    "Teacher A": ["teacher A", "Teacher a", "global teacher"],
    "Teacher B": ["teacher B", "Teacher b", "local teacher"],
    "FedForget": ["Fedforget", "Fed-Forget", "fedforget"],
    "knowledge distillation": ["Knowledge Distillation", "KD"],
    "retention": ["Retention"],
    "forgetting rate": ["Forgetting Rate", "forgetting"],
    "Test Accuracy": ["test accuracy", "Test Acc"],
    "Attack Success Rate": ["attack success rate", "ASR"],
}

# 需要大写的专有名词
PROPER_NOUNS = [
    "CIFAR-10",
    "ResNet-18",
    "GDPR",
    "CCPA",
    "FedAvg",
    "FedProx",
    "SimpleMIA",
    "Non-IID",
]

# 常见拼写错误
COMMON_TYPOS = {
    "seperately": "separately",
    "occured": "occurred",
    "neccessary": "necessary",
    "sucessful": "successful",
    "acheive": "achieve",
    "recieve": "receive",
    "benifit": "benefit",
}


def check_file(filepath):
    """检查单个文件"""
    print(f"\n{'='*60}")
    print(f"检查文件: {filepath.name}")
    print('='*60)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # 1. 检查术语一致性
    print("\n1. 术语一致性检查:")
    for standard, variants in STANDARD_TERMS.items():
        for variant in variants:
            if variant.lower() in content.lower():
                matches = re.findall(rf'\b{re.escape(variant)}\b', content, re.IGNORECASE)
                if matches:
                    issues.append(f"  ⚠️  发现变体: '{variant}' (应使用 '{standard}')")
                    print(f"  ⚠️  发现变体: '{variant}' → 应使用 '{standard}' ({len(matches)}次)")

    # 2. 检查常见拼写错误
    print("\n2. 拼写检查:")
    typos_found = False
    for wrong, correct in COMMON_TYPOS.items():
        if wrong in content:
            count = content.count(wrong)
            issues.append(f"  ❌ 拼写错误: '{wrong}' (正确: '{correct}')")
            print(f"  ❌ 拼写错误: '{wrong}' → 应为 '{correct}' ({count}次)")
            typos_found = True
    if not typos_found:
        print("  ✅ 未发现常见拼写错误")

    # 3. 检查数字一致性
    print("\n3. 数字一致性检查:")
    # 检查关键指标是否一致
    key_numbers = {
        "20.01": "Forgetting rate (5 clients)",
        "96.57": "Retention (5 clients)",
        "52.91": "ASR (5 clients)",
        "11.54": "Dual-teacher improvement",
        "3,500": "Experiments section words",
        "2,800": "Method section words",
    }

    for number, description in key_numbers.items():
        if number in content:
            print(f"  ✅ 发现关键数字: {number} ({description})")

    # 4. 检查引用格式
    print("\n4. 引用格式检查:")
    # 查找可能的引用
    citations = re.findall(r'\[([^\]]+)\]', content)
    citation_issues = []
    for cite in citations:
        # 检查是否是年份引用 (应该用\cite{})
        if re.match(r'^\d{4}', cite):
            citation_issues.append(f"  ⚠️  可能需要转换为\\cite{{}}: [{cite}]")

    if citation_issues:
        for issue in citation_issues[:5]:  # 只显示前5个
            print(issue)
        if len(citation_issues) > 5:
            print(f"  ... 还有 {len(citation_issues) - 5} 个类似问题")
    else:
        print("  ✅ 引用格式基本正常")

    # 5. 检查章节引用
    print("\n5. 章节引用检查:")
    section_refs = re.findall(r'Section (\d+\.?\d*)', content)
    if section_refs:
        print(f"  ℹ️  发现 {len(section_refs)} 个章节引用: {set(section_refs)}")

    # 6. 检查Table/Figure引用
    print("\n6. Table/Figure引用检查:")
    table_refs = re.findall(r'Table (\d+)', content)
    figure_refs = re.findall(r'Figure (\d+)', content)
    if table_refs:
        print(f"  ℹ️  发现 {len(table_refs)} 个Table引用: {set(table_refs)}")
    if figure_refs:
        print(f"  ℹ️  发现 {len(figure_refs)} 个Figure引用: {set(figure_refs)}")

    return issues


def generate_summary_report(all_issues):
    """生成总结报告"""
    print("\n" + "="*60)
    print("总结报告")
    print("="*60)

    if all_issues:
        print(f"\n发现 {len(all_issues)} 个需要注意的问题:")
        for issue in all_issues[:10]:  # 显示前10个
            print(issue)
        if len(all_issues) > 10:
            print(f"\n... 还有 {len(all_issues) - 10} 个问题")
    else:
        print("\n✅ 未发现明显问题")

    print("\n建议:")
    print("1. 统一使用标准术语 (如 'forgetting client' 而非 'target client')")
    print("2. 确保数字一致性 (关键指标在全文中应一致)")
    print("3. 检查引用格式 (使用\\cite{}命令)")
    print("4. 验证章节/表格/图表引用编号")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("FedForget 论文一致性检查")
    print("="*60)

    # 要检查的文件
    files_to_check = [
        "PAPER_INTRODUCTION_RELATEDWORK.md",
        "PAPER_METHOD_SECTION.md",
        "PAPER_EXPERIMENTS_SECTION.md",
        "PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md",
    ]

    all_issues = []

    for filename in files_to_check:
        filepath = Path(filename)
        if filepath.exists():
            issues = check_file(filepath)
            all_issues.extend(issues)
        else:
            print(f"\n⚠️  文件不存在: {filename}")

    generate_summary_report(all_issues)

    print("\n" + "="*60)
    print("检查完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
