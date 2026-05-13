# -*- coding: utf-8 -*-
"""DeepSeek API 连通性验证脚本。

用法：
    python check_api.py
    输入 API Key 后自动测试连接
"""

import json
import sys

# Windows 终端 UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests


DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
TEST_PROMPT = "请用中文回复：API连接测试成功，当前模型是？"


def test_api(api_key: str, model: str = "deepseek-chat", timeout: int = 30) -> bool:
    """测试 DeepSeek API 连通性。返回 True 表示成功。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": TEST_PROMPT},
        ],
        "max_tokens": 100,
        "temperature": 0.7,
    }

    print(f"[测试] 正在连接 DeepSeek API (模型: {model})...")
    try:
        resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
        print(f"[成功] API 返回: {reply}")
        print(f"[信息] 模型: {data.get('model', 'N/A')}")
        print(f"[信息] Token 用量: {json.dumps(data.get('usage', {}), ensure_ascii=False)}")
        return True
    except requests.Timeout:
        print("[失败] 请求超时，请检查网络连接")
        return False
    except requests.HTTPError as e:
        print(f"[失败] HTTP 错误: {e}")
        if e.response is not None and e.response.status_code == 401:
            print("  → API Key 无效，请检查是否填写正确")
        return False
    except requests.ConnectionError:
        print("[失败] 网络连接失败，请检查网络或代理设置")
        return False


def main():
    print("=" * 50)
    print("  DeepSeek API 连通性测试")
    print("=" * 50)
    if api_key := input("请输入 DeepSeek API Key (sk-...): ").strip():
        print(f"\n使用 Key: {api_key[:8]}...{api_key[-4:]}")
        success = test_api(api_key)
        if success:
            print("\n[OK] API 连通性测试通过！")
            sys.exit(0)
        else:
            print("\n[FAIL] API 连通性测试失败")
            sys.exit(1)
    else:
        print("未输入 API Key，退出测试")
        sys.exit(1)


if __name__ == "__main__":
    main()
