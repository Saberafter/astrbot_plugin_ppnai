"""Run the real command handler with small offline AstrBot boundary doubles."""

import ast
import asyncio
import io
import json
import random
import zipfile
from collections.abc import Awaitable, Callable, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from astrbot.api.message_components import Image, Plain

from src import data_source
from src.config import Config
from src.data_source import GeneratedImage, GenerateError, wrapped_generate
from src.generation_report import (
    build_image_output,
    format_generation_report,
    get_input_image_bytes,
)
from src.models import Req

SOURCE = Path(__file__).resolve().parents[1] / "src" / "handlers_nai.py"


@pytest.mark.parametrize("merged", [False, True])
@pytest.mark.parametrize("batch_count", [1, 2])
@pytest.mark.parametrize("retry", [False, True])
def test_command_delivers_only_successful_image_seeds(
    monkeypatch: pytest.MonkeyPatch, merged: bool, batch_count: int, retry: bool,
):
    config = Config()
    config.request.tokens = ["offline-test"]
    config.quota.enable_quota = False
    config.general.merge_draw_to_chat_record = merged
    config.general.send_generation_details = False
    seed_values = iter(([777] if retry else []) + [0, 123])
    monkeypatch.setattr(data_source.random, "randint", lambda *_: next(seed_values))
    req = Req(model="nai-diffusion-5-full")
    attempts = []
    audit_seeds = []
    background = []

    def respond(request: httpx.Request):
        seed = json.loads(request.content)["parameters"]["seed"]
        attempts.append(seed)
        if retry and len(attempts) == 1:
            return httpx.Response(429, json={"message": "Retry offline"})
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("image.png", f"image-{seed}".encode())
        return httpx.Response(200, content=buffer.getvalue())

    @asynccontextmanager
    async def queue_context(*_args, **_kwargs):
        yield SimpleNamespace(queue_total=1)

    async def no_op(*_args, **_kwargs):
        return None

    async def parse_args(*_args):
        return req, batch_count, [], [], []

    async def retry_generate(call: Callable[[], Awaitable[GeneratedImage]]):
        try:
            return await call()
        except GenerateError:
            return await call()

    async def passthrough_curtain(_plugin: object, _event: object, images: list[bytes]):
        return images

    async def optional_output(*_args):
        return []

    async def record_generation(*_args, **kwargs):
        audit_seeds.append(kwargs["seed"])

    def create_task(coroutine: Coroutine[Any, Any, None], *, name: str):
        background.append(asyncio.create_task(coroutine, name=name))

    event = SimpleNamespace(
        message_str="nai\ntag=test",
        unified_msg_origin="offline",
        get_sender_id=lambda: "test-user",
        get_sender_name=lambda: "test",
        plain_result=lambda text: ("text", text),
        chain_result=lambda chain: ("chain", chain),
    )
    plugin = SimpleNamespace(
        config=config,
        _get_user_id=lambda _event: "test-user",
        user_manager=SimpleNamespace(
            is_blacklisted=lambda _user: False,
            is_whitelisted=lambda _user: True,
            arecord_successful_draw=no_op,
        ),
        _parse_args=parse_args,
        _get_next_token=lambda: "offline-test",
        _token_index=1,
        _create_background_task=create_task,
        _run_with_retry=retry_generate,
        vibe_cache_manager=None,
        image_history_cache=None,
    )
    tree = ast.parse(SOURCE.read_text("utf-8"))
    handler = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_cmd_nai"
    )
    scope = {
        "asyncio": asyncio,
        "random": random,
        "AsyncIterator": object,
        "logger": data_source.logger,
        "Image": Image,
        "Plain": Plain,
        "Node": lambda **kwargs: SimpleNamespace(**kwargs),
        "Nodes": lambda nodes: SimpleNamespace(nodes=nodes),
        "GenerateError": GenerateError,
        "QueueRejected": RuntimeError,
        "wrapped_generate": wrapped_generate,
        "reserve_queue": queue_context,
        "acquire_generation_semaphore": queue_context,
        "read_balance": no_op,
        "record_generation": record_generation,
        "_apply_curtain": passthrough_curtain,
        "_build_optional_output_content": optional_output,
        "build_image_output": build_image_output,
        "format_generation_report": format_generation_report,
        "get_input_image_bytes": get_input_image_bytes,
        "build_draw_reaction_result": lambda *_: None,
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(SOURCE), "exec"), scope)  # noqa: S102 - Trusted local handler.

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            async def get_client():
                return client

            plugin.get_http_client = get_client
            results = [
                result async for result in scope["handle_cmd_nai"](plugin, event, ["wait"])
            ]
            await asyncio.gather(*background)
            return results

    results = asyncio.run(run())
    chains = [value for kind, value in results if kind == "chain"]
    assert len(chains) == 1
    content = chains[0][0].nodes[0].content if merged else chains[0]
    expected = [0, 123][:batch_count]
    assert [item.text.strip() for item in content if isinstance(item, Plain)] == [
        f"seed={seed}" for seed in expected
    ]
    assert sum(isinstance(item, Image) for item in content) == batch_count
    assert audit_seeds == expected
    assert attempts == ([777] if retry else []) + expected
    assert req.seed == ""
