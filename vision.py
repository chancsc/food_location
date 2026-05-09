"""Extract food-shop metadata from a screenshot using Claude Vision."""

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

import anthropic

_MEDIA_TYPES: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

_PROMPT = """\
请分析这张图片，提取美食店铺相关信息{location_ctx}。

以 JSON 格式返回以下字段（图片中没有的信息设为 null）：
{{
  "shop_name":   "店铺名称（中英文均可）",
  "food_types":  ["食物类型1", "食物类型2"],
  "location":    "地区／城市（如：芙蓉、Seremban、吉隆坡）",
  "address":     "完整地址（如果可见）",
  "description": "店铺特色或招牌菜的简短中文描述"
}}

注意事项：
- food_types 请使用中文，尽量具体（如"沙劳越叻沙"而非"面条"）。
- 若图片只展示某种食物而非店铺，请推断该食物所属店铺类型。
- 只输出 JSON，不要附加任何说明文字。
"""


def extract_from_screenshot(
    image_path: str,
    location_hint: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Return extracted shop info dict, or None on failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    path = Path(image_path)
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")
    image_data = base64.standard_b64encode(path.read_bytes()).decode()

    location_ctx = f"（用户提示地区：{location_hint}）" if location_hint else ""
    prompt_text = _PROMPT.format(location_ctx=location_ctx)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
