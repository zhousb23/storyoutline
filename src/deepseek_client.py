# -*- coding: utf-8 -*-
"""DeepSeek API 客户端 — 封装 API 调用、重试、超时。"""

import time

import requests

from src.prompts import (
    build_step1_messages,
    build_step2_messages,
    build_step3_messages,
    build_character_messages,
    build_style_messages,
    build_writing_advice_messages,
)

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 120  # 单次请求超时秒数
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 20]  # 重试间隔递增


class DeepSeekClient:
    """DeepSeek API 客户端。"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _call_api(self, messages: list[dict]) -> dict:
        """发送 API 请求，含自动重试。返回完整响应 JSON。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.Timeout:
                last_error = "请求超时"
            except requests.ConnectionError:
                last_error = "网络连接失败"
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    raise RuntimeError("API Key 无效，请检查设置") from e
                if e.response is not None and e.response.status_code == 429:
                    last_error = "API 频率限制，等待重试..."
                else:
                    last_error = f"HTTP错误({e.response.status_code if e.response else 'N/A'})"

            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt]
                print(f"  [重试 {attempt + 1}/{MAX_RETRIES}] {last_error}，{delay}秒后重试...")
                time.sleep(delay)

        raise RuntimeError(f"API 请求失败（已重试{MAX_RETRIES}次）: {last_error}")

    @staticmethod
    def _extract_text(response: dict) -> str:
        """从 API 响应中提取文本内容。"""
        return response["choices"][0]["message"]["content"].strip()

    # ---- 三步分析方法 ----

    def analyze_chapter(self, chapter_title: str, chapter_content: str) -> str:
        """第一步：分析单章大纲，返回 AI 生成的文本。

        返回的文本包含五个要素（激励事件、进展纠葛、危机、高潮、结局）。
        """
        messages = build_step1_messages(chapter_title, chapter_content)
        response = self._call_api(messages)
        return self._extract_text(response)

    def summarize_section(self, outlines: list[dict]) -> str:
        """第二步：阶段性总结（每 50 章），返回总结文本。"""
        messages = build_step2_messages(outlines)
        response = self._call_api(messages)
        return self._extract_text(response)

    def generate_storyline(self, total_chapters: int, summaries: list[dict]) -> str:
        """第三步：全书故事线分析，返回全局分析文本。"""
        messages = build_step3_messages(total_chapters, summaries)
        response = self._call_api(messages)
        return self._extract_text(response)

    def analyze_characters(self, outlines: list[dict], chapter_count: int) -> str:
        """人物分析：提取主要人物小传，返回分析文本。"""
        messages = build_character_messages(outlines, chapter_count)
        response = self._call_api(messages)
        return self._extract_text(response)

    def analyze_writing_style(self, outlines: list[dict], chapter_count: int, text_samples: str) -> str:
        """写作风格分析：分析语言风格、叙事节奏等。"""
        messages = build_style_messages(outlines, chapter_count, text_samples)
        response = self._call_api(messages)
        return self._extract_text(response)

    def analyze_writing_advice(self, chapter_count: int, text_samples: str) -> str:
        """写作建议分析：对白、结构、环境、人物刻画 + 优秀段落摘抄。"""
        messages = build_writing_advice_messages(chapter_count, text_samples)
        response = self._call_api(messages)
        return self._extract_text(response)
