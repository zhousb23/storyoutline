# -*- coding: utf-8 -*-
"""分析流水线 — 三步流程状态机 + 人物分析 + 风格分析，支持流式输出和断点续传。

核心特性：
  - 分批分析：每 N 章一批，完成即输出，不等待全部完成
  - 人物分析：在分析一定量章节后自动触发
  - 风格分析：在全书分析完成后触发
  - 断点续传：进度自动保存
"""

import time
from dataclasses import dataclass, field

from src.deepseek_client import DeepSeekClient
from src.result_manager import ProjectState, ResultManager


def _parse_step1_text(text: str, chapter_index: int, chapter_title: str) -> dict:
    """将第一步 AI 返回的文本解析为结构化数据。"""
    import re

    result = {
        "chapter_index": chapter_index,
        "chapter_title": chapter_title,
        "inciting_incident": "",
        "progressive_complications": "",
        "crisis": "",
        "climax": "",
        "resolution": "",
        "raw": text,
    }

    keywords = [
        ("激励事件", "inciting_incident"),
        ("进展纠葛", "progressive_complications"),
        ("危机", "crisis"),
        ("高潮", "climax"),
        ("结局", "resolution"),
    ]

    remaining = text
    for i, (kw, key) in enumerate(keywords):
        idx = remaining.find(kw)
        if idx == -1:
            pattern = rf"\d+\.\s*\*?\*?{kw}\*?\*?"
            m = re.search(pattern, remaining)
            if m:
                idx = m.start()
        if idx == -1:
            continue

        after_kw = remaining[idx + len(kw):]
        after_kw = re.sub(r"^[：:\s\*]+", "", after_kw)

        end = len(after_kw)
        for next_kw, _ in keywords[i + 1:]:
            next_idx = after_kw.find(next_kw)
            if next_idx != -1:
                end = next_idx
                break

        result[key] = after_kw[:end].strip()
        remaining = after_kw[end:]

    return result


class AnalysisPipeline:
    """分析流水线 — 流式分批处理。

    分析步骤：
      Step 1: 逐章分析大纲 → 每完成一批 N 章，触发 Step 2
      Step 2: 阶段总结 → 即时输出
      Step 2.5: 人物分析（首批完成后触发一次，后续每批更新）
      Step 3: 全书故事线（全部完成后）
      Step 3.5: 写作风格分析（全书完成后）
    """

    def __init__(
        self,
        client: DeepSeekClient,
        manager: ResultManager,
        state: ProjectState,
        section_size: int = 50,
        on_progress: callable = None,
        on_chapter_done: callable = None,
        on_section_done: callable = None,
        on_character_done: callable = None,
        on_style_done: callable = None,
        on_writing_advice_done: callable = None,
        on_storyline_done: callable = None,
        on_error: callable = None,
        on_all_done: callable = None,
    ):
        self.client = client
        self.manager = manager
        self.state = state
        self.section_size = section_size

        self.on_progress = on_progress or (lambda msg: None)
        self.on_chapter_done = on_chapter_done or (lambda ch_idx, result: None)
        self.on_section_done = on_section_done or (lambda section_idx, entry: None)
        self.on_character_done = on_character_done or (lambda result_text: None)
        self.on_style_done = on_style_done or (lambda result_text: None)
        self.on_writing_advice_done = on_writing_advice_done or (lambda result_text: None)
        self.on_storyline_done = on_storyline_done or (lambda result: None)
        self.on_error = on_error or (lambda ch_idx, err: None)
        self.on_all_done = on_all_done or (lambda: None)

        self._paused = False
        self._stopped = False
        self._text_samples: list[str] = []  # 收集原文片段用于风格分析

    def pause(self):
        self._paused = True
        self.on_progress("分析已暂停，当前批次处理完成后将停止")

    def resume(self):
        self._paused = False

    def stop(self):
        self._stopped = True
        self.on_progress("分析已停止")

    # ---- 主流程 ----

    def run(self):
        """运行分析流水线。"""
        self._stopped = False
        self._paused = False

        chapters = self.state.chapters
        total = len(chapters)
        self.on_progress(f"开始分析，共 {total} 章，每 {self.section_size} 章一批")

        batch_start = 0
        while batch_start < total:
            if self._stopped:
                self._save_and_exit("用户手动停止")
                return

            if self._paused:
                self._save_and_exit("用户暂停")
                return

            batch_end = min(batch_start + self.section_size, total)
            self._process_batch(batch_start, batch_end, chapters, total)

            batch_start = batch_end

            # 批次间短暂休息
            if batch_start < total:
                time.sleep(1)

        # 全书完成后
        self._run_storyline(total)
        self._run_style_analysis()
        self._run_writing_advice()
        self.state.current_stage = "done"
        self._save_progress(chapters)
        self.on_progress(f"全部分析完成！共分析 {self.state.analyzed_count} 章")
        self.on_all_done()

    # ---- 内部分批处理 ----

    def _process_batch(self, start: int, end: int, chapters: list[dict], total: int):
        """处理一批章节（start~end-1）。"""
        self.on_progress(f"--- 开始处理第 {start+1}-{end} 章（共{total}章）---")

        # Step 1: 逐章分析
        for i in range(start, end):
            if self._stopped or self._paused:
                return

            ch = chapters[i]
            ch_idx = i + 1

            if ch.get("status") == "done":
                continue

            self.on_progress(f"分析第{ch_idx}/{total}章: {ch.get('title', '')}")

            try:
                ai_text = self.client.analyze_chapter(ch["title"], ch["content"])
            except Exception as e:
                ch["status"] = "error"
                ch["error"] = str(e)
                self.on_error(ch_idx, str(e))
                self._save_progress(chapters)
                continue

            result = _parse_step1_text(ai_text, ch_idx, ch["title"])
            self.state.step1_results.append(result)
            ch["status"] = "done"
            self.state.analyzed_count = len(self.state.step1_results)

            # 收集原文片段用于风格分析（每章取前 200 字）
            self._text_samples.append(ch["content"][:200])

            self.on_chapter_done(ch_idx, result)
            self._save_progress(chapters)

            # 章节间延迟
            time.sleep(0.5)

        # Step 2: 本批阶段总结
        self._run_section_summary(end)

        # Step 2.5: 人物分析（在分析足够章节后触发）
        char_threshold = max(self.section_size, 50)
        if total >= char_threshold and end >= char_threshold:
            self._run_character_analysis()

        self.on_progress(f"第 {start+1}-{end} 章批次处理完成")

    def _run_section_summary(self, end_chapter: int):
        """对刚完成的一批章节做阶段总结（Step 2）。"""
        results = self.state.step1_results
        done_count = len(self.state.step2_results)
        start_idx = done_count * self.section_size
        end_idx = min(len(results), start_idx + self.section_size)
        batch = results[start_idx:end_idx]

        if not batch:
            return

        section_idx = done_count + 1
        chapter_from = batch[0]["chapter_index"]
        chapter_to = batch[-1]["chapter_index"]
        self.on_progress(f"正在生成阶段总结 ({chapter_from}-{chapter_to}章)...")

        try:
            summary = self.client.summarize_section(batch)
        except Exception as e:
            self.on_error(0, f"阶段总结失败: {e}")
            return

        entry = {
            "section_index": section_idx,
            "chapter_range": [chapter_from, chapter_to],
            "summary": summary,
        }
        self.state.step2_results.append(entry)
        self.manager.save_step2_results(self.state.step2_results)
        self.on_section_done(section_idx, entry)
        self.on_progress(f"阶段总结完成 ({chapter_from}-{chapter_to}章)")

    def _run_character_analysis(self):
        """人物分析：基于已有章节大纲提取人物小传。"""
        results = self.state.step1_results
        if len(results) < 20:  # 至少需要 20 章才有足够的人物信息
            return

        self.on_progress("正在分析主要人物...")
        try:
            char_text = self.client.analyze_characters(results, len(results))
        except Exception as e:
            self.on_error(0, f"人物分析失败: {e}")
            return

        self.state.character_analysis = char_text
        self.manager._write_json("character_analysis.json", {"result": char_text})
        self.on_character_done(char_text)
        self.on_progress("人物分析完成")

    def _run_storyline(self, total: int):
        """全书故事线（Step 3）。"""
        if not self.state.step2_results:
            self.on_progress("无阶段总结数据，跳过全书故事线")
            return
        if hasattr(self.state, 'step3_result') and self.state.step3_result:
            self.on_progress("全书故事线已存在，跳过")
            return

        self.on_progress("正在生成全书故事线...")
        try:
            storyline = self.client.generate_storyline(total, self.state.step2_results)
        except Exception as e:
            self.on_error(0, f"全书故事线失败: {e}")
            return

        self.state.step3_result = {
            "total_chapters": total,
            "overall_storyline": storyline,
        }
        self.manager.save_step3_result(self.state.step3_result)
        self.on_storyline_done(self.state.step3_result)
        self.on_progress("全书故事线生成完成！")

    def _run_style_analysis(self):
        """写作风格分析。"""
        self.on_progress("正在分析写作风格...")
        text_samples = "\n".join(self._text_samples)

        try:
            style_text = self.client.analyze_writing_style(
                self.state.step1_results, len(self.state.step1_results), text_samples
            )
        except Exception as e:
            self.on_error(0, f"风格分析失败: {e}")
            return

        self.state.writing_style = style_text
        self.manager._write_json("style_analysis.json", {"result": style_text})
        self.on_style_done(style_text)
        self.on_progress("写作风格分析完成！")

    def _run_writing_advice(self):
        """写作建议分析 + 优秀段落摘抄。"""
        self.on_progress("正在生成写作建议...")
        text_samples = "\n".join(self._text_samples)

        try:
            advice_text = self.client.analyze_writing_advice(
                len(self.state.step1_results), text_samples
            )
        except Exception as e:
            self.on_error(0, f"写作建议分析失败: {e}")
            return

        self.state.writing_advice = advice_text
        self.manager._write_json("writing_advice.json", {"result": advice_text})
        self.on_writing_advice_done(advice_text)
        self.on_progress("写作建议分析完成！")

    # ---- 进度保存 ----

    def _save_progress(self, chapters: list[dict]):
        self.state.chapters = chapters
        self.manager.save_state(self.state)
        self.manager.save_step1_results(self.state.step1_results)

    def _save_and_exit(self, reason: str):
        self.state.chapters = self.state.chapters
        self.manager.save_state(self.state)
        self.on_progress(f"进度已保存（{reason}）")
