#!/bin/bash

# 清理无用文件脚本
echo "======================================"
echo "清理FedForget项目无用文件"
echo "======================================"
echo ""

# 要保留的核心文件
KEEP_FILES=(
    "README.md"
    "PAPER_INTRODUCTION_RELATEDWORK.md"
    "PAPER_METHOD_SECTION.md"
    "PAPER_EXPERIMENTS_SECTION.md"
    "PAPER_ABSTRACT_DISCUSSION_CONCLUSION.md"
    "PAPER_QUICK_REFERENCE.md"
    "TERMINOLOGY_GUIDE.md"
    "PROJECT_FINAL_STATUS.md"
    "LATEX_COMPILATION_GUIDE.md"
    "paper_main.tex"
    "references.bib"
)

# 要删除的临时文档类别
echo "🗑️  删除临时状态文档..."
rm -f QUICK_STATUS.md
rm -f STATUS_*.md
rm -f MORNING_UPDATE.md
rm -f PROGRESS_UPDATE.md
rm -f TODAY_PLAN.md
echo "  ✅ 临时状态文档已删除"

echo ""
echo "🗑️  删除过时的实验文档..."
rm -f STRATEGIC_ASSESSMENT.md
rm -f RESOURCE_DECISION.md
rm -f COMPLETE_EXPERIMENT_ROADMAP.md
rm -f EXPERIMENT_SETUP.md
rm -f experiment.md
rm -f spec.md
echo "  ✅ 过时实验文档已删除"

echo ""
echo "🗑️  删除重复的总结文档..."
rm -f CLEANUP_SUMMARY.md
rm -f PAPER_COMPLETE_SUMMARY.md
rm -f WEEK1_COMPLETION.md
rm -f FIGURES_GENERATED.md
rm -f HIGH_FORGETTING_ANALYSIS.md
echo "  ✅ 重复总结文档已删除"

echo ""
echo "🗑️  删除中间结果文档..."
rm -f REPRODUCIBILITY_RESULTS.md
rm -f ABLATION_RESULTS.md
rm -f 10CLIENTS_RESULTS.md
echo "  ✅ 中间结果文档已删除"

echo ""
echo "🗑️  删除推送相关临时文档..."
rm -f PUSH_SUCCESS.md
rm -f PUSH_TO_GITHUB.md
rm -f GITHUB_SYNC_GUIDE.md
rm -f 如何推送.md
rm -f push_to_github.sh
echo "  ✅ 推送相关文档已删除"

echo ""
echo "🗑️  删除LaTeX准备过程文档..."
rm -f LATEX_CONVERSION_PROGRESS.md
rm -f PAPER_READY_FOR_LATEX.md
rm -f 继续推进完成报告.md
echo "  ✅ LaTeX准备文档已删除"

echo ""
echo "🗑️  删除其他临时文件..."
rm -f FINAL_STATUS.md
rm -f PROJECT_COMPLETION_SUMMARY.md
echo "  ✅ 其他临时文件已删除"

echo ""
echo "🗑️  删除打包目录和临时编译包..."
rm -rf fedforget_latex_package/
rm -f fedforget_latex_package.tar.gz
echo "  ✅ 打包文件已删除"

echo ""
echo "======================================"
echo "✅ 清理完成!"
echo "======================================"
echo ""
echo "📁 保留的核心文件:"
echo "  - README.md"
echo "  - 4个论文Markdown文件"
echo "  - paper_main.tex + references.bib"
echo "  - figures/ 目录"
echo "  - scripts/ 目录"
echo "  - results/ 目录"
echo "  - 核心代码文件"
echo ""
echo "🎯 项目现在更整洁了！"
