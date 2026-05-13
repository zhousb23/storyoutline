# -*- coding: utf-8 -*-
"""三步分析的 System / User Prompt 模板。

DeepSeek API 兼容 OpenAI 格式，使用 messages = [system, user]。
所有 Prompt 均要求中文输出。
"""

# ============================================================
# 第一步：单章大纲提取
# ============================================================

SYSTEM_STEP1 = """\
你是一位专业的故事分析助手。你的任务是对给定的章节内容进行剧情结构分析。

请严格按照以下五个要素输出分析结果：

1. **激励事件**：打破主角日常生活的关键事件，推动故事开始的导火索
2. **进展纠葛**：主角在追求目标过程中遇到的障碍、冲突和反转
3. **危机**：主角面临的最大困境或两难选择，故事的最低点
4. **高潮**：矛盾冲突集中爆发的顶点，主角做出关键决定或行动
5. **结局**：本章的结果，冲突的暂时解决或悬念设置

输出要求：
- 每个要素用 2-4 句话概括
- 使用中文
- 按上述顺序输出，每要素前标注名称
- 如果某个要素在本章中不明显，说明「本章未明显体现」"""

USER_STEP1 = """请分析以下章节的剧情结构：

章节标题：{chapter_title}

章节内容：
{chapter_content}"""

# ============================================================
# 第二步：每 50 章阶段性总结
# ============================================================

SYSTEM_STEP2 = """\
你是一位专业的故事分析助手。现在需要对多章的大纲进行阶段性总结。

你将看到一批已提取的章节大纲（每章包含激励事件、进展纠葛、危机、高潮、结局）。

请总结以下内容：
1. **核心剧情推进**：这几十章讲了什么主要故事
2. **关键转折点**：最重要的 3-5 个剧情转折
3. **人物变化**：主角经历了哪些重要变化
4. **伏笔与悬念**：出现了哪些值得注意的伏笔或未解悬念

输出要求：
- 使用中文
- 每部分用 3-5 句话
- 条理清晰，按上述顺序输出"""

USER_STEP2 = """请对以下 {count} 章的剧情大纲进行阶段性总结：

{outlines}"""

# ============================================================
# 第三步：全书故事线总结
# ============================================================

SYSTEM_STEP3 = """\
你是一位资深的故事结构分析师。你将对整本书的阶段性总结进行最终的全局分析。

你将看到若干阶段性总结（每阶段覆盖约 50 章的剧情）。

请分析并输出以下内容：
1. **全书核心冲突**：一句话概括全书最大矛盾
2. **故事线脉络**：将全书划分为 3-5 个大的剧情弧（Arc），每个弧包括：
   - 弧名
   - 覆盖章节范围
   - 核心剧情概述
   - 该弧的高潮点
3. **主角成长轨迹**：主角从开始到结束的变化曲线
4. **全局结构评价**：故事节奏、高潮分布的总体评价

输出要求：
- 使用中文
- 结构清晰，层次分明
- 每个剧情弧的概述控制在 3-5 句话"""

USER_STEP3 = """请对以下阶段性总结进行全书故事线分析：

本书共 {total_chapters} 章。

阶段性总结：
{summaries}"""


# ============================================================
# 人物分析
# ============================================================

SYSTEM_CHARACTER = """\
你是一位专业的文学人物分析专家。请根据已提取的章节大纲，分析文章中的主要人物。

请对每个人物输出：
1. **人物名称**：人物姓名
2. **身份定位**：在故事中的角色（主角/反派/导师/盟友等）
3. **性格特征**：核心性格特点（3-5个关键词 + 简述）
4. **人物弧线**：从出场到当前阶段的变化轨迹
5. **关键事件**：对该人物影响最大的 2-3 个事件
6. **人物关系**：与其他主要人物的关系

输出要求：
- 使用中文
- 按人物逐一分析，每个人物之间用 --- 分隔
- 只分析在已有章节中明确出现过的主要人物（最多 6 人）"""

USER_CHARACTER = """请根据以下章节大纲分析主要人物：

已分析章节数：{chapter_count}章

章节大纲：
{outlines}"""

# ============================================================
# 写作风格分析
# ============================================================

SYSTEM_STYLE = """\
你是一位专业的文学评论家，擅长分析文章的写作风格。

请从以下维度分析文章的写作风格：
1. **语言特点**：用词习惯、句式特点、修辞手法
2. **叙事节奏**：快慢节奏分布、张弛控制
3. **描写风格**：环境描写、心理描写、动作描写的比重和特点
4. **对话风格**：人物对话的特点、口语化程度
5. **整体氛围**：文章营造的整体氛围和情绪基调

输出要求：
- 使用中文
- 每个维度 3-5 句话
- 给出具体的例子佐证分析（引用原文片段）"""

USER_STYLE = """请分析以下文章的写作风格：

已分析章节数：{chapter_count}章

章节大纲（供参考情节）：
{outlines}

原文片段（供分析文风）：
{text_samples}"""


def build_character_messages(outlines: list[dict], chapter_count: int) -> list[dict]:
    """构建人物分析的 API messages。"""
    outlines_text_parts = []
    for o in outlines[:100]:  # 最多取前 100 章大纲
        parts = [
            f"第{o['chapter_index']}章 {o.get('chapter_title', '')}",
            f"  激励事件：{o.get('inciting_incident', '')}",
            f"  进展纠葛：{o.get('progressive_complications', '')}",
            f"  危机：{o.get('crisis', '')}",
            f"  高潮：{o.get('climax', '')}",
            f"  结局：{o.get('resolution', '')}",
        ]
        outlines_text_parts.append("\n".join(parts))

    return [
        {"role": "system", "content": SYSTEM_CHARACTER},
        {"role": "user", "content": USER_CHARACTER.format(
            chapter_count=chapter_count,
            outlines="\n\n".join(outlines_text_parts),
        )},
    ]


def build_style_messages(outlines: list[dict], chapter_count: int, text_samples: str) -> list[dict]:
    """构建写作风格分析的 API messages。"""
    outlines_text_parts = []
    for o in outlines[:20]:  # 风格分析不需要太多大纲
        outlines_text_parts.append(
            f"第{o['chapter_index']}章 {o.get('chapter_title', '')}: "
            f"{o.get('inciting_incident', '')[:80]}"
        )

    return [
        {"role": "system", "content": SYSTEM_STYLE},
        {"role": "user", "content": USER_STYLE.format(
            chapter_count=chapter_count,
            outlines="\n".join(outlines_text_parts),
            text_samples=text_samples[:8000],  # 限制原文长度
        )},
    ]


# ============================================================
# 写作建议分析
# ============================================================

SYSTEM_WRITING_ADVICE = """\
你是一位资深写作导师和文学评论家。请根据已分析的章节内容，提供具体的写作建议。

请从以下维度进行分析，并对每个维度摘抄1-2个优秀原文段落作为范例：

1. **对白描写**：人物对话是否自然、有区分度、推动剧情。摘抄精彩对白段落。
2. **故事结构**：章节结构、节奏控制、悬念设置是否合理。指出写得好的结构处理。
3. **环境描写**：场景氛围营造、细节刻画是否到位。摘抄优秀环境描写。
4. **人物刻画**：人物性格通过言行举止的展现是否生动。摘抄精彩人物描写。
5. **文笔亮点**：其他值得注意的写作技巧和精彩段落。

输出格式要求：
- 每个维度用 3-5 句话评价
- 每个维度下用「📌 优秀段落摘抄：」标注，摘抄原文精彩片段（注明章节）
- 摘抄的段落用引号包裹
- 使用中文"""

USER_WRITING_ADVICE = """请基于以下已分析的文章内容，提供写作建议并摘抄优秀段落：

已分析章节数：{chapter_count}章

原文片段（供分析）：
{text_samples}"""


def build_writing_advice_messages(chapter_count: int, text_samples: str) -> list[dict]:
    """构建写作建议分析的 API messages。"""
    return [
        {"role": "system", "content": SYSTEM_WRITING_ADVICE},
        {"role": "user", "content": USER_WRITING_ADVICE.format(
            chapter_count=chapter_count,
            text_samples=text_samples[:12000],
        )},
    ]


def build_step1_messages(chapter_title: str, chapter_content: str) -> list[dict]:
    """构建第一步（章节大纲）的 API messages。"""
    return [
        {"role": "system", "content": SYSTEM_STEP1},
        {"role": "user", "content": USER_STEP1.format(
            chapter_title=chapter_title,
            chapter_content=chapter_content,
        )},
    ]


def build_step2_messages(outlines: list[dict]) -> list[dict]:
    """构建第二步（阶段性总结）的 API messages。"""
    outlines_text_parts = []
    for o in outlines:
        parts = [
            f"第{o['chapter_index']}章 {o.get('chapter_title', '')}",
            f"  激励事件：{o.get('inciting_incident', '')}",
            f"  进展纠葛：{o.get('progressive_complications', '')}",
            f"  危机：{o.get('crisis', '')}",
            f"  高潮：{o.get('climax', '')}",
            f"  结局：{o.get('resolution', '')}",
        ]
        outlines_text_parts.append("\n".join(parts))
    outlines_text = "\n\n".join(outlines_text_parts)

    return [
        {"role": "system", "content": SYSTEM_STEP2},
        {"role": "user", "content": USER_STEP2.format(
            count=len(outlines),
            outlines=outlines_text,
        )},
    ]


def build_step3_messages(total_chapters: int, summaries: list[dict]) -> list[dict]:
    """构建第三步（全书故事线）的 API messages。"""
    summaries_text_parts = []
    for s in summaries:
        parts = [
            f"阶段{s['section_index']}（第{s['chapter_range'][0]}-{s['chapter_range'][1]}章）：",
            s.get("summary", ""),
        ]
        summaries_text_parts.append("\n".join(parts))
    summaries_text = "\n\n".join(summaries_text_parts)

    return [
        {"role": "system", "content": SYSTEM_STEP3},
        {"role": "user", "content": USER_STEP3.format(
            total_chapters=total_chapters,
            summaries=summaries_text,
        )},
    ]
