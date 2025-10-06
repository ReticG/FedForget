#!/usr/bin/env python3
"""
完整论文逻辑一致性检查脚本

检查项目:
1. 数值一致性 (不同章节引用的数据是否一致)
2. 交叉引用完整性 (Section/Table/Figure引用)
3. 术语一致性 (确保全文使用标准术语)
4. 叙述逻辑流 (Introduction → Method → Experiments → Conclusion)
5. 引用文献覆盖 (确保所有引用都在references.bib中)
"""

import re
from pathlib import Path
from collections import defaultdict

# 关键数值定义 (ground truth from experiments)
GROUND_TRUTH = {
    '5_clients': {
        'retrain': {
            'test_acc': '67.92',
            'retention': '93.96',
            'forgetting': '32.68',
            'asr': '46.74',
            'time': '116.11'
        },
        'finetune': {
            'test_acc': '70.99',
            'retention': '98.22',
            'forgetting': '15.70',
            'asr': '51.14',
            'time': '57.36'
        },
        'fedforget': {
            'test_acc': '69.81',
            'retention': '96.57',
            'forgetting': '20.01',
            'asr': '52.91',
            'time': '76.15'
        }
    },
    '10_clients': {
        'fedforget': {
            'test_acc': '68.93',
            'retention': '98.66',
            'forgetting': '13.02',
            'asr': '50.23'
        }
    },
    'ablation': {
        'full': {'test_acc': '71.85', 'retention': '101.07', 'forgetting': '11.38'},
        'no_weight': {'retention': '100.86'},
        'no_distillation': {'retention': '14.10'},
        'single_teacher': {'retention': '89.53'}
    }
}

# 关键术语标准
STANDARD_TERMS = {
    'forgetting client': 'forgetting client',  # NOT "target client"
    'remaining clients': 'remaining clients',  # NOT "other clients"
    'Teacher A': 'Teacher A',  # capitalized
    'Teacher B': 'Teacher B',  # capitalized
    'FedForget': 'FedForget',  # NOT "Fed-Forget" or "fedforget"
}

# 需要的交叉引用
REQUIRED_REFERENCES = {
    'PAPER_INTRODUCTION_RELATEDWORK.md': {
        'sections': ['Section 2', 'Section 3', 'Section 4'],
        'tables': [],
        'figures': []
    },
    'PAPER_METHOD_SECTION.md': {
        'sections': ['Section 4.2', 'Section 4.3'],
        'tables': ['Table 2'],
        'figures': ['Figure 4']
    },
    'PAPER_EXPERIMENTS_SECTION.md': {
        'sections': ['Section 3'],
        'tables': ['Table 1', 'Table 2', 'Table 3', 'Table 4', 'Table 5'],
        'figures': ['Figure 1', 'Figure 2', 'Figure 3', 'Figure 4']
    },
    'PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md': {
        'sections': ['Section 4', 'Section 5'],
        'tables': [],
        'figures': []
    }
}


def check_numerical_consistency(files):
    """检查数值一致性"""
    print("\n" + "="*80)
    print("1. 数值一致性检查")
    print("="*80)

    issues = []

    # 提取所有文件中的关键数值
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查5 clients FedForget结果
        patterns = {
            'retention_96.57': r'96\.57',
            'forgetting_20.01': r'20\.01',
            'asr_52.91': r'52\.91',
            'retention_improvement_11.54': r'\+11\.54',
            'retention_improvement_2.09': r'\+2\.09',
        }

        for name, pattern in patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                print(f"  ✓ {filepath.name}: 发现 {name} ({len(matches)}次)")

    # 检查是否有不一致的数值
    inconsistent_patterns = [
        (r'96\.\d{2}', '96.57', 'Retention (5 clients)', ['96.02']),  # 96.02 is for α=0.1
        (r'20\.\d{2}', '20.01', 'Forgetting (5 clients)', []),
        (r'52\.\d{2}', '52.91', 'ASR (5 clients)', []),
    ]

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        for pattern, correct_value, desc, exceptions in inconsistent_patterns:
            matches = re.findall(pattern, content)
            incorrect = [m for m in matches if m != correct_value and m not in exceptions]
            if incorrect:
                issues.append(f"⚠️  {filepath.name}: {desc} - 发现非标准值 {incorrect}")

    if issues:
        print("\n发现不一致:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n  ✅ 所有关键数值一致!")

    return len(issues)


def check_cross_references(files):
    """检查交叉引用完整性"""
    print("\n" + "="*80)
    print("2. 交叉引用完整性检查")
    print("="*80)

    issues = []

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        filename = filepath.name
        if filename not in REQUIRED_REFERENCES:
            continue

        print(f"\n检查 {filename}:")

        required = REQUIRED_REFERENCES[filename]

        # 检查Section引用
        for section_ref in required['sections']:
            if section_ref in content:
                print(f"  ✓ 引用 {section_ref}")
            else:
                issues.append(f"  ⚠️  {filename}: 缺失引用 {section_ref}")

        # 检查Table引用
        for table_ref in required['tables']:
            if table_ref in content:
                print(f"  ✓ 引用 {table_ref}")
            else:
                issues.append(f"  ⚠️  {filename}: 缺失引用 {table_ref}")

        # 检查Figure引用
        for figure_ref in required['figures']:
            # 允许 "Figure 1" 或 "figure1" 或 "Fig. 1"
            pattern = re.compile(rf'(?:Figure|Fig\.|figure)\s*{figure_ref.split()[1]}', re.IGNORECASE)
            if pattern.search(content):
                print(f"  ✓ 引用 {figure_ref}")
            else:
                issues.append(f"  ⚠️  {filename}: 缺失引用 {figure_ref}")

    if issues:
        print("\n发现缺失引用:")
        for issue in issues:
            print(issue)
    else:
        print("\n  ✅ 所有交叉引用完整!")

    return len(issues)


def check_terminology_consistency(files):
    """检查术语一致性"""
    print("\n" + "="*80)
    print("3. 术语一致性检查")
    print("="*80)

    issues = []

    # 检查过时术语
    deprecated_terms = {
        r'\btarget client\b': 'forgetting client',
        r'\bother clients\b': 'remaining clients',
        r'\bteacher A\b': 'Teacher A',
        r'\bteacher B\b': 'Teacher B',
    }

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        for pattern, correct_term in deprecated_terms.items():
            matches = list(re.finditer(pattern, content))
            if matches:
                issues.append(f"  ⚠️  {filepath.name}: 发现过时术语 '{pattern}' (应为 '{correct_term}') - {len(matches)}处")

    if issues:
        print("\n发现术语不一致:")
        for issue in issues:
            print(issue)
    else:
        print("\n  ✅ 所有术语一致!")

    return len(issues)


def check_narrative_flow(files):
    """检查叙述逻辑流"""
    print("\n" + "="*80)
    print("4. 叙述逻辑流检查")
    print("="*80)

    # 读取所有章节
    sections = {}
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            sections[filepath.name] = f.read()

    # 检查关键claim在各章节的一致性
    key_claims = {
        'dual_teacher_contribution': {
            'claim': 'dual-teacher contributes +11.54% retention',
            'should_appear_in': ['PAPER_INTRODUCTION_RELATEDWORK.md',
                                 'PAPER_METHOD_SECTION.md',
                                 'PAPER_EXPERIMENTS_SECTION.md',
                                 'PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md']
        },
        'scalability_improvement': {
            'claim': '10 clients perform better: +2.09% retention',
            'should_appear_in': ['PAPER_INTRODUCTION_RELATEDWORK.md',
                                 'PAPER_EXPERIMENTS_SECTION.md',
                                 'PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md']
        },
        'privacy_ideal': {
            'claim': 'ASR≈50% (ideal privacy)',
            'should_appear_in': ['PAPER_INTRODUCTION_RELATEDWORK.md',
                                 'PAPER_EXPERIMENTS_SECTION.md',
                                 'PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md']
        }
    }

    issues = []

    for claim_name, claim_info in key_claims.items():
        print(f"\n检查关键声明: {claim_info['claim']}")
        for filename in claim_info['should_appear_in']:
            # 简化检查: 寻找关键数字
            if claim_name == 'dual_teacher_contribution':
                found = '11.54' in sections[filename]
            elif claim_name == 'scalability_improvement':
                found = '2.09' in sections[filename]
            elif claim_name == 'privacy_ideal':
                found = re.search(r'ASR.*50', sections[filename]) is not None
            else:
                found = False

            if found:
                print(f"  ✓ {filename}: 提及此声明")
            else:
                issues.append(f"  ⚠️  {filename}: 未提及 '{claim_info['claim']}'")

    if issues:
        print("\n发现叙述流缺失:")
        for issue in issues:
            print(issue)
    else:
        print("\n  ✅ 关键声明在各章节一致!")

    return len(issues)


def check_citation_coverage():
    """检查引用覆盖"""
    print("\n" + "="*80)
    print("5. 引用文献覆盖检查")
    print("="*80)

    # 读取references.bib
    bib_path = Path('references.bib')
    if not bib_path.exists():
        print("  ⚠️  references.bib 不存在!")
        return 1

    with open(bib_path, 'r', encoding='utf-8') as f:
        bib_content = f.read()

    # 提取BibTeX条目
    bib_keys = re.findall(r'@\w+\{([^,]+),', bib_content)
    print(f"\n发现 {len(bib_keys)} 个BibTeX条目")

    # 关键引用检查 (使用更灵活的匹配)
    critical_citations = [
        ('mcmahan', 'McMahan FedAvg'),
        ('ferrari', 'Ferrari NeurIPS 2024'),
        ('wu2023', 'Wu KNOT ICLR 2023'),
        ('liu2021', 'Liu FedEraser'),
        ('bourtoule', 'Bourtoule SISA'),
        ('hinton', 'Hinton KD')
    ]

    issues = []
    for citation_pattern, citation_name in critical_citations:
        if any(citation_pattern in key.lower() for key in bib_keys):
            print(f"  ✓ 包含关键引用: {citation_name}")
        else:
            issues.append(f"  ⚠️  缺失关键引用: {citation_name}")

    if issues:
        print("\n发现缺失引用:")
        for issue in issues:
            print(issue)
    else:
        print("\n  ✅ 所有关键引用都在references.bib中!")

    return len(issues)


def generate_report(total_issues):
    """生成总结报告"""
    print("\n" + "="*80)
    print("总结报告")
    print("="*80)

    if total_issues == 0:
        print("\n✅ 论文逻辑一致性检查通过!")
        print("   所有数值、引用、术语和叙述流均一致。")
        print("\n下一步: 可以进行语法检查和句式优化")
    else:
        print(f"\n⚠️  发现 {total_issues} 个问题需要修复")
        print("\n建议:")
        print("  1. 修复上述问题")
        print("  2. 重新运行此脚本验证")
        print("  3. 然后进行语法检查")

    print("="*80 + "\n")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("FedForget 论文完整逻辑一致性检查")
    print("="*80)

    # 待检查的文件
    files_to_check = [
        Path("PAPER_INTRODUCTION_RELATEDWORK.md"),
        Path("PAPER_METHOD_SECTION.md"),
        Path("PAPER_EXPERIMENTS_SECTION.md"),
        Path("PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md"),
    ]

    # 检查文件是否存在
    missing = [f for f in files_to_check if not f.exists()]
    if missing:
        print(f"\n⚠️  缺失文件: {missing}")
        return

    total_issues = 0

    # 1. 数值一致性
    total_issues += check_numerical_consistency(files_to_check)

    # 2. 交叉引用
    total_issues += check_cross_references(files_to_check)

    # 3. 术语一致性
    total_issues += check_terminology_consistency(files_to_check)

    # 4. 叙述逻辑流
    total_issues += check_narrative_flow(files_to_check)

    # 5. 引用覆盖
    total_issues += check_citation_coverage()

    # 生成报告
    generate_report(total_issues)


if __name__ == "__main__":
    main()
