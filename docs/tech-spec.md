# 技术规格说明

## 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语言 | Python | 3.11+ | 主开发语言 |
| UI 框架 | PySide6 | 6.x | 桌面 GUI（Qt for Python） |
| HTTP 客户端 | requests | 2.x | 调用 DeepSeek API |
| Word 读取 | python-docx | 1.x | 解析 .docx 文件 |
| PDF 读取 | pdfplumber | 0.x | 解析 PDF 文件 |
| 编码检测 | chardet | 5.x | 自动检测 TXT 文件编码 |
| Word 写入 | python-docx | 1.x | 生成导出 .docx 文件 |
| 打包 | PyInstaller | 6.x | 生成独立 .exe |

---

## 系统架构

```
┌─────────────────────────────────────────┐
│              UI 层 (PySide6)              │
│  main_window / chapter_panel / result_  │
│  panel / settings_dialog / progress      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           应用逻辑层                       │
│  analysis_pipeline (状态机)               │
│  result_manager (存储/导出)               │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           核心服务层                       │
│  file_parser    │  chapter_splitter      │
│  deepseek_client│  prompts              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           外部依赖                         │
│  DeepSeek API  │  本地文件系统             │
└─────────────────────────────────────────┘
```

## 模块职责

### UI 层
- **main_window.py**：主窗口，包含菜单栏、工具栏、状态栏，管理整体布局
- **chapter_panel.py**：左侧章节列表面板，树形展示，支持右键菜单调整
- **result_panel.py**：右侧结果展示区，QTabWidget 包含四个标签页
- **settings_dialog.py**：设置对话框，管理 API Key 和章节规则
- **progress_widget.py**：进度显示组件

### 应用逻辑层
- **analysis_pipeline.py**：分析流程状态机，管理三步分析的执行顺序和进度
- **result_manager.py**：结果读写（JSON 格式），Word/TXT 导出

### 核心服务层
- **file_parser.py**：统一文件解析入口，支持 TXT/DOCX/PDF
- **chapter_splitter.py**：正则匹配拆分章节，管理自定义规则
- **deepseek_client.py**：封装 DeepSeek API 调用，含重试和超时
- **prompts.py**：管理三步分析的 System/User Prompt 模板

---

## API 接口

### DeepSeek API
- 端点：`https://api.deepseek.com/v1/chat/completions`
- 鉴权：`Authorization: Bearer {API_KEY}`
- 请求格式：兼容 OpenAI Chat Completions API

```
POST /v1/chat/completions
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "max_tokens": 4096
}
```

---

## 数据格式

### 章节数据结构
```python
{
    "index": int,        # 章节序号（从1开始）
    "title": str,        # 章节标题（如"第一章 大闹天宫"）
    "content": str,      # 章节正文
    "status": str        # 分析状态: "pending" | "analyzing" | "done" | "error"
}
```

### 第一步结果
```python
{
    "chapter_index": int,
    "chapter_title": str,
    "inciting_incident": str,      # 激励事件
    "progressive_complications": str, # 进展纠葛
    "crisis": str,                 # 危机
    "climax": str,                 # 高潮
    "resolution": str              # 结局
}
```

### 第二步结果
```python
{
    "section_index": int,    # 第几个50章段（1开始）
    "chapter_range": [1, 50], # 覆盖的章节范围
    "summary": str           # 总结内容
}
```

### 第三步结果
```python
{
    "total_chapters": int,
    "overall_storyline": str  # 全书故事线
}
```

### 项目文件结构
```
项目名.storyoutline/
  ├── project.json        # 元数据 + 进度
  ├── step1_results.json  # 各章分析结果数组
  ├── step2_results.json  # 阶段总结数组
  └── step3_result.json   # 全书故事线
```

---

## 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| API 超时 | 自动重试 3 次，间隔递增（5s/10s/20s） |
| API Key 无效 | 提示用户检查 Key |
| 文件编码无法识别 | 尝试常见编码列表，失败则提示用户 |
| PDF 解析失败 | 降级为纯文本提取（放弃排版） |
| 章节拆分结果为空 | 将全文当作一章，提示用户手动拆分 |
| 磁盘空间不足 | 保存前检查，提示用户释放空间 |
