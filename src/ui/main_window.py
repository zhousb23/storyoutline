# -*- coding: utf-8 -*-
"""主窗口 — 多项目标签页管理，支持同时分析多个文件。"""

import os

from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup

from src.ui.project_tab import ProjectTab
from src.ui.settings_dialog import SettingsDialog, Settings

STYLE_SHEET = """
QMainWindow {
    background-color: #F0F6FB;
}
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #D9D9D9;
    padding: 2px;
    font-size: 13px;
}
QMenuBar::item:selected {
    background-color: #E3F0F8;
    border-radius: 4px;
}
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E3F0F8;
    spacing: 8px;
    padding: 4px 8px;
}
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E3F0F8;
    color: #666666;
    font-size: 12px;
}
QTabWidget::pane {
    border: none;
    background-color: #F0F6FB;
}
QTabBar::tab {
    background-color: #E3F0F8;
    color: #333333;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 12px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    border-bottom: 2px solid #5B9BD5;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #CDE3F2;
}
QTabBar::tab:disabled {
    color: #999999;
}
"""


class MainWindow(QMainWindow):
    """StoryOutline 主窗口 — 管理多个分析项目。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StoryOutline — 故事大纲分析")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(STYLE_SHEET)

        self._settings = Settings.load()
        self._tabs: list[ProjectTab] = []

        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        # 默认从已有项目打开（如果有）
        self._set_status("就绪 — 点击「新建项目」导入文章，或点击「打开项目」继续之前的工作")

    # ---- 菜单栏 ----

    def _build_menu(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        act_new = QAction("新建项目(&N)...", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._on_new_project)
        file_menu.addAction(act_new)

        act_open = QAction("打开项目(&O)...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_open_project)
        file_menu.addAction(act_open)

        file_menu.addSeparator()

        act_backup = QAction("备份当前项目(&B)...", self)
        act_backup.triggered.connect(self._on_backup_current)
        file_menu.addAction(act_backup)

        act_cloud_sync = QAction("同步到云盘(&S)...", self)
        act_cloud_sync.triggered.connect(self._on_cloud_sync)
        file_menu.addAction(act_cloud_sync)

        file_menu.addSeparator()

        act_close = QAction("关闭当前项目(&W)", self)
        act_close.setShortcut("Ctrl+W")
        act_close.triggered.connect(self._on_close_current)
        file_menu.addAction(act_close)

        file_menu.addSeparator()

        act_exit = QAction("退出(&X)", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        act_settings = QAction("API 配置(&A)...", self)
        act_settings.triggered.connect(self._on_settings)
        settings_menu.addAction(act_settings)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        act_about = QAction("关于(&A)", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ---- 工具栏 ----

    def _build_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        btn_style = """
            QToolBar QToolButton {
                background-color: #5B9BD5;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
                margin: 0 2px;
            }
            QToolBar QToolButton:hover { background-color: #4A8AC4; }
            QToolBar QToolButton:disabled { background-color: #BFBFBF; color: #FFFFFF; }
        """
        toolbar.setStyleSheet(btn_style)

        self._act_new = toolbar.addAction("📂 新建项目")
        self._act_new.triggered.connect(self._on_new_project)

        self._act_open = toolbar.addAction("📁 打开项目")
        self._act_open.triggered.connect(self._on_open_project)

    # ---- 中央区域 ----

    def _build_central(self):
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.tabCloseRequested.connect(self._on_close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        # 添加"+"按钮标签页用于新建项目
        self._tab_widget.setStyleSheet(self._tab_widget.styleSheet() + """
            QTabBar::tab:last {
                background-color: transparent;
                border: 1px dashed #BDBDBD;
                color: #666666;
                min-width: 40px;
                max-width: 40px;
                font-size: 18px;
            }
        """)

        self.setCentralWidget(self._tab_widget)

    # ---- 状态栏 ----

    def _build_statusbar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _set_status(self, msg: str):
        self.statusBar().showMessage(msg)

    # ---- 项目管理 ----

    def _add_project_tab(self, name: str = "新建项目") -> ProjectTab:
        """创建一个新的项目标签页。"""
        tab = ProjectTab(self._settings)
        tab.status_message.connect(self._on_project_status)
        tab.project_closed.connect(self._remove_tab)

        idx = self._tab_widget.addTab(tab, name)
        self._tab_widget.setCurrentIndex(idx)
        self._tabs.append(tab)
        return tab

    def _remove_tab(self, tab: ProjectTab):
        """移除指定的项目标签页。"""
        for i in range(self._tab_widget.count()):
            if self._tab_widget.widget(i) is tab:
                self._tab_widget.removeTab(i)
                break
        if tab in self._tabs:
            self._tabs.remove(tab)
        tab.stop_analysis()
        tab.deleteLater()

    # ---- 槽函数 ----

    def _on_new_project(self):
        tab = self._add_project_tab("新建项目")
        # 直接触发导入
        tab._on_import()
        # 更新标签页标题
        for i in range(self._tab_widget.count()):
            if self._tab_widget.widget(i) is tab:
                self._tab_widget.setTabText(i, tab.project_name)
                break

    def _on_open_project(self):
        """打开已有的 .storyoutline 项目目录。"""
        dirpath = QFileDialog.getExistingDirectory(
            self, "打开项目目录", "",
        )
        if not dirpath:
            return
        # 检查是否含 project.json
        if not os.path.isfile(os.path.join(dirpath, "project.json")):
            QMessageBox.warning(self, "无效项目", "所选目录不是有效的 StoryOutline 项目（缺少 project.json）")
            return

        tab = self._add_project_tab()
        tab.load_existing_project(dirpath)
        for i in range(self._tab_widget.count()):
            if self._tab_widget.widget(i) is tab:
                self._tab_widget.setTabText(i, tab.project_name)
                break

    def _on_close_tab(self, index: int):
        """关闭标签页按钮被点击。"""
        widget = self._tab_widget.widget(index)
        if isinstance(widget, ProjectTab):
            if widget.is_analyzing:
                reply = QMessageBox.question(
                    self, "确认关闭",
                    f"项目「{widget.project_name}」正在分析中，确定要关闭吗？",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self._remove_tab(widget)

    def _on_close_current(self):
        """关闭当前标签页。"""
        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            self._on_close_tab(idx)

    def _on_tab_changed(self, index: int):
        """标签页切换时更新状态栏。"""
        if index < 0:
            return
        widget = self._tab_widget.widget(index)
        if isinstance(widget, ProjectTab):
            self._set_status(f"当前项目: {widget.project_name}")

    def _on_project_status(self, msg: str):
        """接收来自项目标签页的状态消息。"""
        self._set_status(msg)

    def _on_settings(self):
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            self._settings = dlg.settings
            self._settings.save()
            # 通知所有标签页设置已更新
            for tab in self._tabs:
                tab._settings = self._settings

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 StoryOutline",
            "StoryOutline — 故事大纲分析软件\n\n"
            "功能特性：\n"
            "• 分章节提取故事大纲（激励事件/进展纠葛/危机/高潮/结局）\n"
            "• 每 50 章阶段性总结\n"
            "• 全书故事线分析\n"
            "• 人物小传提取\n"
            "• 写作风格分析\n"
            "• 支持多项目并行分析\n\n"
            "技术: Python + PySide6 + DeepSeek\n"
            "版本: 1.0.0",
        )

    def _current_tab(self) -> ProjectTab | None:
        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            widget = self._tab_widget.widget(idx)
            if isinstance(widget, ProjectTab):
                return widget
        return None

    def _on_backup_current(self):
        """备份当前项目到指定文件夹。"""
        tab = self._current_tab()
        if not tab:
            QMessageBox.warning(self, "无项目", "请先打开一个项目")
            return
        target = QFileDialog.getExistingDirectory(self, "选择备份目标文件夹")
        if not target:
            return
        try:
            if tab.backup_project(target):
                QMessageBox.information(self, "备份成功", f"项目已备份到:\n{target}")
            else:
                QMessageBox.warning(self, "备份失败", "项目尚未开始分析，无数据可备份")
        except Exception as e:
            QMessageBox.warning(self, "备份失败", str(e))

    def _on_cloud_sync(self):
        """同步项目到云盘（复制到云盘本地同步文件夹）。"""
        tab = self._current_tab()
        if not tab:
            QMessageBox.warning(self, "无项目", "请先打开一个项目")
            return

        # 检查是否配置了云盘路径
        cloud_path = self._settings.cloud_sync_path
        if not cloud_path or not os.path.isdir(cloud_path):
            reply = QMessageBox.question(
                self, "未配置云盘",
                "尚未设置云盘同步文件夹。\n\n是否现在设置？（选择云盘本地同步文件夹即可，\n如 OneDrive、百度网盘、坚果云等本地目录）",
            )
            if reply == QMessageBox.StandardButton.Yes:
                cloud_path = QFileDialog.getExistingDirectory(self, "选择云盘本地同步文件夹")
                if cloud_path:
                    self._settings.cloud_sync_path = cloud_path
                    self._settings.save()
                else:
                    return
            else:
                return

        try:
            if tab.backup_project(cloud_path):
                QMessageBox.information(self, "同步成功", f"项目已同步到云盘:\n{cloud_path}")
            else:
                QMessageBox.warning(self, "同步失败", "项目无数据可同步")
        except Exception as e:
            QMessageBox.warning(self, "同步失败", str(e))

    def closeEvent(self, event):
        """关闭窗口时停止所有分析。"""
        for tab in self._tabs:
            if tab.is_analyzing:
                reply = QMessageBox.question(
                    self, "确认退出",
                    f"项目「{tab.project_name}」仍在分析中，确定退出吗？\n（进度已自动保存，下次可继续）",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            tab.stop_analysis()
        event.accept()
