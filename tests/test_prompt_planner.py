"""The prompt command calls only a fake LLM and never the drawing pipeline."""

import asyncio
import sys
from types import ModuleType, SimpleNamespace

import pytest

from src.config import Config
from src.prompt_planner import SKILL_ROOT, load_planner_rules, plan_prompt
from tests.test_multiline_characters import load_method


def test_shared_skill_text_and_text_only_llm(monkeypatch):
    messages = ModuleType("astrbot.core.agent.message")
    messages.Message = lambda **kwargs: SimpleNamespace(**kwargs)
    messages.ImageURLPart = SimpleNamespace()
    messages.TextPart = lambda **kwargs: SimpleNamespace(**kwargs)
    monkeypatch.setitem(sys.modules, "astrbot.core.agent.message", messages)
    calls = []

    async def provider(umo):
        assert umo == "offline"
        return "fake-provider"

    async def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(completion_text="/nai\n1girl\n\n中文对照\n1名女孩")

    config = Config()
    ctx = SimpleNamespace(get_current_chat_provider_id=provider, llm_generate=generate)
    event = SimpleNamespace(unified_msg_origin="offline")
    result = asyncio.run(plan_prompt(ctx, event, config, "白发少女", []))
    assert result.startswith("/nai\n")
    assert calls[0]["chat_provider_id"] == "fake-provider"
    system, user = calls[0]["contexts"]
    assert system.content == load_planner_rules()
    assert (SKILL_ROOT / "SKILL.md").read_text("utf-8") in system.content
    assert user.content == "白发少女"
    assert len(calls) == 1

    config.llm.advanced_arg_generation_provider = "configured"
    asyncio.run(plan_prompt(ctx, event, config, "白发少女", []))
    assert calls[1]["chat_provider_id"] == "configured"
    config.llm.enable_vision = False
    with pytest.raises(ValueError, match="识图"):
        asyncio.run(plan_prompt(ctx, event, config, "参考图", [object()]))


def test_command_delivers_copyable_command_and_separate_translation(monkeypatch):
    from src import prompt_planner
    calls = []

    async def planner(*args):
        calls.append(args)
        return "/nai\n2girls\n角色1=左\nwhite hair\n角色2=右\nblack hair\n\n中文对照\n两名女孩"

    monkeypatch.setattr(prompt_planner, "plan_prompt", planner)
    handler = load_method("cmd_nai_plan")
    handler.__globals__["format_readable_error"] = str
    # No drawing, quota manager or NAI token is exposed by this fake plugin.
    plugin = SimpleNamespace(context=object(), config=Config())
    event = SimpleNamespace(
        message_str="nai写词 两名女孩站在花园",
        message_obj=SimpleNamespace(message=[]),
        plain_result=lambda text: text,
    )

    async def run():
        return [result async for result in handler(plugin, event)]

    replies = asyncio.run(run())
    assert len(calls) == 1
    assert calls[0][3] == "两名女孩站在花园"
    assert replies[0] == "/nai\n2girls\n角色1=左\nwhite hair\n角色2=右\nblack hair"
    assert replies[1] == "中文对照\n两名女孩"
    event.message_str = "nai写词"
    assert "用法" in asyncio.run(run())[0]
    assert len(calls) == 1
