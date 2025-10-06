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
