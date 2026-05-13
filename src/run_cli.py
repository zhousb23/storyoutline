# -*- coding: utf-8 -*-
"""命令行集成测试 — 完整走通「导入 → 拆分 → 分析 → 导出」流程。

用法:
    python -m src.run_cli <文件路径> [--api-key KEY] [--step1-only] [--output-dir DIR]
"""

import argparse
import os
import sys

# Windows 终端 UTF-8 支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="StoryOutline 命令行测试")
    parser.add_argument("file", help="文章文件路径 (.txt/.docx/.pdf)")
    parser.add_argument("--api-key", help="DeepSeek API Key（也可通过 DEEPSEEK_KEY 环境变量传入）")
    parser.add_argument("--step1-only", action="store_true", help="仅执行第一步（章节大纲）")
    parser.add_argument("--section-size", type=int, default=5, help="每阶段章节数（测试用默认5）")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    args = parser.parse_args()

    # API Key 优先级：命令行 > 环境变量
    api_key = args.api_key or os.environ.get("DEEPSEEK_KEY")
    if not api_key:
        print("请通过 --api-key 参数或 DEEPSEEK_KEY 环境变量提供 API Key")
        sys.exit(1)

    # 导入项目根到路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.file_parser import parse_file
    from src.chapter_splitter import split_chapters
    from src.deepseek_client import DeepSeekClient
    from src.analysis_pipeline import AnalysisPipeline
    from src.result_manager import ProjectState, ResultManager

    # 1. 解析文件
    print(f"\n{'=' * 50}")
    print(f"  解析文件: {args.file}")
    print(f"{'=' * 50}")
    text = parse_file(args.file)
    print(f"  文本长度: {len(text):,} 字符")

    # 2. 拆分章节
    print(f"\n{'=' * 50}")
    print(f"  拆分章节")
    print(f"{'=' * 50}")
    split_result = split_chapters(text)
    print(f"  章节数: {split_result.total_chapters}")
    print(f"  匹配模式: {split_result.pattern_used}")
    for ch in split_result.chapters[:10]:
        print(f"    第{ch.index}章: {ch.title} ({len(ch.content)}字)")
    if split_result.total_chapters > 10:
        print(f"    ... 共{split_result.total_chapters}章")

    # 3. 初始化项目
    project_name = os.path.splitext(os.path.basename(args.file))[0]
    output_dir = os.path.join(args.output_dir, f"{project_name}.storyoutline")
    os.makedirs(output_dir, exist_ok=True)

    chapters = [
        {
            "index": ch.index,
            "title": ch.title,
            "content": ch.content,
            "status": "pending",
        }
        for ch in split_result.chapters
    ]

    state = ProjectState(
        name=project_name,
        source_file=os.path.abspath(args.file),
        chapters=chapters,
        section_size=args.section_size,
    )

    manager = ResultManager(output_dir)
    client = DeepSeekClient(api_key=api_key)
    pipeline = AnalysisPipeline(
        client=client,
        manager=manager,
        state=state,
        section_size=args.section_size,
    )

    # 4. 运行分析
    print(f"\n{'=' * 50}")
    print(f"  开始分析")
    print(f"{'=' * 50}")
    pipeline.run()

    # 5. 显示结果
    print(f"\n{'=' * 50}")
    print(f"  分析结果")
    print(f"{'=' * 50}")

    step1 = manager.load_step1_results()
    print(f"\n第一步（章节大纲）: {len(step1)} 章已分析")
    for r in step1[:3]:
        print(f"  第{r['chapter_index']}章 {r['chapter_title']}")
        print(f"    激励事件: {r['inciting_incident'][:60]}...")
        print(f"    危机: {r['crisis'][:60]}...")
        print(f"    高潮: {r['climax'][:60]}...")
    if len(step1) > 3:
        print(f"  ... 共{len(step1)}章")

    step2 = manager.load_step2_results()
    print(f"\n第二步（阶段总结）: {len(step2)} 个阶段")
    for s in step2:
        print(f"  阶段{s['section_index']}: 第{s['chapter_range'][0]}-{s['chapter_range'][1]}章")

    step3 = manager.load_step3_result()
    if step3:
        print(f"\n第三步（全书故事线）:")
        print(f"  {step3['overall_storyline'][:200]}...")

    # 6. 导出
    docx_path = os.path.join(output_dir, f"{project_name}_大纲分析.docx")
    manager.export_to_docx(docx_path, project_name)
    print(f"\n导出 Word: {docx_path}")

    txt_path = os.path.join(output_dir, f"{project_name}_大纲分析.txt")
    manager.export_to_txt(txt_path, project_name)
    print(f"导出 TXT: {txt_path}")

    print(f"\n{'=' * 50}")
    print(f"  全部完成！输出目录: {output_dir}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
