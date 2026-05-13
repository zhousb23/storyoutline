# -*- coding: utf-8 -*-
"""章节拆分模块 — 自动识别章节标记，拆分全文为章节列表。

支持内置正则模式 + 用户自定义模式。
"""

import re
from dataclasses import dataclass, field


# 内置章节匹配模式（按优先级排序）
DEFAULT_PATTERNS: list[str] = [
    # 行首中文数字章（第一章、第十回、第二十卷）
    r"^\s*第[一二三四五六七八九十百千万零]+[章节回卷]",
    # 行首阿拉伯数字章（第1章、第 12 回）
    r"^\s*第\s*[0-9０-９]+\s*[章节回卷]",
    # 行首英文 Chapter
    r"^\s*[Cc]hapter\s+[0-9]+",
]


@dataclass
class Chapter:
    """章节数据结构。"""

    index: int  # 从 1 开始的序号
    title: str  # 章节标题（匹配到的标记行）
    content: str  # 章节正文
    start_pos: int = 0  # 在原文本中的起始位置


@dataclass
class SplitResult:
    """拆分结果。"""

    chapters: list[Chapter] = field(default_factory=list)
    total_chapters: int = 0
    total_chars: int = 0
    pattern_used: str = ""  # 实际匹配到的模式


def _compile_patterns(patterns: list[str]) -> re.Pattern:
    """编译组合正则，使用非捕获组避免回溯问题。"""
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.MULTILINE)


def split_chapters(
    text: str,
    custom_patterns: list[str] | None = None,
) -> SplitResult:
    """将文本拆分为章节列表。"""
    patterns = list(DEFAULT_PATTERNS)
    if custom_patterns:
        patterns = custom_patterns + patterns

    regex = _compile_patterns(patterns)
    matches = list(regex.finditer(text))

    if not matches:
        return SplitResult(
            chapters=[Chapter(index=1, title="全文", content=text.strip(), start_pos=0)],
            total_chapters=1,
            total_chars=len(text),
            pattern_used="",
        )

    chapters = []
    for i, match in enumerate(matches):
        title = match.group().strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        chapters.append(Chapter(index=i + 1, title=title, content=content, start_pos=match.start()))

    return SplitResult(
        chapters=chapters,
        total_chapters=len(chapters),
        total_chars=sum(len(ch.content) for ch in chapters),
        pattern_used=", ".join(patterns[:3]),
    )


def merge_chapters(chapters: list[Chapter], from_idx: int, to_idx: int) -> list[Chapter]:
    """合并相邻的两章为一章。"""
    if from_idx >= to_idx or to_idx - from_idx > 1:
        raise ValueError("只能合并相邻的两章")
    a = chapters[from_idx - 1]
    b = chapters[to_idx - 1]
    merged = Chapter(
        index=a.index,
        title=f"{a.title} + {b.title}",
        content=f"{a.content}\n\n{b.content}",
        start_pos=a.start_pos,
    )
    new_list = chapters[: from_idx - 1] + [merged] + chapters[to_idx:]
    # 重新编号
    for i, ch in enumerate(new_list):
        ch.index = i + 1
    return new_list


def split_one_chapter(chapters: list[Chapter], idx: int, split_pos: int) -> list[Chapter]:
    """将一章拆分为两章。split_pos 为拆分点在该章正文中的位置。"""
    ch = chapters[idx - 1]
    part1_content = ch.content[:split_pos].strip()
    part2_content = ch.content[split_pos:].strip()
    first = Chapter(index=ch.index, title=f"{ch.title}(上)", content=part1_content, start_pos=ch.start_pos)
    second = Chapter(index=ch.index + 1, title=f"{ch.title}(下)", content=part2_content, start_pos=ch.start_pos + split_pos)
    new_list = chapters[: idx - 1] + [first, second] + chapters[idx:]
    for i, c in enumerate(new_list):
        c.index = i + 1
    return new_list


def rename_chapter(chapters: list[Chapter], idx: int, new_title: str) -> None:
    """重命名某章标题。"""
    chapters[idx - 1].title = new_title
