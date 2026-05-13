# -*- coding: utf-8 -*-
"""文件解析功能验证脚本。

测试 TXT / DOCX / PDF 三种格式的读取能力。
用法：
    python check_parser.py <文件路径>
"""

import os
import sys

# Windows 终端 UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check_txt(filepath: str) -> str | None:
    """解析 TXT 文件，返回文本内容。"""
    import chardet

    with open(filepath, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8")
    confidence = detected.get("confidence", 0)
    print(f"  编码检测: {encoding} (置信度: {confidence:.0%})")
    return raw.decode(encoding, errors="replace")


def check_docx(filepath: str) -> str:
    """解析 DOCX 文件，返回合并后的文本。"""
    from docx import Document

    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    print(f"  段落数: {len(paragraphs)}")
    return "\n".join(paragraphs)


def check_pdf(filepath: str) -> str:
    """解析 PDF 文件，返回合并后的文本。"""
    import pdfplumber

    with pdfplumber.open(filepath) as pdf:
        pages_text = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
        print(f"  总页数: {len(pdf.pages)}，有效文本页: {len(pages_text)}")
        return "\n".join(pages_text)


def print_preview(text: str, lines: int = 5):
    """打印文本预览。"""
    preview_lines = text.split("\n")[:lines]
    for line in preview_lines:
        display = line[:100] + ("..." if len(line) > 100 else "")
        print(f"  | {display}")
    if len(text.split("\n")) > lines:
        print(f"  ... 共 {len(text.splitlines())} 行")


def main():
    if len(sys.argv) < 2:
        print("用法: python check_parser.py <文件路径>")
        print("支持格式: .txt, .docx, .pdf")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    ext = os.path.splitext(filepath)[1].lower()
    print(f"\n文件: {filepath}")
    print(f"格式: {ext}  |  大小: {os.path.getsize(filepath):,} 字节")

    parsers = {".txt": check_txt, ".docx": check_docx, ".pdf": check_pdf}
    if ext not in parsers:
        print(f"不支持的格式: {ext}，支持: {', '.join(parsers)}")
        sys.exit(1)

    try:
        text = parsers[ext](filepath)
    except Exception as e:
        print(f"解析失败: {e}")
        sys.exit(1)

    char_count = len(text)
    print(f"  总字符数: {char_count:,}")
    print("  内容预览:")
    print_preview(text)
    print(f"\n[OK] {ext} 解析成功！")


if __name__ == "__main__":
    main()
