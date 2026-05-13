# -*- coding: utf-8 -*-
"""进度显示组件。"""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtCore import Qt


class ProgressWidget(QFrame):
    """分析进度条 + 状态提示 + 暂停/继续。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total = 0
        self._current = 0
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("ProgressWidget")
        self.setStyleSheet("""
            #ProgressWidget {
                background-color: #FFFFFF;
                border: 1px solid #E3F0F8;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
            }
            QProgressBar {
                border: none;
                background-color: #E3F0F8;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #3B7DD8;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #5B9BD5;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4A8AC4;
            }
            QPushButton:disabled {
                background-color: #BFBFBF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 文字信息行
        info_row = QHBoxLayout()
        self._lbl_status = QLabel("就绪")
        info_row.addWidget(self._lbl_status)
        info_row.addStretch()
        self._lbl_count = QLabel("")
        info_row.addWidget(self._lbl_count)
        layout.addLayout(info_row)

        # 进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

    def set_total(self, total: int):
        self._total = total
        self._current = 0
        self._progress.setRange(0, total)
        self._update_display()

    def set_current(self, current: int, chapter_title: str = ""):
        self._current = current
        self._update_display()
        if chapter_title:
            self._lbl_status.setText(f"正在分析: {chapter_title}")

    def set_status(self, text: str):
        self._lbl_status.setText(text)

    def _update_display(self):
        self._progress.setValue(self._current)
        self._lbl_count.setText(f"{self._current}/{self._total}")
