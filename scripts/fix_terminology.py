"""
术语统一修正脚本
根据TERMINOLOGY_GUIDE.md中的标准,批量修正术语
"""

import re
from pathlib import Path
import shutil

# 术语替换规则 (精确匹配,避免误替换)
REPLACEMENTS = [
    # 1. Target client -> forgetting client
    (r'\btarget client\b', 'forgetting client'),

    # 2. Teacher A/B 大小写统一
    (r'\bteacher A\b', 'Teacher A'),
    (r'\bTeacher a\b', 'Teacher A'),
    (r'\bteacher B\b', 'Teacher B'),
    (r'\bTeacher b\b', 'Teacher B'),

    # 3. Global/local teacher -> Teacher A/B (仅在特定上下文)
    # 注意: 这个需要手动检查,因为有些地方用"global teacher"是合适的
    # (r'\bthe global teacher\b', 'Teacher A'),
    # (r'\bthe local teacher\b', 'Teacher B'),

    # 4. Other clients -> remaining clients
    (r'\bother clients\b', 'remaining clients'),

    # 5. FedForget大小写
    # 注意: 需要小心,避免替换代码中的变量名
]

# 需要手动检查的替换 (标记但不自动替换)
MANUAL_REVIEW = [
    (r'\bglobal teacher\b', 'Teacher A (需人工确认)'),
    (r'\blocal teacher\b', 'Teacher B (需人工确认)'),
]


def create_backup(filepath):
    """创建备份文件"""
    backup_path = filepath.with_suffix(filepath.suffix + '.backup')
    shutil.copy2(filepath, backup_path)
    return backup_path


def fix_file(filepath, dry_run=True):
    """修正单个文件"""
    print(f"\n{'='*60}")
    print(f"处理文件: {filepath.name}")
    print('='*60)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # 应用替换规则
    for pattern, replacement in REPLACEMENTS:
        matches = list(re.finditer(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            changes_made.append(f"  ✓ 替换 '{pattern}' -> '{replacement}' ({len(matches)}处)")
            print(f"  ✓ 替换: '{pattern}' -> '{replacement}' ({len(matches)}处)")

    # 检查需要手动review的内容
    manual_items = []
    for pattern, note in MANUAL_REVIEW:
        matches = list(re.finditer(pattern, content))
        if matches:
            manual_items.append(f"  ⚠️  发现: '{pattern}' - {note} ({len(matches)}处)")
            print(f"  ⚠️  发现: '{pattern}' - {note} ({len(matches)}处)")

    # 统计
    if changes_made:
        print(f"\n总计: {len(changes_made)}类替换")
    else:
        print("\n  ✅ 无需替换")

    if manual_items:
        print(f"\n需人工检查: {len(manual_items)}项")

    # 保存结果
    if not dry_run and content != original_content:
        backup_path = create_backup(filepath)
        print(f"\n  💾 备份已保存: {backup_path.name}")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 文件已更新: {filepath.name}")

    return {
        'file': filepath.name,
        'changes': len(changes_made),
        'manual_reviews': len(manual_items),
        'modified': content != original_content
    }


def generate_report(results):
    """生成总结报告"""
    print("\n" + "="*60)
    print("总结报告")
    print("="*60)

    total_changes = sum(r['changes'] for r in results)
    total_manual = sum(r['manual_reviews'] for r in results)
    modified_files = sum(1 for r in results if r['modified'])

    print(f"\n处理文件: {len(results)}个")
    print(f"修改文件: {modified_files}个")
    print(f"总替换数: {total_changes}类")
    print(f"需人工检查: {total_manual}项")

    print("\n详细统计:")
    for r in results:
        if r['changes'] > 0 or r['manual_reviews'] > 0:
            status = "✓ 已修改" if r['modified'] else "○ 无变化"
            print(f"  {status} {r['file']}: {r['changes']}替换, {r['manual_reviews']}待检查")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("FedForget 术语统一修正工具")
    print("="*60)

    # 要处理的文件
    files_to_fix = [
        "PAPER_INTRODUCTION_RELATEDWORK.md",
        "PAPER_METHOD_SECTION.md",
        "PAPER_EXPERIMENTS_SECTION.md",
        "PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md",
    ]

    # 询问是否dry run
    print("\n模式选择:")
    print("  1. Dry run (仅显示,不修改文件)")
    print("  2. 实际修改 (会创建备份)")

    # 默认dry run模式
    dry_run = True
    choice = input("\n请选择模式 [1/2] (默认=1): ").strip()

    if choice == '2':
        dry_run = False
        print("\n⚠️  将实际修改文件 (会自动备份)")
        confirm = input("确认继续? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
    else:
        print("\n✓ Dry run 模式 (不会修改文件)")

    results = []

    for filename in files_to_fix:
        filepath = Path(filename)
        if filepath.exists():
            result = fix_file(filepath, dry_run=dry_run)
            results.append(result)
        else:
            print(f"\n⚠️  文件不存在: {filename}")

    generate_report(results)

    print("\n" + "="*60)
    if dry_run:
        print("Dry run 完成! (未修改任何文件)")
        print("\n要实际修改文件,请重新运行并选择模式2")
    else:
        print("修正完成!")
        print("\n备份文件已保存 (*.backup)")
        print("请人工检查标记为'需人工确认'的内容")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
