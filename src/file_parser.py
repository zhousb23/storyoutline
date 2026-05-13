# -*- coding: utf-8 -*-
"""文件解析模块 — 支持 TXT / DOCX / PDF / EPUB 格式的文本提取。"""

import os

import chardet


def detect_encoding(filepath: str) -> str:
    """检测文本文件编码，返回编码名称。"""
    with open(filepath, "rb") as f:
        raw = f.read(100 * 1024)
    result = chardet.detect(raw)
    encoding = result.get("encoding", "utf-8")
    if encoding and "gb" in encoding.lower():
        encoding = "gbk"
    return encoding or "utf-8"


def parse_txt(filepath: str) -> str:
    """解析 TXT 纯文本文件。"""
    encoding = detect_encoding(filepath)
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        return f.read()


def parse_docx(filepath: str) -> str:
    """解析 Word 文档。"""
    from docx import Document

    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_pdf(filepath: str) -> str:
    """解析 PDF 文件。"""
    import pdfplumber

    pages_text = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return "\n".join(pages_text)


def parse_epub(filepath: str) -> str:
    """解析 EPUB 电子书，提取所有章节文本。"""
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(filepath)
    chapters = []

    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT = 9 (html 文档)
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            if text:
                chapters.append(text)

    return "\n\n".join(chapters)


def parse_file(filepath: str) -> str:
    """统一文件解析入口。支持 .txt / .docx / .pdf / .epub"""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    parsers = {
        ".txt": parse_txt,
        ".docx": parse_docx,
        ".pdf": parse_pdf,
        ".epub": parse_epub,
    }

    if ext not in parsers:
        supported = ", ".join(parsers.keys())
        raise ValueError(f"不支持的文件格式: {ext}，支持: {supported}")

    return parsers[ext](filepath)
