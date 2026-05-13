# -*- coding: utf-8 -*-
"""StoryOutline 应用入口。

用法:
    python -m src.main
"""

import sys
import os

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StoryOutline")
    app.setOrganizationName("StoryOutline")

    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
