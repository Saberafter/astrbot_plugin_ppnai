"""Topic help: /nai lists features; /nai TOPIC shows only that feature."""

import asyncio
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from astrbot.api import logger
from astrbot.api.message_components import Image


ROOT = Path(__file__).resolve().parent.parent
MANUAL_PATH = ROOT / "docs" / "USAGE.md"
ASSETS = ROOT / "docs" / "branch_help_assets"
DOC_URL = (
    "https://github.com/Saberafter/astrbot_plugin_ppnai/blob/main/docs/USAGE.md"
)


ALIASES = {
    "home": ("", "帮助", "菜单", "目录", "总览"),
    "draw": ("画图", "画图命令", "绘图", "ai画图", "draw"),
    "params": ("参数", "参数表", "个性化", "个性化设置", "个性化设置参数", "设置", "模型", "多角色"),
    "presets": ("预设", "预设管理", "preset"),
    "characters": ("角色", "角色tag", "角色tag库", "角色库", "cs"),
    "vision": ("识图", "参考图", "图生图", "画风", "画风迁移", "画风参考", "氛围转移", "角色保持", "i2i", "vibe"),
    "auto": ("自动画图", "自动绘图", "自动"),
    "gallery": ("图库", "图库管理"),
    "quota": ("额度", "额度队列", "队列", "统计", "排行", "账户", "审计"),
    "output": ("输出", "输出方式", "二维码", "网盘", "缓存"),
    "curtain": ("帷幕", "幻影坦克"),
    "admin": ("管理", "管理员", "管理员命令", "黑名单", "白名单"),
}
TOPICS = {alias.casefold(): key for key, aliases in ALIASES.items() for alias in aliases}


def help_query(message):
    """Match only exact, single-line help commands; never swallow draw params."""
    match = re.fullmatch(r"/?nai(?:[ \t]+([^\r\n=]+))?[ \t]*", message.strip(), re.IGNORECASE)
    if match is None:
        return None
    query = (match.group(1) or "").strip()
    return query if query.casefold() in TOPICS else None


def verified_manifest(source_digest):
    manifest = json.loads((ASSETS / "manifest.json").read_text("utf-8"))
    if manifest["source_sha256"] != source_digest:
        raise ValueError("Manual changed; regenerate topic help")
    return manifest


@lru_cache(maxsize=4)
def verified_image(topic, digest):
    data = (ASSETS / (topic + ".png")).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Help image checksum mismatch")
    return data


async def handle_manual_help(plugin, event, query=""):
    topic = TOPICS.get(query.strip().casefold())
    if topic is None:
        yield event.plain_result("没有这个帮助分支。发送 /nai 查看功能总览，例如 /nai 预设、/nai 识图。")
        return
    try:
        source = (await asyncio.to_thread(MANUAL_PATH.read_bytes)).replace(b"\r\n", b"\n")
        manifest = await asyncio.to_thread(verified_manifest, hashlib.sha256(source).hexdigest())
        if plugin.config.general.help_t2i:
            try:
                data = await asyncio.to_thread(verified_image, topic, manifest["images"][topic]["sha256"])
                yield event.chain_result([Image.fromBytes(data)])
                return
            except Exception:
                logger.exception("Topic help image unavailable; falling back to topic text")
        text = await asyncio.to_thread((ASSETS / (topic + ".md")).read_text, encoding="utf-8")
        for start in range(0, len(text), 1000):
            yield event.plain_result(text[start:start + 1000])
    except Exception:
        logger.exception("Topic help unavailable")
        yield event.plain_result("功能帮助暂时不可用，原始文档：" + DOC_URL)
