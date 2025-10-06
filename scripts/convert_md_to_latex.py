#!/usr/bin/env python3
"""
Markdown转LaTeX转换脚本
自动化转换论文Markdown内容到LaTeX格式
"""

import re
from pathlib import Path

def clean_markdown_metadata(text):
    """移除Markdown元数据"""
    # 移除文件头部的中文元数据
    lines = text.split('\n')
    cleaned_lines = []
    skip_until_section = True

    for line in lines:
        if line.startswith('## ') and not any(ord(c) > 127 for c in line):
            skip_until_section = False
        if not skip_until_section:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

def convert_headers(text):
    """转换Markdown标题到LaTeX"""
    # ## -> \subsection
    text = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'\\subsection{\1}', text, flags=re.MULTILINE)
    # # 级别标题不转换,因为已经在主文件中定义
    text = re.sub(r'^# (.+)$', r'% SECTION: \1', text, flags=re.MULTILINE)

    return text

def convert_emphasis(text):
    """转换强调格式"""
    # **text** -> \textbf{text}
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    # *text* -> \textit{text}
    text = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'\\textit{\1}', text)

    return text

def convert_citations(text):
    """转换引用格式"""
    # [Author YEAR] -> \cite{key}
    # 简化处理: [XX] -> \cite{XX}
    text = re.sub(r'\[([A-Z][^\]]+?)\]', r'\\cite{\1}', text)

    return text

def convert_lists(text):
    """转换列表格式"""
    lines = text.split('\n')
    result = []
    in_itemize = False
    in_enumerate = False

    for i, line in enumerate(lines):
        # 检测无序列表
        if re.match(r'^\s*[-\*]\s+', line):
            if not in_itemize:
                result.append('\\begin{itemize}')
                in_itemize = True
            # 提取列表项内容
            item_text = re.sub(r'^\s*[-\*]\s+', '', line)
            result.append(f'  \\item {item_text}')
        # 检测有序列表
        elif re.match(r'^\s*\d+\.\s+', line):
            if not in_enumerate:
                result.append('\\begin{enumerate}')
                in_enumerate = True
            # 提取列表项内容
            item_text = re.sub(r'^\s*\d+\.\s+', '', line)
            result.append(f'  \\item {item_text}')
        else:
            # 结束列表
            if in_itemize:
                result.append('\\end{itemize}')
                in_itemize = False
            if in_enumerate:
                result.append('\\end{enumerate}')
                in_enumerate = False
            result.append(line)

    # 确保最后关闭列表
    if in_itemize:
        result.append('\\end{itemize}')
    if in_enumerate:
        result.append('\\end{enumerate}')

    return '\n'.join(result)

def convert_inline_code(text):
    """转换行内代码"""
    # `code` -> \texttt{code}
    text = re.sub(r'`([^`]+)`', r'\\texttt{\1}', text)
    return text

def protect_math(text):
    """保护数学公式"""
    # 数学公式已经是LaTeX格式,只需确保正确的$$分隔符
    # 这里不做修改,保持原样
    return text

def convert_special_chars(text):
    """转换特殊字符"""
    # & -> \&
    text = re.sub(r'&(?![\w#])', r'\\&', text)
    # % -> \%  (不在注释中)
    text = re.sub(r'%(?![^\n]*\\)', r'\\%', text)
    # # -> \# (非标题)
    # $ 保留用于数学
    return text

def remove_emoji(text):
    """移除emoji"""
    # 移除常见emoji符号
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\u2705"  # checkmark
        u"\u274C"  # cross mark
        u"\u2B50"  # star
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)

    # 移除特殊标记符号
    text = text.replace('⭐', '')
    text = text.replace('✅', '')
    text = text.replace('❌', '')
    text = text.replace('⚠️', '')
    text = text.replace('🔒', '')
    text = text.replace('🚀', '')
    text = text.replace('📊', '')
    text = text.replace('🎯', '')

    return text

def convert_section(markdown_file, output_file=None):
    """转换单个Markdown文件到LaTeX"""
    print(f"\n转换: {markdown_file.name}")

    with open(markdown_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # 清理元数据
    text = clean_markdown_metadata(text)

    # 移除emoji
    text = remove_emoji(text)

    # 应用转换
    text = convert_headers(text)
    text = convert_emphasis(text)
    text = convert_inline_code(text)
    text = convert_lists(text)
    text = protect_math(text)
    text = convert_special_chars(text)

    # 最后处理引用 (可能会误转换一些内容,需要手动调整)
    # text = convert_citations(text)

    # 保存或打印
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"  ✓ 已保存到: {output_file}")
    else:
        print(f"  (预览模式,未保存)")
        print(text[:500] + "...\n")

    return text

def main():
    """主函数"""
    print("="*80)
    print("Markdown → LaTeX 转换工具")
    print("="*80)

    sections = {
        'PAPER_INTRODUCTION_RELATEDWORK.md': 'latex/intro_relatedwork.tex',
        'PAPER_METHOD_SECTION.md': 'latex/method.tex',
        'PAPER_EXPERIMENTS_SECTION.md': 'latex/experiments.tex',
        'PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md': 'latex/discussion_conclusion.tex',
    }

    # 创建输出目录
    Path('latex').mkdir(exist_ok=True)

    print("\n选项:")
    print("  1. 转换所有章节并保存")
    print("  2. 预览单个章节 (不保存)")
    print("  3. 仅生成转换命令提示")

    choice = input("\n选择 [1/2/3] (默认=3): ").strip() or '3'

    if choice == '1':
        print("\n开始转换所有章节...")
        for md_file, tex_file in sections.items():
            if Path(md_file).exists():
                convert_section(Path(md_file), Path(tex_file))
            else:
                print(f"  ⚠️  文件不存在: {md_file}")

        print("\n" + "="*80)
        print("转换完成!")
        print("="*80)
        print("\n生成的文件:")
        for tex_file in sections.values():
            if Path(tex_file).exists():
                print(f"  ✓ {tex_file}")

        print("\n下一步:")
        print("  1. 手动检查latex/*.tex文件")
        print("  2. 将内容复制到paper_main.tex相应位置")
        print("  3. 调整引用格式 (\\cite{})")
        print("  4. 添加表格和图片")
        print("  5. 编译: pdflatex paper_main.tex")

    elif choice == '2':
        print("\n可用章节:")
        for i, md_file in enumerate(sections.keys(), 1):
            print(f"  {i}. {md_file}")

        file_choice = input(f"\n选择文件 [1-{len(sections)}]: ").strip()
        try:
            idx = int(file_choice) - 1
            md_file = list(sections.keys())[idx]
            convert_section(Path(md_file))
        except (ValueError, IndexError):
            print("无效选择")

    else:
        print("\n" + "="*80)
        print("手动转换指南")
        print("="*80)
        print("""
建议采用手动转换方式,以获得最佳效果:

【转换顺序】

1. ✅ Abstract: 已在paper_main.tex中
   - 直接从markdown复制
   - 调整引用格式

2. Introduction (Section 1)
   - 从PAPER_INTRODUCTION_RELATEDWORK.md复制Section 1内容
   - 替换##为\\subsection{}
   - 替换**text**为\\textbf{text}
   - 调整引用:[XX]→\\cite{XX}

3. Related Work (Section 2)
   - 从PAPER_INTRODUCTION_RELATEDWORK.md复制Section 2内容
   - 转换格式同上
   - 特别注意对比表格

4. Methodology (Section 3)
   - 从PAPER_METHOD_SECTION.md复制
   - ⚠️ 重点: 数学公式保持原样
   - 添加Algorithm 1 (使用algorithm环境)

5. Experiments (Section 4)
   - 从PAPER_EXPERIMENTS_SECTION.md复制
   - ⚠️ 重点: 添加Tables 1-5
   - 插入Figures 1-4

6. Discussion (Section 5)
   - 从PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md复制Section 5
   - 转换表格

7. Conclusion (Section 6)
   - 从PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md复制Section 6

【关键转换规则】

Markdown → LaTeX:
- ## Title → \\subsection{Title}
- ### Title → \\subsubsection{Title}
- **text** → \\textbf{text}
- *text* → \\textit{text}
- `code` → \\texttt{code}
- [Citation] → \\cite{key}
- - item → \\begin{itemize}\\item item\\end{itemize}

【数学公式】
- 保持原样: $$...$$, $...$
- 确保在equation或align环境中

【表格模板】
\\begin{table}[t]
\\centering
\\caption{Title}
\\label{tab:xxx}
\\begin{tabular}{lcccc}
\\toprule
... & ... & ... \\\\
\\midrule
... & ... & ... \\\\
\\bottomrule
\\end{tabular}
\\end{table}

【图片插入】
\\begin{figure}[t]
\\centering
\\includegraphics[width=0.9\\linewidth]{figures/figureX.pdf}
\\caption{Caption text}
\\label{fig:xxx}
\\end{figure}

【预计时间】
- Manual conversion: 4-6 hours
- Careful, but higher quality
        """)

    print("="*80 + "\n")

if __name__ == "__main__":
    main()
