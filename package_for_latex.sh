#!/bin/bash

# FedForget LaTeX编译包打包脚本
# 创建一个包含所有必需文件的压缩包，可直接用于Overleaf或本地编译

echo "======================================"
echo "FedForget LaTeX编译包打包工具"
echo "======================================"
echo ""

# 设置输出目录
OUTPUT_DIR="fedforget_latex_package"
ARCHIVE_NAME="fedforget_latex_package.tar.gz"

# 创建输出目录
echo "📁 创建打包目录..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/figures"
mkdir -p "$OUTPUT_DIR/source_markdown"
mkdir -p "$OUTPUT_DIR/guides"

# 复制核心LaTeX文件
echo ""
echo "📄 复制核心LaTeX文件..."
cp paper_main.tex "$OUTPUT_DIR/" 2>/dev/null || echo "⚠️  paper_main.tex 不存在"
cp references.bib "$OUTPUT_DIR/" 2>/dev/null || echo "⚠️  references.bib 不存在"

# 复制图表 (PDF优先)
echo ""
echo "🎨 复制图表文件..."
cp figures/*.pdf "$OUTPUT_DIR/figures/" 2>/dev/null && echo "  ✅ PDF图表已复制" || echo "  ⚠️  未找到PDF图表"
cp figures/*.png "$OUTPUT_DIR/figures/" 2>/dev/null && echo "  ✅ PNG图表已复制" || echo "  ⚠️  未找到PNG图表"

# 复制Markdown源文件 (供参考)
echo ""
echo "📝 复制Markdown源文件..."
cp PAPER_INTRODUCTION_RELATEDWORK.md "$OUTPUT_DIR/source_markdown/" 2>/dev/null || echo "  ⚠️  Introduction未找到"
cp PAPER_METHOD_SECTION.md "$OUTPUT_DIR/source_markdown/" 2>/dev/null || echo "  ⚠️  Method未找到"
cp PAPER_EXPERIMENTS_SECTION.md "$OUTPUT_DIR/source_markdown/" 2>/dev/null || echo "  ⚠️  Experiments未找到"
cp PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md "$OUTPUT_DIR/source_markdown/" 2>/dev/null || echo "  ⚠️  Abstract/Discussion/Conclusion未找到"

# 复制指南文档
echo ""
echo "📚 复制指南文档..."
cp LATEX_COMPILATION_GUIDE.md "$OUTPUT_DIR/guides/" 2>/dev/null || echo "  ⚠️  编译指南未找到"
cp PAPER_QUICK_REFERENCE.md "$OUTPUT_DIR/guides/" 2>/dev/null || echo "  ⚠️  速查表未找到"
cp PAPER_READY_FOR_LATEX.md "$OUTPUT_DIR/guides/" 2>/dev/null || echo "  ⚠️  LaTeX准备指南未找到"

# 创建README
echo ""
echo "📋 创建README..."
cat > "$OUTPUT_DIR/README.md" << 'EOF'
# FedForget LaTeX编译包 📦

**包含内容**: 所有LaTeX编译所需文件
**使用环境**: Overleaf (推荐) 或 本地TeXLive

---

## 📁 目录结构

```
fedforget_latex_package/
├── paper_main.tex                    # LaTeX主文件 (框架)
├── references.bib                    # BibTeX文献 (35篇)
├── figures/                          # 图表文件
│   ├── figure1_main_results.pdf
│   ├── figure2_ablation_study.pdf
│   ├── figure3_scalability.pdf
│   └── figure4_dynamic_weights.pdf
├── source_markdown/                  # Markdown源文件 (供参考)
│   ├── PAPER_INTRODUCTION_RELATEDWORK.md
│   ├── PAPER_METHOD_SECTION.md
│   ├── PAPER_EXPERIMENTS_SECTION.md
│   └── PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md
├── guides/                           # 编译指南
│   ├── LATEX_COMPILATION_GUIDE.md   # 完整编译指南 ⭐
│   ├── PAPER_QUICK_REFERENCE.md     # 关键数据速查
│   └── PAPER_READY_FOR_LATEX.md     # LaTeX准备说明
└── README.md                         # 本文件
```

---

## 🚀 快速开始

### 方法1: 使用Overleaf (推荐)

1. 访问 https://www.overleaf.com/
2. 创建新项目: New Project → Upload Project
3. 上传本压缩包或以下文件:
   - `paper_main.tex`
   - `references.bib`
   - `figures/` 目录下所有文件
4. 按照 `guides/LATEX_COMPILATION_GUIDE.md` 填充内容
5. 点击 "Recompile" 生成PDF

### 方法2: 本地编译

**前置条件**: 安装TeXLive

```bash
# 解压本包
tar -xzf fedforget_latex_package.tar.gz
cd fedforget_latex_package

# 编译 (需要手动填充内容后)
pdflatex paper_main.tex
bibtex paper_main
pdflatex paper_main.tex
pdflatex paper_main.tex
```

---

## 📝 下一步工作

### 1. 填充内容 (6-8小时)

参考 `source_markdown/` 中的文件，将内容转换为LaTeX格式并填充到 `paper_main.tex`

**转换规则** 见 `guides/LATEX_COMPILATION_GUIDE.md`

**填充顺序**:
1. Introduction (Section 1) - 从 `PAPER_INTRODUCTION_RELATEDWORK.md`
2. Related Work (Section 2) - 从 `PAPER_INTRODUCTION_RELATEDWORK.md`
3. Methodology (Section 3) - 从 `PAPER_METHOD_SECTION.md`
4. Experiments (Section 4) - 从 `PAPER_EXPERIMENTS_SECTION.md`
5. Discussion (Section 5) - 从 `PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md`
6. Conclusion (Section 6) - 从 `PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md`

### 2. 编译PDF (2-3小时)

- 首次编译
- 修复错误
- 调整格式
- 最终校对

### 3. 提交准备 (1-2小时)

- 生成最终PDF
- 准备Supplementary Materials
- 撰写Cover Letter

---

## 📊 关键数据速查

**Main Results (5 Clients, CIFAR-10)**:
- FedForget: Retention=96.57±1.21%, ASR=52.91±2.32%
- Retrain: Retention=93.96±2.33%, ASR=46.74±2.26%

**Ablation Study**:
- Dual-teacher: +11.54% retention vs single-teacher

**Scalability (10 Clients)**:
- +2.09% retention improvement vs 5 clients
- ASR=50.23% (closest to ideal 50%)

**完整数据** 见 `guides/PAPER_QUICK_REFERENCE.md`

---

## 📚 重要文档

1. **LATEX_COMPILATION_GUIDE.md** ⭐⭐⭐⭐⭐
   - 完整的编译指南
   - Markdown→LaTeX转换规则
   - 常见问题解决
   - 编译检查清单

2. **PAPER_QUICK_REFERENCE.md** ⭐⭐⭐⭐
   - 所有关键数据
   - 实验结果表格
   - 核心claims

3. **PAPER_READY_FOR_LATEX.md** ⭐⭐⭐
   - LaTeX准备说明
   - 表格模板
   - 公式清单

---

## ✅ 文件检查清单

- [x] `paper_main.tex` - LaTeX主文件
- [x] `references.bib` - 35篇文献
- [x] `figures/figure1_main_results.pdf` - 主实验结果
- [x] `figures/figure2_ablation_study.pdf` - 消融实验
- [x] `figures/figure3_scalability.pdf` - 可扩展性
- [x] `figures/figure4_dynamic_weights.pdf` - 动态权重
- [x] 4个Markdown源文件 (12,200词)
- [x] 3个指南文档

---

## 🎯 预期时间线

- **Day 1** (4-6h): 填充Introduction, Related Work, Methodology
- **Day 2** (4-6h): 填充Experiments, Discussion, Conclusion
- **Day 3** (2-4h): 格式调整, 编译, 校对

**总计**: 10-16小时 → 完成可提交的PDF! 🎉

---

## 📧 问题反馈

如有问题，请参考:
- `guides/LATEX_COMPILATION_GUIDE.md` (完整指南)
- Overleaf文档: https://www.overleaf.com/learn
- LaTeX Stack Exchange: https://tex.stackexchange.com/

---

**状态**: ✅ 所有材料已准备完毕
**下一步**: 在Overleaf或本地环境开始填充内容
**目标**: ICML 2025 / NeurIPS 2025 提交! 🚀

祝编译顺利！📝✨
EOF

# 创建Overleaf使用说明
cat > "$OUTPUT_DIR/OVERLEAF_INSTRUCTIONS.md" << 'EOF'
# Overleaf使用说明 (超简单版) 🎨

## 步骤1: 创建项目 (2分钟)

1. 访问 https://www.overleaf.com/
2. 注册/登录账号
3. 点击 **"New Project"** → **"Upload Project"**
4. 上传 `fedforget_latex_package.zip` (或手动上传文件)

## 步骤2: 上传文件 (3分钟)

**必需文件**:
- ✅ `paper_main.tex`
- ✅ `references.bib`
- ✅ `figures/` 文件夹下所有PDF文件

**可选文件** (供参考):
- `source_markdown/` 下的Markdown文件
- `guides/` 下的指南文档

## 步骤3: 填充内容 (6-8小时)

打开 `paper_main.tex`，找到以下位置并填充内容:

### 3.1 Introduction
```latex
\section{Introduction}
% TODO: 从 PAPER_INTRODUCTION_RELATEDWORK.md 的 "1. Introduction" 部分复制内容
% 转换规则见 LATEX_COMPILATION_GUIDE.md
```

### 3.2 Related Work
```latex
\section{Related Work}
% TODO: 从 PAPER_INTRODUCTION_RELATEDWORK.md 的 "2. Related Work" 部分复制内容
```

### 3.3 Methodology
```latex
\section{Methodology}
% TODO: 从 PAPER_METHOD_SECTION.md 复制内容
% 数学公式已经是LaTeX格式，可直接使用
```

### 3.4 Experiments
```latex
\section{Experiments}
% TODO: 从 PAPER_EXPERIMENTS_SECTION.md 复制内容
% 表格需要转换为LaTeX格式 (见LATEX_COMPILATION_GUIDE.md)
```

### 3.5 Discussion
```latex
\section{Discussion}
% TODO: 从 PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md 的 Discussion 部分复制内容
```

### 3.6 Conclusion
```latex
\section{Conclusion}
% TODO: 从 PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md 的 Conclusion 部分复制内容
```

## 步骤4: 编译PDF (5分钟)

1. 点击页面顶部的 **"Recompile"** 按钮
2. 查看右侧PDF预览
3. 如有错误，根据左下角错误提示修复
4. 重复编译直到无错误

## 步骤5: 下载PDF (1分钟)

1. 点击右上角的 **"Download PDF"** 按钮
2. 保存为 `fedforget_paper.pdf`
3. 恭喜！可提交的论文完成！🎉

---

## 🔧 快速转换技巧

### 引用转换
```
Markdown: [McMahan et al., 2017]
LaTeX:    \cite{mcmahan2017communication}
```

### 强调转换
```
Markdown: **bold**
LaTeX:    \textbf{bold}
```

### 列表转换
```
Markdown:          LaTeX:
- Item 1           \begin{itemize}
- Item 2           \item Item 1
                   \item Item 2
                   \end{itemize}
```

**详细规则** 见 `LATEX_COMPILATION_GUIDE.md`

---

## ⚠️ 常见错误

### 错误1: "Undefined control sequence"
**解决**: 检查LaTeX命令拼写，确保包已导入

### 错误2: 引用显示 [?]
**解决**: 点击 "Recompile" 多次 (2-3次)

### 错误3: 图片不显示
**解决**: 确认 `figures/` 文件夹和图片已上传

---

## 📞 需要帮助?

参考 `LATEX_COMPILATION_GUIDE.md` 获取完整指南！

**预计完成时间**: 1-2天 (每天4-6小时)
**祝编译顺利！** 🚀📝
EOF

# 统计文件
echo ""
echo "📊 打包统计..."
LATEX_FILES=$(find "$OUTPUT_DIR" -name "*.tex" | wc -l)
BIB_FILES=$(find "$OUTPUT_DIR" -name "*.bib" | wc -l)
PDF_FILES=$(find "$OUTPUT_DIR" -name "*.pdf" | wc -l)
PNG_FILES=$(find "$OUTPUT_DIR" -name "*.png" | wc -l)
MD_FILES=$(find "$OUTPUT_DIR" -name "*.md" | wc -l)

echo "  LaTeX文件: $LATEX_FILES"
echo "  BibTeX文件: $BIB_FILES"
echo "  PDF图表: $PDF_FILES"
echo "  PNG图表: $PNG_FILES"
echo "  文档文件: $MD_FILES"

# 创建压缩包
echo ""
echo "📦 创建压缩包..."
tar -czf "$ARCHIVE_NAME" "$OUTPUT_DIR"

# 显示结果
echo ""
echo "======================================"
echo "✅ 打包完成!"
echo "======================================"
echo ""
echo "📦 压缩包: $ARCHIVE_NAME"
echo "📁 目录: $OUTPUT_DIR/"
echo ""

# 显示大小
PACKAGE_SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
DIR_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)

echo "💾 大小:"
echo "  压缩包: $PACKAGE_SIZE"
echo "  解压后: $DIR_SIZE"
echo ""

echo "📋 使用说明:"
echo "  1. 解压: tar -xzf $ARCHIVE_NAME"
echo "  2. 查看: cd $OUTPUT_DIR && cat README.md"
echo "  3. Overleaf: 上传压缩包或手动上传文件"
echo "  4. 本地编译: 见 guides/LATEX_COMPILATION_GUIDE.md"
echo ""

echo "🎯 下一步:"
echo "  1. 上传到Overleaf或复制到本地LaTeX环境"
echo "  2. 填充内容 (6-8小时)"
echo "  3. 编译PDF (2-3小时)"
echo "  4. 提交ICML/NeurIPS 2025! 🚀"
echo ""

echo "✅ 完成! 所有文件已打包到: $ARCHIVE_NAME"
