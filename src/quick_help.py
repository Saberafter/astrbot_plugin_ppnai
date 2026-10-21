"""Bounded local help rendering; no Markdown renderer or network requests."""

from functools import lru_cache
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


DOC_URL = (
    "https://github.com/dafeiwu666/astrbot_plugin_ppnai/blob/"
    "3fba81326ef789e4ec38cd2a20d589efca5b68f3/docs/USAGE.md"
)


def build_quick_help(config) -> str:
    defaults = config.defaults
    return "\n".join([
        "泡泡画图 · 快速帮助",
        "",
        "基础绘图",
        "下面三行作为同一条消息发送",
        "/nai",
        "tag=1girl, coffee shop, smile",
        "n=1",
        "",
        "常用参数",
        "每行一项，使用英文等号",
        "tag=正向提示词    negative=反向提示词",
        "size=1024x1024    steps=23    seed=12345",
        "s1=预设名    cs1=角色Tag名",
        "",
        "复用与查询",
        "/nai预设列表    查看可用预设",
        "/cs添加 白发角色",
        "1girl, white hair, blue eyes",
        "上面两行一条消息；画图时加 cs1=白发角色",
        "/nai账户    查询订阅与余额（管理员）",
        "/nai审计    查看近期点数消耗（管理员）",
        "",
        "额外输出",
        "按需添加；图片会上传到第三方",
        "QR=true    图片链接二维码",
        "QK=true    夸克分享链接，需先配置夸克",
        "",
        "当前默认参数",
        f"模型：{defaults.model}",
        f"尺寸：{defaults.size}    步数：{defaults.steps}",
        "仅 /nai 查看帮助不生图；扣点以服务端为准。",
        "完整文档见本条消息附带的链接。",
    ])


def _font_path() -> Path:
    spec = find_spec("pillowmd")
    if spec and spec.origin:
        bundled = Path(spec.origin).parent / "data" / "fonts" / "yahei.ttf"
        if bundled.is_file():
            return bundled
    for name in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ):
        path = Path(name)
        if path.is_file():
            return path
    raise FileNotFoundError("No local CJK font available for quick help")


@lru_cache(maxsize=4)
def render_quick_help(text: str) -> bytes:
    if len(text) > 2400 or len(text.splitlines()) > 42:
        raise ValueError("Quick help exceeds its size limit")
    font_path = str(_font_path())
    # BASIC avoids the RAQM newline failure and requires no global patches.
    def font(size):
        return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.BASIC)

    body, heading, title, small = font(27), font(31), font(64), font(23)
    width, padding, line_height = 1080, 54, 39
    blocks = [block.splitlines() for block in text.split("\n\n") if block.strip()]
    if not blocks or len(blocks) > 7:
        raise ValueError("Invalid quick help sections")

    def wrap(line, available):
        lines = []
        current = ""
        for char in line:
            if current and body.getlength(current + char) > available:
                lines.append(current)
                current = ""
            current += char
        lines.append(current)
        return lines

    sections = []
    for block in blocks[1:]:
        lines = []
        for line in block[1:]:
            lines.extend(wrap(line, width - padding * 2 - 52))
        sections.append((block[0], lines))
    height = 238 + sum(83 + line_height * len(lines) for _, lines in sections) + 70
    if height > 1800:
        raise ValueError("Quick help exceeds one bounded page")
    background, surface = "#121c1b", "#192a28"
    white, muted, mint, coral = "#ecf5ef", "#a5bdb5", "#66edcc", "#f3b99f"
    with Image.new("RGB", (width, height), background) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, 7), fill=mint)
        draw.rectangle((width - 170, 0, width, 7), fill=coral)
        for x in range(740, width, 42):
            draw.line((x, 36, x, 196), fill="#20332f")
        for y in range(42, 197, 42):
            draw.line((725, y, width - padding, y), fill="#20332f")
        draw.text((padding, 34), "NOVELAI  /  COMMAND GUIDE", font=small, fill=mint)
        draw.text((padding - 2, 75), "泡泡画图", font=title, fill=white, stroke_width=1)
        draw.text((padding, 165), "提示词  /  预设  /  角色 Tag", font=body, fill=muted)
        draw.text((814, 83), "/nai", font=title, fill=mint)
        draw.line((padding, 220, width - padding, 220), fill="#3b5a50", width=2)

        def draw_line(line, x, y, base=white):
            # Highlight only command names and parameter keys, not user values.
            for token in re.split(r"([A-Za-z][A-Za-z0-9_]*=|/[A-Za-z\u4e00-\u9fff]+)", line):
                color = mint if token.endswith("=") or token.startswith("/") else base
                draw.text((x, y), token, font=body, fill=color)
                x += body.getlength(token)

        y = 247
        for index, (label, lines) in enumerate(sections, 1):
            draw.text((padding, y + 2), f"{index:02}", font=small, fill=coral)
            draw.text((padding + 52, y - 3), label, font=heading, fill=mint)
            y += 49
            if index == 1:
                draw.text((padding + 52, y), lines[0], font=body, fill=muted)
                y += line_height
                code_height = line_height * (len(lines) - 1)
                draw.rectangle(
                    (padding + 52, y - 3, width - padding, y + code_height + 2),
                    fill=surface,
                )
                draw.rectangle((padding + 52, y - 3, padding + 55, y + code_height + 2), fill=mint)
                for line in lines[1:]:
                    draw_line(line, padding + 73, y)
                    y += line_height
            else:
                for line in lines:
                    is_note = line.startswith(("每行", "按需", "上面", "仅 ", "完整文档"))
                    draw_line(line, padding + 52, y, muted if is_note else white)
                    y += line_height
            y += 18
            draw.line((padding + 52, y, width - padding, y), fill="#2a4039")
            y += 16
        draw.text((padding, height - 41), "QUICK REFERENCE", font=small, fill=muted)
        footer = "完整手册见随图链接"
        draw.text((width - padding - small.getlength(footer), height - 41), footer, font=small, fill=muted)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
