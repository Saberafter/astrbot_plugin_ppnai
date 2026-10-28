"""Text-only /nai写词, using the same maintained skill as chat planning."""

from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "anima-tag-planner"


def load_planner_rules() -> str:
    rules = (SKILL_ROOT / "SKILL.md").read_text("utf-8")
    expansion = (SKILL_ROOT / "references" / "expansion.md").read_text("utf-8")
    return rules + "\n\n以下是按需使用的扩写参考；仅在用户明确要求扩写时采用：\n" + expansion


async def plan_prompt(ctx, event, config, instructions: str, images: list) -> str:
    # Import AstrBot only at the boundary so rule loading stays offline/testable.
    from astrbot.core.agent.message import ImageURLPart, Message, TextPart
    from .image_io import resolve_image

    provider_id = config.llm.advanced_arg_generation_provider
    if not provider_id:
        provider_id = await ctx.get_current_chat_provider_id(event.unified_msg_origin)
    content = instructions
    if images and config.llm.enable_vision:
        content = [TextPart(text=instructions)]
        for index, image in enumerate(images[:3]):
            content.append(ImageURLPart(image_url=ImageURLPart.ImageURL(
                url=await resolve_image(image), id=f"img{index}",
            )))
    elif images:
        raise ValueError("当前未开启识图，请在配置中开启 enable_vision 后再使用参考图写词")
    response = await ctx.llm_generate(
        chat_provider_id=provider_id,
        contexts=[
            Message(role="system", content=load_planner_rules()),
            Message(role="user", content=content),
        ],
    )
    text = (response.completion_text or "").strip()
    if not text:
        raise ValueError("写词模型返回了空内容，请稍后重试")
    return text
