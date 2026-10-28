"""Shared structured preset merging and explicit AI request overrides."""

from .input_merge import merge_groups
from .input_parser import Pairs
from .models import Req
from .params import parse_params


def _groups(preset_contents: list[str], direct_text: str | Pairs) -> list[Pairs]:
    return [list(parse_params(text)) for text in reversed(preset_contents)] + [
        list(parse_params(direct_text))
    ]


def merge_nai_params(
    preset_contents: list[str],
    direct_text: str | Pairs = "",
) -> tuple[Pairs, dict[str, str], set[str]]:
    """Direct scalars override s1, s2, ...; numbered roles replace whole entries.

    Return parsed pairs, wrappers and explicit canonical IDs. Multiline values
    remain values all the way to the request assembler.
    """
    return merge_groups(_groups(preset_contents, direct_text))


def extract_batch_count(
    preset_contents: list[str],
    direct_text: str | Pairs = "",
    *,
    max_n: int = 0,
) -> int:
    count = 1
    for group in _groups(preset_contents, direct_text):
        for key, value in group:
            if key != "n" or not value:
                continue
            if not value.isdigit() or int(value) < 1:
                raise ValueError("参数 n 必须是大于等于 1 的整数")
            count = int(value)
    if max_n > 0 and count > max_n:
        raise ValueError(f"参数 n 不能超过 {max_n}")
    return count


def _apply_prompt_wrappers(base: str, prepend: str, append: str) -> str:
    return ", ".join(part.strip() for part in (prepend, base, append) if part.strip())


def apply_explicit_overrides(
    req: Req,
    user_req: Req,
    explicit_ids: set[str],
    wrappers: dict[str, str],
) -> None:
    """Apply user params and wrappers onto an LLM-generated request."""
    for key in (
        "model", "size", "seed", "steps", "scale", "cfg", "sampler",
        "noise_schedule", "other", "i2i_force", "i2i_cl", "artist", "data",
    ):
        if key in explicit_ids:
            setattr(req, key, getattr(user_req, key))

    if "character_keep" in explicit_ids and user_req.addition.character_keep:
        req.addition.character_keep = user_req.addition.character_keep
    if "role" in explicit_ids and user_req.addition.multi_role_list:
        req.addition.multi_role_list = user_req.addition.multi_role_list
    if user_req.addition.vibe_transfer_list and (
        "vibe_transfer_info_extract" in explicit_ids
        or "vibe_transfer_ref_strength" in explicit_ids
    ):
        req.addition.vibe_transfer_list = user_req.addition.vibe_transfer_list

    for key in ("tag", "negative"):
        if key in explicit_ids:
            setattr(req, key, getattr(user_req, key))
        elif f"prepend_{key}" in explicit_ids or f"append_{key}" in explicit_ids:
            setattr(req, key, _apply_prompt_wrappers(
                getattr(req, key),
                wrappers.get(f"prepend_{key}", ""),
                wrappers.get(f"append_{key}", ""),
            ))
