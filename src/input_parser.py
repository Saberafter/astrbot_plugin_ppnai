"""Parse chat text once; keep multiline captions as values, never as kv text."""

from __future__ import annotations

import json
import math
import re

Pairs = list[tuple[str, str]]
ROLE_PREFIX = "__character__:"
CONTROL_KEYS = {"n", "ds", "QR", "QK", "qr", "qk", "curtain", "帷幕"}
SELECTOR = re.compile(r"(?:s|cs)(?:[1-9]\d*)?$")
NUMBERED = re.compile(r"(角色|role|负面|negative)([1-9]\d*)$", re.I)
KEY_VALUE = re.compile(r"^([\w.-]+)\s*=(.*)$")


def parse_position(value: str) -> tuple[float, float] | None:
    value = value.strip().lower()
    if value in {"", "自动", "auto", "automatic"}:
        return None
    names = {
        "左": (.3, .5), "右": (.7, .5), "中": (.5, .5), "中间": (.5, .5),
        "上": (.5, .3), "下": (.5, .7), "左上": (.3, .3), "右上": (.7, .3),
        "左下": (.3, .7), "右下": (.7, .7),
        "left": (.3, .5), "right": (.7, .5), "center": (.5, .5),
        "top": (.5, .3), "bottom": (.5, .7),
        "top-left": (.3, .3), "top-right": (.7, .3),
        "bottom-left": (.3, .7), "bottom-right": (.7, .7),
    }
    if value in names:
        return names[value]
    if re.fullmatch(r"[a-e][1-5]", value):
        return (round((ord(value[0]) - ord("a")) * .2 + .1, 1),
                round((int(value[1]) - 1) * .2 + .1, 1))
    try:
        x, y = (float(v.strip()) for v in value.replace("，", ",").split(","))
        if all(math.isfinite(v) and 0 <= v <= 1 for v in (x, y)):
            return x, y
    except ValueError:
        pass
    raise ValueError(f"无效角色位置 {value!r}，请用左、右、自动、A1～E5 或 0～1 的 x,y 坐标")


def strip_command(text: str) -> str:
    return re.sub(r"^/?nai(?=\s|$)\s?", "", text.strip(), count=1)


def decode_role(value: str) -> dict | None:
    return json.loads(value[len(ROLE_PREFIX):]) if value.startswith(ROLE_PREFIX) else None


def encode_role(role: dict) -> str:
    return ROLE_PREFIX + json.dumps(role, ensure_ascii=False)


def parse_input(text: str | Pairs, aliases: dict[str, str]) -> Pairs:
    if not isinstance(text, str):
        return list(text)
    text = strip_command(text)
    pairs: Pairs = []
    captions: dict[str, list[list[str]]] = {}
    explicit_captions: set[str] = set()
    roles: dict[int, dict] = {}
    section = "tag"
    old_roles = False
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        match = KEY_VALUE.fullmatch(line)
        if match:
            key, value = match[1], match[2].strip()
            numbered = NUMBERED.fullmatch(key)
            if numbered:
                number = int(numbered[2])
                role = roles.setdefault(number, {
                    "number": number, "prompt": [], "negative_prompt": [],
                    "center": None, "automatic": True, "declared": False,
                })
                if numbered[1].lower() in {"角色", "role"}:
                    center = parse_position(value)
                    if value:
                        previous = role.get("_position")
                        if "_position" in role and previous != center:
                            raise ValueError(f"第 {line_number} 行：角色{number} 的位置重复且冲突")
                        role["_position"] = center
                        role["center"] = center
                        role["automatic"] = center is None
                    role["declared"] = True
                    section = f"role{number}"
                else:
                    section = f"negative{number}"
                    if value:
                        role["negative_prompt"].append(value)
                continue
            canonical = aliases.get(key)
            if canonical in {
                "tag", "negative", "prepend_tag", "append_tag",
                "prepend_negative", "append_negative",
            }:
                section = canonical
                explicit_captions.add(section)
                captions.setdefault(section, []).append([value])
                continue
            if canonical or key in CONTROL_KEYS or SELECTOR.fullmatch(key):
                canonical = canonical or key
                old_roles |= canonical == "role"
                pairs.append((canonical, value))
                continue
            raise ValueError(
                f"第 {line_number} 行：未知参数 `{key}`。"
                "若这是提示词正文，请写成 tag=" + line
            )
        if section.startswith("role") and section[4:].isdigit():
            roles[int(section[4:])]["prompt"].append(raw)
        elif section.startswith("negative") and section[8:].isdigit():
            roles[int(section[8:])]["negative_prompt"].append(raw)
        else:
            captions.setdefault(section, [[]])[-1].append(raw)

    for key, blocks in captions.items():
        # Legacy repeated tag=/negative= are separate prompt fragments.
        # Only explicit section boundaries get a comma; body newlines stay intact.
        value = ", ".join(part for block in blocks if (part := "\n".join(block).strip()))
        if value or key in explicit_captions:
            pairs.append((key, value))
    if old_roles and roles:
        raise ValueError("不能混用 role= 和编号角色分区。请改为：\n角色1=左\n角色描述\n负面1=\n角色负面")
    for number, role in sorted(roles.items()):
        role.pop("_position", None)
        role["prompt"] = "\n".join(role["prompt"]).strip()
        role["negative_prompt"] = "\n".join(role["negative_prompt"]).strip()
        pairs.append(("role", encode_role(role)))
    return pairs
