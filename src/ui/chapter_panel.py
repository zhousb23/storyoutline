# -*- coding: utf-8 -*-
"""章节列表面板 — 树形导航，支持手动调整。"""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal


class ChapterPanel(QFrame):
    """左侧章节列表面板。"""

    chapter_selected = Signal(int)  # 章节序号（1-based）
    chapters_modified = Signal(list)  # 修改后的章节列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapters: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("ChapterPanel")
        self.setStyleSheet("""
            #ChapterPanel {
                background-color: #EAF2F8;
                border-right: 1px solid #D5E3EE;
            }
            QLabel#PanelTitle {
                font-size: 13px; font-weight: bold; color: #333;
                padding: 10px 12px 4px 12px;
            }
            QLabel#ChapterCount {
                font-size: 11px; color: #777;
                padding: 0 12px 6px 12px;
            }
            QTreeWidget {
                background-color: transparent; border: none;
                font-size: 12px; color: #333; outline: none;
            }
            QTreeWidget::item {
                padding: 4px 8px; border-radius: 3px; height: 28px;
            }
            QTreeWidget::item:selected {
                background-color: #5B9BD5; color: #FFFFFF;
            }
            QTreeWidget::item:hover {
                background-color: #D4E6F5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._lbl_title = QLabel("📖 章节列表")
        self._lbl_title.setObjectName("PanelTitle")
        layout.addWidget(self._lbl_title)

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("ChapterCount")
        layout.addWidget(self._lbl_count)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._tree)

    # ---- 公开方法 ----

    def load_chapters(self, chapters: list[dict]):
        """加载章节列表。"""
        self._chapters = chapters
        self._tree.clear()

        for ch in chapters:
            item = QTreeWidgetItem()
            icon = "⚪" if ch.get("status") == "pending" else (
                "✅" if ch.get("status") == "done" else "❌"
            )
            item.setText(0, f"{icon}  {ch['title']}")
            item.setData(0, Qt.UserRole, ch["index"])
            self._tree.addTopLevelItem(item)

        self._lbl_count.setText(f"共 {len(chapters)} 章")

    def mark_chapter_done(self, chapter_index: int):
        """标记章节为已完成。"""
        self._mark_status(chapter_index, "✅")

    def mark_chapter_error(self, chapter_index: int):
        """标记章节为错误。"""
        self._mark_status(chapter_index, "❌")

    def update_progress(self, analyzed_count: int):
        """批量更新进度标记。"""
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            idx = item.data(0, Qt.UserRole)
            text = item.text(0)
            if idx <= analyzed_count:
                item.setText(0, text.replace("⚪", "✅").replace("❌", "✅"))
                if idx <= len(self._chapters):
                    self._chapters[idx - 1]["status"] = "done"

    def _mark_status(self, chapter_index: int, icon: str):
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == chapter_index:
                text = item.text(0)
                # 去掉原有图标
                for old_icon in ["⚪", "✅", "❌"]:
                    text = text.replace(old_icon, "")
                item.setText(0, f"{icon} {text.strip()}")
                break

    # ---- 交互 ----

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        idx = item.data(0, Qt.UserRole)
        if idx is not None:
            self.chapter_selected.emit(idx)

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        idx = item.data(0, Qt.UserRole)
        if idx is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #D9D9D9;
                padding: 4px;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #E3F0F8;
            }
        """)

        act_merge_prev = menu.addAction("合并到上一章")
        act_merge_next = menu.addAction("合并到下一章")
        menu.addSeparator()
        act_split = menu.addAction("拆分为两章...")
        menu.addSeparator()
        act_rename = menu.addAction("重命名...")

        action = menu.exec(self._tree.viewport().mapToGlobal(pos))

        if action == act_merge_prev:
            self._merge_chapters(idx - 1, idx)
        elif action == act_merge_next:
            self._merge_chapters(idx, idx + 1)
        elif action == act_split:
            self._split_chapter(idx)
        elif action == act_rename:
            self._rename_chapter(idx)

    def _merge_chapters(self, from_idx: int, to_idx: int):
        if from_idx < 1 or to_idx > len(self._chapters) or from_idx >= to_idx:
            return
        reply = QMessageBox.question(
            self, "确认合并",
            f"确定将「{self._chapters[from_idx-1]['title']}」和「{self._chapters[to_idx-1]['title']}」合并？",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from src.chapter_splitter import Chapter as ChModel
        chapters_model = [
            ChModel(index=ch["index"], title=ch["title"], content=ch["content"])
            for ch in self._chapters
        ]
        from src.chapter_splitter import merge_chapters
        merged = merge_chapters(chapters_model, from_idx, to_idx)
        self._chapters = [
            {"index": ch.index, "title": ch.title, "content": ch.content, "status": "pending"}
            for ch in merged
        ]
        self.load_chapters(self._chapters)
        self.chapters_modified.emit(self._chapters)

    def _split_chapter(self, idx: int):
        ch = self._chapters[idx - 1]
        mid = len(ch["content"]) // 2
        pos, ok = QInputDialog.getInt(
            self, "拆分章节",
            f"请输入拆分位置（字符数，当前章节共 {len(ch['content'])} 字）：",
            value=mid, min=1, max=len(ch["content"]) - 1,
        )
        if not ok:
            return
        from src.chapter_splitter import Chapter as ChModel
        chapters_model = [
            ChModel(index=c["index"], title=c["title"], content=c["content"])
            for c in self._chapters
        ]
        from src.chapter_splitter import split_one_chapter
        try:
            new_list = split_one_chapter(chapters_model, idx, pos)
        except Exception as e:
            QMessageBox.warning(self, "拆分失败", str(e))
            return
        self._chapters = [
            {"index": c.index, "title": c.title, "content": c.content, "status": "pending"}
            for c in new_list
        ]
        self.load_chapters(self._chapters)
        self.chapters_modified.emit(self._chapters)

    def _rename_chapter(self, idx: int):
        ch = self._chapters[idx - 1]
        new_title, ok = QInputDialog.getText(
            self, "重命名章节",
            "新标题：",
            text=ch["title"],
        )
        if not ok or not new_title.strip():
            return
        self._chapters[idx - 1]["title"] = new_title.strip()
        self.load_chapters(self._chapters)
        self.chapters_modified.emit(self._chapters)
