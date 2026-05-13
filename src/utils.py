# -*- coding: utf-8 -*-
"""工具函数 — 路径、环境判断。"""

import os
import sys


def get_app_dir() -> str:
    """获取应用根目录（开发时 = 项目根，打包后 = exe 所在目录）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """获取用户数据目录（%APPDATA%/StoryOutline/），确保对非管理员可写。"""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    data_dir = os.path.join(appdata, "StoryOutline")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_wenjian_dir() -> str:
    """获取默认文件存储目录。安装在 Program Files 时使用用户数据目录。"""
    data_dir = get_data_dir()
    wenjian = os.path.join(data_dir, "wenjian")
    os.makedirs(wenjian, exist_ok=True)
    return wenjian


def get_config_path() -> str:
    """获取配置文件路径。"""
    return os.path.join(get_data_dir(), "storyoutline_config.json")
