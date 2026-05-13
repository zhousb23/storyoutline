# -*- coding: utf-8 -*-
"""项目标签页 — 紧凑布局，后台解析，流式分析。"""

import os
import shutil

from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.file_parser import parse_file
from src.chapter_splitter import split_chapters
from src.deepseek_client import DeepSeekClient
from src.analysis_pipeline import AnalysisPipeline
from src.result_manager import ProjectState, ResultManager
from src.ui.chapter_panel import ChapterPanel
from src.ui.result_panel import ResultPanel
from src.utils import get_wenjian_dir


# ============================================================
# 后台线程
# ============================================================

class LoadFileWorker(QThread):
    finished = Signal(str, list, str)  # (全文, 章节列表, 匹配模式)
    error = Signal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            text = parse_file(self.filepath)
            split_result = split_chapters(text)
            chapters = [
                {"index": ch.index, "title": ch.title, "content": ch.content, "status": "pending"}
                for ch in split_result.chapters
            ]
            self.finished.emit(text, chapters, split_result.pattern_used)
        except Exception as e:
            self.error.emit(str(e))


class AnalysisWorker(QThread):
    progress = Signal(str)
    chapter_done = Signal(int, dict)
    section_done = Signal(int, dict)
    character_done = Signal(str)
    style_done = Signal(str)
    writing_advice_done = Signal(str)
    storyline_done = Signal(dict)
    error = Signal(int, str)
    all_done = Signal()

    def __init__(self, pipeline: AnalysisPipeline):
        super().__init__()
        self.pipeline = pipeline

    def run(self):
        self.pipeline.on_progress = self.progress.emit
        self.pipeline.on_chapter_done = self.chapter_done.emit
        self.pipeline.on_section_done = self.section_done.emit
        self.pipeline.on_character_done = self.character_done.emit
        self.pipeline.on_style_done = self.style_done.emit
        self.pipeline.on_writing_advice_done = self.writing_advice_done.emit
        self.pipeline.on_storyline_done = self.storyline_done.emit
        self.pipeline.on_error = self.error.emit
        self.pipeline.on_all_done = self.all_done.emit
        try:
            self.pipeline.run()
        except Exception as e:
            self.error.emit(0, str(e))
        self.all_done.emit()

    def pause(self): self.pipeline.pause()
    def resume(self): self.pipeline.resume()
    def stop(self): self.pipeline.stop()


# ============================================================
# ProjectTab
# ============================================================

class ProjectTab(QWidget):
    project_closed = Signal(object)
    status_message = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._source_file: str | None = None
        self._project_dir: str | None = None
        self._manager: ResultManager | None = None
        self._state: ProjectState | None = None
        self._chapters: list[dict] = []
        self._pipeline: AnalysisPipeline | None = None
        self._worker: AnalysisWorker | None = None
        self._load_worker: LoadFileWorker | None = None
        self._is_analyzing = False
        self._is_loading = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("background-color: #F0F6FB;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 紧凑工具栏 ===
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet("""
            QFrame { background: #FFFFFF; border-bottom: 1px solid #DEE8F0; }
            QPushButton { background: #5B9BD5; color: #FFF; border: none;
                border-radius: 3px; padding: 5px 12px; font-size: 12px; }
            QPushButton:hover { background: #4A8AC4; }
            QPushButton:disabled { background: #C0C0C0; }
            QLabel { color: #555; font-size: 12px; padding: 0 8px; }
        """)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 6, 8, 6)
        bl.setSpacing(6)

        self._btn_import = QPushButton("📂 导入")
        self._btn_import.clicked.connect(self._on_import)
        bl.addWidget(self._btn_import)

        self._btn_analyze = QPushButton("▶ 分析")
        self._btn_analyze.clicked.connect(self._on_analyze)
        self._btn_analyze.setEnabled(False)
        bl.addWidget(self._btn_analyze)

        self._btn_pause = QPushButton("⏸ 暂停")
        self._btn_pause.clicked.connect(self._on_pause_resume)
        self._btn_pause.setEnabled(False)
        bl.addWidget(self._btn_pause)

        self._btn_export = QPushButton("💾 导出")
        self._btn_export.clicked.connect(self._on_export)
        self._btn_export.setEnabled(False)
        bl.addWidget(self._btn_export)

        bl.addStretch()
        self._lbl_progress = QLabel("就绪")
        bl.addWidget(self._lbl_progress)
        layout.addWidget(bar)

        # === 主内容区 ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self._chapter_panel = ChapterPanel()
        self._chapter_panel.chapter_selected.connect(self._on_chapter_selected)
        self._chapter_panel.chapters_modified.connect(self._on_chapters_modified)
        splitter.addWidget(self._chapter_panel)

        self._result_panel = ResultPanel()
        splitter.addWidget(self._result_panel)

        splitter.setSizes([220, 1060])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # === 底部状态条 ===
        status_bar = QFrame()
        status_bar.setFixedHeight(26)
        status_bar.setStyleSheet("""
            QFrame { background: #FFFFFF; border-top: 1px solid #DEE8F0; }
            QLabel { color: #888; font-size: 11px; padding: 0 12px; }
        """)
        sl = QHBoxLayout(status_bar)
        sl.setContentsMargins(0, 0, 0, 0)
        self._lbl_status = QLabel("就绪 — 点击「导入」选择文章文件")
        sl.addWidget(self._lbl_status)
        layout.addWidget(status_bar)

    # ---- 属性 ----
    @property
    def project_name(self) -> str:
        return self._state.name if self._state else "新建项目"

    @property
    def is_analyzing(self) -> bool:
        return self._is_analyzing

    # ---- 公开方法 ----
    def load_existing_project(self, project_dir: str):
        self._project_dir = project_dir
        self._manager = ResultManager(project_dir)
        self._state = self._manager.load_state()
        if self._state and self._state.chapters:
            self._chapters = self._state.chapters
            self._source_file = self._state.source_file
            self._chapter_panel.load_chapters(self._chapters)
            self._restore_results()
            self._btn_analyze.setEnabled(True)
            self._btn_export.setEnabled(True)
            self.status_message.emit(f"已加载: {self._state.name} | {len(self._chapters)}章 | 已分析{self._state.analyzed_count}章")

    def stop_analysis(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)

    # ---- 导入 ----
    def _on_import(self):
        if self._is_loading:
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入文章", "",
            "所有支持格式 (*.txt *.docx *.pdf *.epub);;文本文件 (*.txt);;Word文档 (*.docx);;PDF文件 (*.pdf);;EPUB电子书 (*.epub)",
        )
        if not filepath:
            return

        self._is_loading = True
        self._btn_import.setEnabled(False)
        self._btn_import.setText("⏳ 解析中...")
        self._btn_analyze.setEnabled(False)
        self._lbl_progress.setText(f"解析中: {os.path.basename(filepath)}...")
        self._lbl_status.setText("正在解析文件，大文件可能需要几秒...")

        self._source_file = filepath
        self._load_worker = LoadFileWorker(filepath)
        self._load_worker.finished.connect(self._on_load_finished)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_load_finished(self, text: str, chapters: list[dict], pattern_used: str):
        self._is_loading = False
        self._btn_import.setEnabled(True)
        self._btn_import.setText("📂 导入")
        self._btn_analyze.setEnabled(True)
        self._btn_export.setEnabled(False)

        self._chapters = chapters
        self._chapter_panel.load_chapters(chapters)
        self._result_panel.show_original_text(text)
        name = os.path.splitext(os.path.basename(self._source_file or ""))[0]
        self._lbl_progress.setText(f"{len(chapters)}章 | {len(text):,}字")
        self._lbl_status.setText(f"已加载: {name} | {len(chapters)}章 | 匹配: {pattern_used} | 点击「分析」开始")
        self.status_message.emit(f"已加载: {name} | {len(chapters)}章")

    def _on_load_error(self, error_msg: str):
        self._is_loading = False
        self._btn_import.setEnabled(True)
        self._btn_import.setText("📂 导入")
        self._lbl_progress.setText("解析失败")
        self._lbl_status.setText(f"解析失败: {error_msg}")
        QMessageBox.warning(self, "解析失败", str(error_msg))

    # ---- 分析 ----
    def _on_analyze(self):
        if not self._chapters:
            return
        if not self._settings.api_key:
            QMessageBox.warning(self, "未配置 API Key", "请先在菜单 设置→API配置 中填写 Key")
            return
        if self._worker and self._worker.isRunning():
            return

        project_name = os.path.splitext(os.path.basename(self._source_file or "未命名"))[0]

        # 选择项目存储位置（默认 wenjian 文件夹）
        if not self._project_dir:
            default_dir = self._settings.project_root or get_wenjian_dir()
            chosen_dir = QFileDialog.getExistingDirectory(self, "选择项目保存位置", default_dir)
            if not chosen_dir:
                return
            self._project_dir = os.path.join(chosen_dir, f"{project_name}.storyoutline")

        os.makedirs(self._project_dir, exist_ok=True)

        # 复制源文件到项目目录
        if self._source_file and os.path.isfile(self._source_file):
            src_dir = os.path.join(self._project_dir, "source")
            os.makedirs(src_dir, exist_ok=True)
            dst = os.path.join(src_dir, os.path.basename(self._source_file))
            if not os.path.isfile(dst):
                shutil.copy2(self._source_file, dst)

        self._manager = ResultManager(self._project_dir)

        existing = self._manager.load_state()
        if existing and existing.chapters:
            self._state = existing
        else:
            self._state = ProjectState(
                name=project_name,
                source_file=self._source_file or "",
                chapters=self._chapters,
                section_size=self._settings.section_size,
            )

        client = DeepSeekClient(
            api_key=self._settings.api_key,
            model=self._settings.model,
            timeout=self._settings.timeout,
        )
        self._pipeline = AnalysisPipeline(
            client=client, manager=self._manager, state=self._state,
            section_size=self._settings.section_size,
        )
        self._worker = AnalysisWorker(self._pipeline)
        self._worker.progress.connect(self._on_progress)
        self._worker.chapter_done.connect(self._on_chapter_done)
        self._worker.section_done.connect(self._on_section_done)
        self._worker.character_done.connect(self._on_character_done)
        self._worker.style_done.connect(self._on_style_done)
        self._worker.writing_advice_done.connect(self._on_writing_advice_done)
        self._worker.storyline_done.connect(self._on_storyline_done)
        self._worker.error.connect(self._on_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

        self._is_analyzing = True
        self._btn_analyze.setEnabled(False)
        self._btn_pause.setEnabled(True)
        self._lbl_progress.setText(f"0/{len(self._chapters)}章")
        self._lbl_status.setText("分析中...")

    def _on_pause_resume(self):
        if not self._worker or not self._worker.isRunning():
            return
        if self._worker.pipeline._paused:
            self._worker.resume()
            self._btn_pause.setText("⏸ 暂停")
            self._lbl_status.setText("已恢复分析")
        else:
            self._worker.pause()
            self._btn_pause.setText("▶ 继续")
            self._lbl_status.setText("已暂停（当前批次完成后停止）")

    # ---- 信号处理 ----
    def _on_chapter_selected(self, idx: int):
        if self._chapters and 1 <= idx <= len(self._chapters):
            ch = self._chapters[idx - 1]
            self._result_panel.show_chapter_text(ch["title"], ch["content"])

    def _on_chapters_modified(self, chapters: list[dict]):
        self._chapters = chapters

    def _on_progress(self, msg: str):
        self._lbl_status.setText(msg)

    def _on_chapter_done(self, idx: int, result: dict):
        self._chapter_panel.mark_chapter_done(idx)
        self._result_panel.add_step1_result(result)
        self._lbl_progress.setText(f"{idx}/{len(self._chapters)}章")

    def _on_section_done(self, idx: int, entry: dict):
        self._result_panel.add_step2_result(entry)

    def _on_character_done(self, text: str):
        self._result_panel.show_character_analysis(text)

    def _on_style_done(self, text: str):
        self._result_panel.show_style_analysis(text)

    def _on_writing_advice_done(self, text: str):
        self._result_panel.show_writing_advice(text)

    def _on_storyline_done(self, result: dict):
        self._result_panel.show_step3_result(result)

    def _on_error(self, idx: int, msg: str):
        if idx > 0:
            self._chapter_panel.mark_chapter_error(idx)

    def _on_all_done(self):
        self._is_analyzing = False
        self._btn_analyze.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_pause.setText("⏸ 暂停")
        self._btn_export.setEnabled(True)
        self._lbl_progress.setText(f"{len(self._chapters)}/{len(self._chapters)}章 ✓")
        self._lbl_status.setText("分析完成！可导出结果")

        if self._manager:
            for results, show_fn in [
                (self._manager.load_step2_results(), self._result_panel.show_step2_results),
                (self._manager.load_step3_result(), self._result_panel.show_step3_result),
            ]:
                if results and not isinstance(results, bool):
                    show_fn(results) if isinstance(results, dict) else show_fn(results)

    def _on_export(self):
        if not self._manager:
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "导出为", "", "Word 文档 (*.docx)")
        if not filepath:
            return
        try:
            name = self._state.name if self._state else "故事大纲分析"
            self._manager.export_to_docx(filepath, name)
            self._lbl_status.setText(f"已导出: {os.path.basename(filepath)}")
            QMessageBox.information(self, "导出成功", f"文件已保存至:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _restore_results(self):
        if not self._manager:
            return
        for r in (self._manager.load_step1_results() or []):
            self._result_panel.add_step1_result(r)
            self._chapter_panel.mark_chapter_done(r["chapter_index"])
        for data_key, show_fn in [
            ("step2_results.json", None),
            ("character_analysis.json", self._result_panel.show_character_analysis),
            ("style_analysis.json", self._result_panel.show_style_analysis),
            ("writing_advice.json", self._result_panel.show_writing_advice),
        ]:
            data = self._manager._read_json(data_key)
            if data and show_fn:
                show_fn(data["result"])
        step3 = self._manager.load_step3_result()
        if step3:
            self._result_panel.show_step3_result(step3)
        step2 = self._manager.load_step2_results()
        if step2:
            self._result_panel.show_step2_results(step2)

    def backup_project(self, target_dir: str) -> bool:
        """备份项目到指定目录。"""
        if not self._project_dir or not os.path.isdir(self._project_dir):
            return False
        dst = os.path.join(target_dir, os.path.basename(self._project_dir))
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(self._project_dir, dst)
        return True
