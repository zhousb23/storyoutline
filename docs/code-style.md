# 代码规范

## Python 版本
- 目标版本：Python 3.11+
- 编码声明：文件头 `# -*- coding: utf-8 -*-`（涉及中文时）

---

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/文件 | 小写 + 下划线 | `file_parser.py`, `chapter_splitter.py` |
| 类名 | 大驼峰 | `FileParser`, `ChapterSplitter` |
| 函数/方法 | 小写 + 下划线 | `parse_file()`, `split_chapters()` |
| 变量 | 小写 + 下划线 | `chapter_list`, `api_key` |
| 常量 | 全大写 + 下划线 | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 私有属性 | 单下划线前缀 | `_results`, `_api_client` |
| UI 组件变量 | 描述性名称 | `btn_import`, `tree_chapters`, `tab_results` |

---

## 代码组织

### 导入顺序
```python
# 1. 标准库
import os
import json
from pathlib import Path

# 2. 第三方库
from PySide6.QtWidgets import QMainWindow
import requests

# 3. 项目内模块
from src.file_parser import FileParser
```

### 函数规范
- 每个函数只做一件事
- 函数体不超过 50 行（超过则拆分）
- 参数不超过 5 个（超过则用数据类封装）
- 公共函数必须带类型注解

### 类型注解
```python
def parse_file(filepath: str) -> str:
    """解析文件，返回纯文本内容"""
    ...

def split_chapters(text: str, patterns: list[str]) -> list[dict]:
    """拆分章节，返回章节列表"""
    ...
```

---

## 错误处理

- 使用具体异常类型，不使用裸 `except:`
- 在系统边界处捕获异常（文件 I/O、网络请求）
- 内部逻辑优先使用断言和提前返回
- 错误信息用中文，方便用户理解

```python
# ✅ 好的做法
try:
    response = requests.post(url, json=data, timeout=timeout)
    response.raise_for_status()
except requests.Timeout:
    raise RuntimeError("API 请求超时，请检查网络连接")
except requests.HTTPError as e:
    if e.response.status_code == 401:
        raise RuntimeError("API Key 无效，请检查设置")

# ❌ 不好的做法
try:
    ...
except:
    pass
```

---

## UI 代码规范

### 信号槽命名
```python
# 信号连接在 __init__ 末尾统一处理
def _connect_signals(self):
    self.btn_import.clicked.connect(self._on_import_clicked)
    self.btn_analyze.clicked.connect(self._on_analyze_clicked)
```

### 事件处理命名
```python
# 格式：_on_{组件}_{事件}
def _on_import_clicked(self): ...
def _on_chapter_selected(self, index): ...
def _on_analyze_finished(self): ...
```

### UI 与逻辑分离
- UI 文件只处理界面和交互
- 业务逻辑调用核心模块，不写在 UI 类里
- 耗时操作必须在后台线程执行，不阻塞 UI

---

## 注释规范

- 不说「做了什么」（代码本身已说明），只说「为什么这样做」
- 只在逻辑不直观时才加注释
- 不用多行注释，一行短注释即可

```python
# ✅ 有用的注释
# GB2312 在部分 Windows 旧文件中仍常见，优先于 UTF-8 检测
encoding = detect_encoding(filepath)

# ❌ 多余的注释
# 打开文件
with open(filepath, 'r') as f:
    # 读取文件内容
    content = f.read()
```

---

## 提交规范

- 每完成一个步骤就提交一次
- 提交信息格式：`[阶段X.Y] 简短描述`
- 示例：`[1.2] 安装项目依赖`、`[2.3] 完成 DeepSeek 客户端`

---

## 禁止事项

- 禁止硬编码绝对路径
- 禁止在代码中写死 API Key
- 禁止使用 `eval()` 或 `exec()`
- 禁止忽略异常不处理
- 禁止在 UI 线程中发起网络请求
