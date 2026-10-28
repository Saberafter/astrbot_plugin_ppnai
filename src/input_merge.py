"""Merge parsed preset entries without turning multiline values back into text."""

from .input_parser import CONTROL_KEYS, SELECTOR, Pairs, decode_role


def merge_groups(groups: list[Pairs]) -> tuple[Pairs, dict[str, str], set[str]]:
    scalar_indices: dict[str, int] = {}
    ordered: Pairs = []
    prompts: dict[str, list[str]] = {}
    numbered: dict[int, str] = {}
    explicit: set[str] = set()
    has_legacy = False
    for group in groups:  # low to high priority
        group_roles = {}
        for key, value in group:
            if SELECTOR.fullmatch(key) or key in CONTROL_KEYS:
                continue
            explicit.add(key)
            if key in {"tag", "negative", "prepend_tag", "append_tag", "prepend_negative", "append_negative"}:
                parts = prompts.setdefault(key, [])
                if key.startswith("prepend_"):
                    parts.insert(0, value)
                else:
                    parts.append(value)
            elif key == "role":
                role = decode_role(value)
                if role:
                    group_roles[role["number"]] = value
                else:
                    has_legacy = True
                    ordered.append((key, value))
            elif key == "vibe_transfer":
                # Keep per-image info/strength entries adjacent to their image.
                ordered.append((key, value))
            elif key in {"vibe_transfer_info_extract", "vibe_transfer_ref_strength"}:
                ordered.append((key, value))
            else:
                if key not in scalar_indices:
                    scalar_indices[key] = len(ordered)
                    ordered.append((key, value))
                else:
                    ordered[scalar_indices[key]] = (key, value)
        numbered.update(group_roles)  # replace whole character, never blend attributes
    if has_legacy and numbered:
        raise ValueError("预设与正文不能混用 role= 和编号角色。请统一改为：\n角色1=左\n角色描述")
    wrappers = {key: ", ".join(prompts.get(key, [])) for key in (
        "prepend_tag", "append_tag", "prepend_negative", "append_negative",
    )}
    pairs = [(key, ", ".join(values)) for key, values in prompts.items()]
    pairs.extend(ordered)
    pairs.extend(("role", value) for _, value in sorted(numbered.items()))
    return pairs, wrappers, explicit
