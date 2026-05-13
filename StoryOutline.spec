# -*- mode: python ; coding: utf-8 -*-
"""StoryOutline PyInstaller 打包配置"""

# StoryOutline PyInstaller 打包配置
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 如果有额外数据文件，在此添加
    ],
    hiddenimports=[
        'src.file_parser',
        'src.chapter_splitter',
        'src.prompts',
        'src.deepseek_client',
        'src.analysis_pipeline',
        'src.result_manager',
        'src.utils',
        'src.ui.chapter_panel',
        'src.ui.result_panel',
        'src.ui.settings_dialog',
        'src.ui.progress_widget',
        'src.ui.project_tab',
        'src.ui.main_window',
        'ebooklib',
        'bs4',
        'chardet',
        'pdfplumber',
        'docx',
        'lxml',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'email.utils',
        'email.encoders',
        'email.header',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'xmlrpc',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StoryOutline',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # 不显示命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                   # 可在此添加 .ico 图标路径
)
