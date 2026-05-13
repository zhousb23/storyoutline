# CLAUDE.md — StoryOutline 项目 AI 助手指引

## 项目简介
这是 StoryOutline（故事大纲分析软件），一个 Windows 桌面应用，通过 DeepSeek API 自动分析长篇小说，提取结构化故事大纲。

## 用户背景
用户为非技术人员，沟通时避免技术黑话，用大白话解释。

---

## 标准文档索引

所有开发规范和标准文档位于 `docs/` 文件夹：

| 文档 | 路径 | 用途 |
|------|------|------|
| 需求规格 | [docs/requirements.md](docs/requirements.md) | 功能需求、非功能需求、约束条件 |
| 技术规格 | [docs/tech-spec.md](docs/tech-spec.md) | 技术栈、架构、API 接口、数据结构 |
| UI 设计 | [docs/design-spec.md](docs/design-spec.md) | 配色、字体、布局、各界面设计 |
| 开发路线 | [docs/dev-roadmap.md](docs/dev-roadmap.md) | 分阶段执行计划，追踪进度 |
| 代码规范 | [docs/code-style.md](docs/code-style.md) | 命名、格式、错误处理、UI 规范 |

---

## 工作指引

### 开发阶段
当前处于第 0 阶段（项目初始化），后续阶段参照 [docs/dev-roadmap.md](docs/dev-roadmap.md)。

### 每阶段工作流
1. 查看 `docs/dev-roadmap.md` 了解当前阶段步骤
2. 阅读对应的标准文档（需求/技术/设计）
3. 按步骤顺序执行，每完成一步更新路线图状态
4. 每步完成后更新 `dev_logs/` 对应日期的日志文件

### 日常记录
- 每次开发会话在 `dev_logs/YYYY-MM-DD.md` 记录：
  - 今日完成了什么
  - 遇到了什么问题及解决方式
  - 下一步计划
  - 当前阶段和进度
- 如果当天文件不存在，新建一个

### 代码存放
- 源代码：`src/`
- 测试代码：`tests/`
- 依赖清单：`requirements.txt`（项目根目录）

### 提交时机
- 每完成一个步骤就提交一次 Git
- 提交信息格式：`[阶段X.Y] 简短描述`

---

## 核心设计决策（勿轻易更改）

1. **UI 框架**：PySide6（Qt for Python），不是 Tkinter 或 Electron
2. **API 服务**：DeepSeek，兼容 OpenAI 接口格式
3. **文件解析**：python-docx + pdfplumber + chardet
4. **打包**：PyInstaller 生成独立 .exe
5. **配色**：淡蓝色主题，详见 [docs/design-spec.md](docs/design-spec.md)
6. **存储**：本地 JSON 文件（.storyoutline 目录），不上传云端

---

## 关键原则

- 稳步推进，每步验证，不做大跨步
- 先逻辑后 UI：核心逻辑在第 2 阶段完成并验证后，再开始 UI
- UI 线程不能阻塞：网络请求必须在后台线程
- API Key 不在代码中写死
- 所有路径使用相对路径或基于项目根的计算路径
