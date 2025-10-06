#!/usr/bin/env python3
"""
论文语法检查与句式优化指南

由于无法直接调用Grammarly API,此脚本提供:
1. 常见语法问题自动检测
2. 学术写作风格检查
3. 冗余表达识别
4. 被动语态检测
5. 句子长度分析
"""

import re
from pathlib import Path
from collections import defaultdict

# 常见语法问题模式
GRAMMAR_PATTERNS = {
    'a_vs_an': [
        (r'\ba ([aeiou])', r'an \1', 'Use "an" before vowel sounds'),
        (r'\ban ([^aeiou])', r'a \1', 'Use "a" before consonant sounds'),
    ],
    'subject_verb_agreement': [
        (r'\b(data|criteria|phenomena) is\b', r'\1 are', 'Plural subject needs "are"'),
        (r'\b(datum|criterion|phenomenon) are\b', r'\1 is', 'Singular subject needs "is"'),
    ],
    'redundant_phrases': [
        (r'\bvery unique\b', 'unique', '"unique" already means "one of a kind"'),
        (r'\bmore optimal\b', 'optimal', '"optimal" already means "best"'),
        (r'\bmore superior\b', 'superior', '"superior" already means "better"'),
        (r'\bin order to\b', 'to', 'Often "to" alone is sufficient'),
        (r'\bdue to the fact that\b', 'because', 'More concise'),
        (r'\bat this point in time\b', 'now', 'More concise'),
    ],
    'wordy_constructions': [
        (r'\bmake use of\b', 'use', 'Simpler'),
        (r'\bgive consideration to\b', 'consider', 'Simpler'),
        (r'\btake into account\b', 'consider', 'Simpler'),
        (r'\bby means of\b', 'by', 'Simpler'),
        (r'\bfor the purpose of\b', 'for', 'Simpler'),
    ],
}

# 学术写作风格问题
STYLE_PATTERNS = {
    'contractions': [
        (r"\bdon't\b", "do not", "Avoid contractions in academic writing"),
        (r"\bcan't\b", "cannot", "Avoid contractions"),
        (r"\bwon't\b", "will not", "Avoid contractions"),
        (r"\bwe're\b", "we are", "Avoid contractions"),
        (r"\bit's\b", "it is", "Avoid contractions (or use 'its' for possessive)"),
    ],
    'informal_language': [
        (r'\ba lot of\b', 'many/much', 'Too informal'),
        (r'\bkinda\b', 'somewhat', 'Too informal'),
        (r'\bgonna\b', 'going to', 'Too informal'),
        (r'\bstuff\b', 'things/items', 'Too informal'),
        (r'\bget\b', 'obtain/achieve/receive', 'Often too informal'),
    ],
    'vague_qualifiers': [
        (r'\bvery\b', '[consider removing or be specific]', 'Often unnecessary'),
        (r'\breally\b', '[consider removing]', 'Often adds little meaning'),
        (r'\bquite\b', '[be specific]', 'Vague quantifier'),
        (r'\bsomewhat\b', '[be specific]', 'Vague quantifier'),
    ],
}

# 被动语态检测 (简化版)
PASSIVE_VOICE_PATTERNS = [
    r'\bis (being )?([\w]+ed|shown|made|given|obtained|achieved)\b',
    r'\bare (being )?([\w]+ed|shown|made|given|obtained|achieved)\b',
    r'\bwas (being )?([\w]+ed|shown|made|given|obtained|achieved)\b',
    r'\bwere (being )?([\w]+ed|shown|made|given|obtained|achieved)\b',
    r'\bhas been ([\w]+ed|shown|made|given|obtained|achieved)\b',
    r'\bhave been ([\w]+ed|shown|made|given|obtained|achieved)\b',
]

def check_sentence_length(text):
    """检查句子长度"""
    sentences = re.split(r'[.!?]+', text)
    long_sentences = []

    for i, sent in enumerate(sentences):
        words = len(sent.split())
        if words > 40:
            long_sentences.append({
                'sentence': sent.strip()[:100] + '...',
                'words': words,
                'recommendation': 'Consider breaking into multiple sentences'
            })

    return long_sentences

def check_passive_voice(text):
    """检测被动语态"""
    passive_instances = []

    for pattern in PASSIVE_VOICE_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end]

            passive_instances.append({
                'phrase': match.group(),
                'context': context,
                'recommendation': 'Consider active voice if possible'
            })

    return passive_instances

def check_grammar_and_style(text, filename):
    """检查语法和风格"""
    issues = defaultdict(list)

    # 语法检查
    for category, patterns in GRAMMAR_PATTERNS.items():
        for pattern, replacement, explanation in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues[category].append({
                    'original': match.group(),
                    'suggested': replacement,
                    'explanation': explanation,
                    'position': match.start()
                })

    # 风格检查
    for category, patterns in STYLE_PATTERNS.items():
        for pattern, replacement, explanation in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues[category].append({
                    'original': match.group(),
                    'suggested': replacement,
                    'explanation': explanation,
                    'position': match.start()
                })

    return issues

def analyze_file(filepath):
    """分析单个文件"""
    print(f"\n{'='*80}")
    print(f"分析文件: {filepath.name}")
    print('='*80)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 只分析英文内容 (排除代码块和中文部分)
    # 简化: 提取## 标题之后的段落
    english_sections = []
    lines = content.split('\n')
    in_english_section = False

    for line in lines:
        if line.startswith('## ') and not any(ord(c) > 127 for c in line):
            in_english_section = True
        elif line.startswith('## ') and any(ord(c) > 127 for c in line):
            in_english_section = False
        elif in_english_section and line.strip() and not line.startswith('```'):
            english_sections.append(line)

    english_text = ' '.join(english_sections)

    # 语法和风格检查
    issues = check_grammar_and_style(english_text, filepath.name)

    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        print("  ✅ 未发现常见语法/风格问题")
    else:
        print(f"\n发现 {total_issues} 个潜在问题:\n")

        for category, problem_list in issues.items():
            if problem_list:
                print(f"\n【{category.upper()}】({len(problem_list)}处)")
                for i, problem in enumerate(problem_list[:3], 1):  # 只显示前3个
                    print(f"  {i}. '{problem['original']}' → '{problem['suggested']}'")
                    print(f"     说明: {problem['explanation']}")
                if len(problem_list) > 3:
                    print(f"  ... 还有 {len(problem_list) - 3} 处类似问题")

    # 句子长度检查
    long_sentences = check_sentence_length(english_text)
    if long_sentences:
        print(f"\n【LONG SENTENCES】({len(long_sentences)}处)")
        for i, sent_info in enumerate(long_sentences[:3], 1):
            print(f"  {i}. {sent_info['words']} words: {sent_info['sentence']}")
            print(f"     {sent_info['recommendation']}")
        if len(long_sentences) > 3:
            print(f"  ... 还有 {len(long_sentences) - 3} 个长句")

    # 被动语态检查 (抽样)
    passive_instances = check_passive_voice(english_text)
    if len(passive_instances) > 10:
        print(f"\n【PASSIVE VOICE】(发现 {len(passive_instances)}处)")
        print(f"  提示: 学术写作中被动语态可接受,但主动语态通常更清晰")
        print(f"  建议: 检查是否可以改为主动语态以增强可读性")

    return {
        'grammar_style_issues': total_issues,
        'long_sentences': len(long_sentences),
        'passive_voice': len(passive_instances)
    }

def generate_optimization_suggestions():
    """生成优化建议"""
    print(f"\n{'='*80}")
    print("语法优化通用建议")
    print('='*80)

    suggestions = """
【学术写作最佳实践】

1. **清晰性优先**
   - 优先使用主动语态 (We propose... vs. It is proposed...)
   - 避免冗长句子 (理想长度: 15-25词)
   - 使用具体术语而非模糊限定词

2. **一致性**
   - 时态一致 (Introduction: present tense, Method: past tense)
   - 术语一致 (已通过检查 ✅)
   - 引用格式一致

3. **简洁性**
   - 删除冗余词汇 ("in order to" → "to")
   - 避免名词化 ("conduct an analysis" → "analyze")
   - 删除无意义的限定词 ("very", "really")

4. **专业性**
   - 避免口语化表达 ("a lot of" → "many")
   - 避免缩写 ("don't" → "do not")
   - 使用领域标准术语

5. **逻辑流畅性**
   - 使用过渡词连接句子 (However, Moreover, Therefore)
   - 段落主题句明确
   - 每段聚焦单一观点

【推荐工具】

1. **Grammarly** (付费版)
   - 实时语法检查
   - 学术写作模式
   - 句式优化建议

2. **QuillBot** (免费/付费)
   - Paraphrasing tool
   - Grammar checker
   - 句式变化建议

3. **ChatGPT/Claude** (AI辅助)
   - 逐段润色
   - 提供改写建议
   - 解释语法规则

【手动检查清单】

□ 所有句子主谓宾清晰
□ 没有悬垂修饰语
□ 代词指代明确 (this/that/it 指代清楚)
□ 平行结构正确 (A, B, and C 格式一致)
□ 标点符号正确 (逗号、分号使用规范)
□ 引用格式统一
□ 首字母缩写首次使用时定义
□ 数字格式一致 (何时用阿拉伯数字,何时拼写)
"""

    print(suggestions)

def main():
    """主函数"""
    print("\n" + "="*80)
    print("FedForget 论文语法与风格检查")
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

    results = {}

    # 分析每个文件
    for filepath in files_to_check:
        results[filepath.name] = analyze_file(filepath)

    # 总结
    print(f"\n{'='*80}")
    print("检查总结")
    print('='*80)

    total_grammar = sum(r['grammar_style_issues'] for r in results.values())
    total_long = sum(r['long_sentences'] for r in results.values())
    total_passive = sum(r['passive_voice'] for r in results.values())

    print(f"\n发现问题统计:")
    print(f"  语法/风格问题: {total_grammar}处")
    print(f"  长句 (>40词): {total_long}处")
    print(f"  被动语态: {total_passive}处")

    print(f"\n详细结果:")
    for filename, stats in results.items():
        print(f"  {filename}:")
        print(f"    - 语法/风格: {stats['grammar_style_issues']}")
        print(f"    - 长句: {stats['long_sentences']}")
        print(f"    - 被动语态: {stats['passive_voice']}")

    # 生成建议
    generate_optimization_suggestions()

    print("\n" + "="*80)
    print("下一步行动:")
    print("="*80)
    print("""
1. ✅ 已完成基础语法检查 (自动化)

2. 📝 推荐手动操作:
   a) 使用Grammarly/QuillBot检查4个章节
   b) 逐段复制到AI工具 (ChatGPT/Claude) 进行润色
   c) 重点关注:
      - Introduction (吸引读者)
      - Abstract (简洁有力)
      - Conclusion (强调贡献)

3. ⏭️  完成语法检查后:
   - 运行一致性检查确认未引入新问题
   - 进入LaTeX转换阶段

预计时间: 2-3小时人工润色
    """)
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
