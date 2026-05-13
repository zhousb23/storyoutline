# -*- coding: utf-8 -*-
"""设置对话框 — API Key 配置、章节规则、分析参数。"""

import json
import os
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt

import requests

from src.utils import get_config_path


@dataclass
class Settings:
    """应用设置。"""
    api_key: str = ""
    model: str = "deepseek-chat"
    timeout: int = 120
    section_size: int = 50
    project_root: str = ""  # 默认项目存储位置
    cloud_sync_path: str = ""  # 云盘本地同步文件夹路径
    custom_patterns: list[str] = None

    def __post_init__(self):
        if self.custom_patterns is None:
            self.custom_patterns = []

    @classmethod
    def load(cls) -> "Settings":
        """从配置文件加载设置。"""
        if not os.path.isfile(get_config_path()):
            return cls()
        with open(get_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            api_key=data.get("api_key", ""),
            model=data.get("model", "deepseek-chat"),
            timeout=data.get("timeout", 120),
            section_size=data.get("section_size", 50),
            project_root=data.get("project_root", ""),
            cloud_sync_path=data.get("cloud_sync_path", ""),
            custom_patterns=data.get("custom_patterns", []),
        )

    def save(self):
        """保存设置到配置文件。"""
        if not self.api_key:
            self.api_key = ""  # 不保存空 Key（保留旧值）
        data = {
            "api_key": self.api_key,
            "model": self.model,
            "timeout": self.timeout,
            "section_size": self.section_size,
            "project_root": self.project_root,
            "cloud_sync_path": self.cloud_sync_path,
            "custom_patterns": self.custom_patterns,
        }
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class SettingsDialog(QDialog):
    """设置对话框。"""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        self.setWindowTitle("设置")
        self.setFixedSize(520, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F6FB;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #333333;
                border: 1px solid #D9D9D9;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 6px;
                color: #3B7DD8;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
            }
            QLineEdit {
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #5B9BD5;
            }
            QPushButton {
                background-color: #5B9BD5;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4A8AC4;
            }
            QSpinBox {
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- API 配置 ---
        api_group = QGroupBox("🔑 API 配置")
        api_form = QFormLayout(api_group)

        self._edit_api_key = QLineEdit()
        self._edit_api_key.setEchoMode(QLineEdit.Password)
        self._edit_api_key.setPlaceholderText("sk-...")
        api_form.addRow("API Key:", self._edit_api_key)

        key_row = QHBoxLayout()
        self._btn_test = QPushButton("测试连接")
        self._btn_test.clicked.connect(self._on_test_api)
        key_row.addWidget(self._btn_test)
        key_row.addStretch()
        self._lbl_test_result = QLabel("")
        self._lbl_test_result.setStyleSheet("color: #666666; font-size: 11px;")
        key_row.addWidget(self._lbl_test_result)
        api_form.addRow("", key_row)

        layout.addWidget(api_group)

        # --- 分析设置 ---
        analysis_group = QGroupBox("⚙️ 分析设置")
        analysis_form = QFormLayout(analysis_group)

        self._spin_section = QSpinBox()
        self._spin_section.setRange(5, 200)
        self._spin_section.setValue(50)
        self._spin_section.setSuffix(" 章")
        analysis_form.addRow("每阶段章数:", self._spin_section)

        self._spin_timeout = QSpinBox()
        self._spin_timeout.setRange(30, 600)
        self._spin_timeout.setValue(120)
        self._spin_timeout.setSuffix(" 秒")
        analysis_form.addRow("API 超时:", self._spin_timeout)

        # 项目存储位置
        from PySide6.QtWidgets import QFileDialog
        project_row = QHBoxLayout()
        self._edit_project_root = QLineEdit()
        self._edit_project_root.setPlaceholderText("留空则保存在软件 wenjian 文件夹")
        self._edit_project_root.setReadOnly(True)
        project_row.addWidget(self._edit_project_root)
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet("padding: 4px 12px;")
        btn_browse.clicked.connect(lambda: self._browse_project_root())
        project_row.addWidget(btn_browse)
        analysis_form.addRow("项目存储位置:", project_row)

        # 云盘同步路径
        cloud_row = QHBoxLayout()
        self._edit_cloud_path = QLineEdit()
        self._edit_cloud_path.setPlaceholderText("选择 OneDrive/百度网盘/坚果云 等本地同步文件夹")
        self._edit_cloud_path.setReadOnly(True)
        cloud_row.addWidget(self._edit_cloud_path)
        btn_cloud = QPushButton("浏览...")
        btn_cloud.setStyleSheet("padding: 4px 12px;")
        btn_cloud.clicked.connect(lambda: self._browse_cloud_path())
        cloud_row.addWidget(btn_cloud)
        analysis_form.addRow("云盘同步文件夹:", cloud_row)

        layout.addWidget(analysis_group)

        # --- 章节识别 ---
        chapter_group = QGroupBox("📑 章节识别")
        chapter_form = QFormLayout(chapter_group)

        self._chk_cn_digit = QCheckBox("中文数字章节（第一章、第十回）")
        self._chk_cn_digit.setChecked(True)
        self._chk_cn_digit.setEnabled(False)
        chapter_form.addRow(self._chk_cn_digit)

        self._chk_ar_digit = QCheckBox("阿拉伯数字章节（第1章、第12章）")
        self._chk_ar_digit.setChecked(True)
        self._chk_ar_digit.setEnabled(False)
        chapter_form.addRow(self._chk_ar_digit)

        self._chk_en = QCheckBox("英文章节（Chapter 1）")
        self._chk_en.setChecked(True)
        self._chk_en.setEnabled(False)
        chapter_form.addRow(self._chk_en)

        self._edit_custom = QLineEdit()
        self._edit_custom.setPlaceholderText("自定义正则，多个用分号分隔。如：第[0-9]+节;^[0-9]+、")
        chapter_form.addRow("自定义规则:", self._edit_custom)

        layout.addWidget(chapter_group)

        # --- 按钮 ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                min-width: 80px;
                padding: 6px 16px;
            }
        """)
        layout.addWidget(buttons)

    def _load_settings(self):
        self._edit_api_key.setText(self.settings.api_key)
        self._spin_section.setValue(self.settings.section_size)
        self._spin_timeout.setValue(self.settings.timeout)
        self._edit_project_root.setText(self.settings.project_root)
        self._edit_cloud_path.setText(self.settings.cloud_sync_path)
        if self.settings.custom_patterns:
            self._edit_custom.setText(";".join(self.settings.custom_patterns))

    def _browse_project_root(self):
        from PySide6.QtWidgets import QFileDialog
        dirpath = QFileDialog.getExistingDirectory(self, "选择默认项目存储文件夹")
        if dirpath:
            self._edit_project_root.setText(dirpath)

    def _browse_cloud_path(self):
        from PySide6.QtWidgets import QFileDialog
        dirpath = QFileDialog.getExistingDirectory(self, "选择云盘本地同步文件夹")
        if dirpath:
            self._edit_cloud_path.setText(dirpath)

    def _on_accept(self):
        self.settings.api_key = self._edit_api_key.text().strip()
        self.settings.section_size = self._spin_section.value()
        self.settings.timeout = self._spin_timeout.value()
        self.settings.project_root = self._edit_project_root.text().strip()
        self.settings.cloud_sync_path = self._edit_cloud_path.text().strip()
        custom_text = self._edit_custom.text().strip()
        self.settings.custom_patterns = (
            [p.strip() for p in custom_text.split(";") if p.strip()]
            if custom_text else []
        )
        self.accept()

    def _on_test_api(self):
        """测试 API 连接。"""
        api_key = self._edit_api_key.text().strip()
        if not api_key:
            self._lbl_test_result.setText("请输入 API Key")
            self._lbl_test_result.setStyleSheet("color: #FF4D4F;")
            return
        if not api_key.startswith("sk-"):
            self._lbl_test_result.setText("Key 格式可能不正确")
            self._lbl_test_result.setStyleSheet("color: #FAAD14;")

        self._lbl_test_result.setText("测试中...")
        self._lbl_test_result.setStyleSheet("color: #666666;")
        self._btn_test.setEnabled(False)

        try:
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "回复OK"}],
                    "max_tokens": 10,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                self._lbl_test_result.setText("连接成功！")
                self._lbl_test_result.setStyleSheet("color: #52C41A;")
            elif resp.status_code == 401:
                self._lbl_test_result.setText("API Key 无效")
                self._lbl_test_result.setStyleSheet("color: #FF4D4F;")
            else:
                self._lbl_test_result.setText(f"错误 ({resp.status_code})")
                self._lbl_test_result.setStyleSheet("color: #FF4D4F;")
        except Exception:
            self._lbl_test_result.setText("网络连接失败")
            self._lbl_test_result.setStyleSheet("color: #FF4D4F;")
        finally:
            self._btn_test.setEnabled(True)
