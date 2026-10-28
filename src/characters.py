"""Character capability validation and API coordinate mapping."""

from .input_parser import parse_position
from .models import NAI5_MEDIUM_MODEL, Req


def validate_characters(req: Req) -> None:
    roles = req.addition.multi_role_list
    if not roles:
        return
    if req.model in {"nai-diffusion-3", "nai-diffusion-furry-3"}:
        raise ValueError("V3 不支持独立角色提示词，请切换 model=45f 或 model=5f")
    if any(not role.prompt.strip() for role in roles):
        raise ValueError("每个角色都必须有正向描述")
    if len({role.automatic for role in roles}) > 1:
        raise ValueError("角色位置不能混用自动和明确定位，请为所有角色补齐位置，或全部设为自动")
    if req.model == NAI5_MEDIUM_MODEL and any(role.negative_prompt.strip() for role in roles):
        raise ValueError("V5 Medium 不支持自定义角色负面，请删除角色负面或切换 model=5f")


def character_center(req: Req, role) -> dict[str, float]:
    center = role.center or parse_position(role.position) or (.5, .5)
    if role.automatic:
        center = (.5, .5)
    if req.model.startswith("nai-diffusion-4"):
        grid = (.1, .3, .5, .7, .9)
        # Five equal image regions; exact midpoints snap toward the next cell.
        center = tuple(grid[min(4, int(value * 5))] for value in center)
    return {"x": center[0], "y": center[1]}
