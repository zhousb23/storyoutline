# -*- coding: utf-8 -*-
"""结果展示区 — 四个标签页（原文 / 章节大纲 / 阶段总结 / 全书故事线）。"""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Qt


class ResultPanel(QFrame):
    """右侧结果展示区。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._step1_results: dict[int, dict] = {}  # chapter_index -> result
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("ResultPanel")
        self.setStyleSheet("""
            #ResultPanel {
                background-color: #F0F6FB;
            }
            QTabWidget::pane {
                background-color: #FFFFFF;
                border: 1px solid #D5E3EE;
                border-radius: 3px;
                margin: 4px;
            }
            QTabBar::tab {
                background-color: #EAF2F8;
                color: #555;
                padding: 6px 14px; margin-right: 1px;
                border-top-left-radius: 3px; border-top-right-radius: 3px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                border-bottom: 2px solid #5B9BD5;
                color: #333;
            }
            QTabBar::tab:hover:!selected {
                background-color: #D4E6F5;
            }
            QTextBrowser {
                background-color: #FFFFFF;
                border: none; color: #333;
                font-size: 13px; padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()

        # 标签页1：原文
        self._tab_original = QTextBrowser()
        self._tabs.addTab(self._tab_original, "📄 原文")

        # 标签页2：章节大纲
        self._tab_step1 = QWidget()
        self._step1_layout = QVBoxLayout(self._tab_step1)
        self._step1_scroll = QScrollArea()
        self._step1_scroll.setWidgetResizable(True)
        self._step1_scroll.setStyleSheet("QScrollArea { border: none; background: #FFFFFF; }")
        self._step1_container = QWidget()
        self._step1_container_layout = QVBoxLayout(self._step1_container)
        self._step1_container_layout.setAlignment(Qt.AlignTop)
        self._step1_scroll.setWidget(self._step1_container)
        self._step1_layout.addWidget(self._step1_scroll)
        self._tabs.addTab(self._tab_step1, "📝 章节大纲")

        # 标签页3：阶段总结
        self._tab_step2 = QTextBrowser()
        self._tabs.addTab(self._tab_step2, "📊 阶段总结")

        # 标签页4：全书故事线
        self._tab_step3 = QTextBrowser()
        self._tabs.addTab(self._tab_step3, "📈 全书故事线")

        # 标签页5：人物小传
        self._tab_character = QTextBrowser()
        self._tabs.addTab(self._tab_character, "👤 人物小传")

        # 标签页6：语言风格
        self._tab_style = QTextBrowser()
        self._tabs.addTab(self._tab_style, "🎨 语言风格")

        # 标签页7：写作建议
        self._tab_writing_advice = QTextBrowser()
        self._tabs.addTab(self._tab_writing_advice, "✍️ 写作建议")

        layout.addWidget(self._tabs)

        # 阶段总结累积内容（用于流式追加）
        self._step2_html_parts: list[str] = []

    # ---- 公开方法 ----

    def show_original_text(self, text: str):
        """显示全文原文。"""
        self._tab_original.setPlainText(text)
        self._tabs.setCurrentWidget(self._tab_original)

    def show_chapter_text(self, title: str, content: str):
        """显示单章原文。"""
        self._tab_original.setPlainText(f"{title}\n\n{content}")

    def add_step1_result(self, result: dict):
        """追加单章分析结果到章节大纲标签页。"""
        idx = result["chapter_index"]
        self._step1_results[idx] = result

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FAFCFF;
                border: 1px solid #E3F0F8;
                border-radius: 8px;
                padding: 12px;
                margin: 4px 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        title_lbl = QLabel(f"第{idx}章 {result.get('chapter_title', '')}")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #3B7DD8; padding-bottom: 4px;")
        card_layout.addWidget(title_lbl)

        fields = [
            ("激励事件", result.get("inciting_incident", "")),
            ("进展纠葛", result.get("progressive_complications", "")),
            ("危机", result.get("crisis", "")),
            ("高潮", result.get("climax", "")),
            ("结局", result.get("resolution", "")),
        ]
        for label, content in fields:
            if content:
                field_widget = QLabel(f"<b>{label}：</b>{content}")
                field_widget.setWordWrap(True)
                field_widget.setStyleSheet("font-size: 12px; color: #333333; padding: 2px 0;")
                card_layout.addWidget(field_widget)

        self._step1_container_layout.addWidget(card)

    def show_step2_results(self, results: list[dict]):
        """显示阶段总结。"""
        html_parts = []
        for r in results:
            section_range = f"{r['chapter_range'][0]}-{r['chapter_range'][1]}"
            html_parts.append(
                f"<h2 style='color: #3B7DD8;'>阶段{r['section_index']}（第{section_range}章）</h2>"
                f"<p style='font-size:13px; line-height:1.8;'>{r.get('summary', '')}</p>"
                f"<hr style='border: 1px solid #E3F0F8;'>"
            )
        self._tab_step2.setHtml("".join(html_parts))

    def show_step3_result(self, result: dict):
        """显示全书故事线。"""
        storyline = result.get("overall_storyline", "")
        html = storyline.replace("\n", "<br>")
        self._tab_step3.setHtml(
            f"<div style='font-size:13px; line-height:1.8; color:#333333;'>{html}</div>"
        )
        self._tabs.setCurrentWidget(self._tab_step3)

    def add_step2_result(self, entry: dict):
        """流式追加单条阶段总结（每 50 章完成后立即显示）。"""
        section_range = f"{entry['chapter_range'][0]}-{entry['chapter_range'][1]}"
        html = (
            f"<h2 style='color: #3B7DD8;'>阶段{entry['section_index']}（第{section_range}章）</h2>"
            f"<p style='font-size:13px; line-height:1.8;'>{entry.get('summary', '')}</p>"
            f"<hr style='border: 1px solid #E3F0F8;'>"
        )
        self._step2_html_parts.append(html)
        self._tab_step2.setHtml("".join(self._step2_html_parts))

    def show_character_analysis(self, char_text: str):
        """显示人物分析结果。"""
        html = char_text.replace("\n", "<br>").replace("---", "<hr style='border: 1px dashed #D9D9D9;'>")
        self._tab_character.setHtml(
            f"<div style='font-size:13px; line-height:1.8; color:#333333;'>{html}</div>"
        )

    def show_style_analysis(self, style_text: str):
        """显示写作风格分析结果。"""
        html = style_text.replace("\n", "<br>")
        self._tab_style.setHtml(
            f"<div style='font-size:13px; line-height:1.8; color:#333333;'>{html}</div>"
        )

    def show_writing_advice(self, advice_text: str):
        """显示写作建议与段落摘抄。"""
        html = advice_text.replace("\n", "<br>").replace("📌", "<br><b>📌")
        self._tab_writing_advice.setHtml(
            f"<div style='font-size:13px; line-height:1.8; color:#333333;'>{html}</div>"
        )
