import asyncio
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from astrbot.api.message_components import Image, Plain

from src import data_source
from src.config import Config
from src.data_source import (
    GeneratedImage,
    GenerateError,
    generate_image,
    wrapped_generate,
)
from src.generation_report import build_image_output, format_generation_report
from src.image_history_cache import ImageHistoryCache
from src.models import NAI5_MEDIUM_MODEL, Req


def zipped_image(image: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("image.png", image)
    return buffer.getvalue()


@pytest.mark.parametrize("model", ["nai-diffusion-5-full", NAI5_MEDIUM_MODEL])
def test_random_batch_keeps_each_successful_seed_with_its_image(
    monkeypatch: pytest.MonkeyPatch, model: str,
):
    random_seeds = iter([0, 2**32 - 1])
    monkeypatch.setattr(data_source.random, "randint", lambda *_: next(random_seeds))
    sent_seeds = []
    req = Req(model=model)

    def respond(request: httpx.Request):
        seed = json.loads(request.content)["parameters"]["seed"]
        sent_seeds.append(seed)
        return httpx.Response(200, content=zipped_image(f"image-{seed}".encode()))

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            return [await generate_image(client, req) for _ in range(2)]

    results = asyncio.run(run())
    assert sent_seeds == [0, 2**32 - 1]
    assert [result.seed for result in results] == sent_seeds
    assert [result.image for result in results] == [
        b"image-0", b"image-4294967295",
    ]
    assert req.seed == ""


@pytest.mark.parametrize("seed", [0, 123456, 2**32 - 1])
def test_explicit_seed_is_preserved_without_randomization(
    monkeypatch: pytest.MonkeyPatch, seed: int,
):
    def unexpected_random(*_):
        pytest.fail("An explicit seed must not be randomized")

    monkeypatch.setattr(data_source.random, "randint", unexpected_random)
    req = Req(model="nai-diffusion-5-full", seed=str(seed))

    def respond(request: httpx.Request):
        assert json.loads(request.content)["parameters"]["seed"] == seed
        return httpx.Response(200, content=zipped_image(b"fixed-image"))

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            return await generate_image(client, req)

    assert asyncio.run(run()) == GeneratedImage(image=b"fixed-image", seed=seed)
    assert req.seed == str(seed)


def test_retry_returns_successful_attempt_seed_not_failed_attempt(
    monkeypatch: pytest.MonkeyPatch,
):
    random_seeds = iter([111, 222, 333])
    monkeypatch.setattr(data_source.random, "randint", lambda *_: next(random_seeds))
    attempts = []
    req = Req(model="nai-diffusion-5-full")

    def respond(request: httpx.Request):
        seed = json.loads(request.content)["parameters"]["seed"]
        attempts.append(seed)
        if len(attempts) == 1:
            return httpx.Response(429, json={"message": "Concurrent requests"})
        return httpx.Response(200, content=zipped_image(f"image-{seed}".encode()))

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            with pytest.raises(GenerateError):
                await generate_image(client, req)
            return [await generate_image(client, req) for _ in range(2)]

    results = asyncio.run(run())
    assert attempts == [111, 222, 333]
    assert [result.seed for result in results] == [222, 333]
    assert req.seed == ""


def test_concurrent_results_do_not_overwrite_each_others_seed(
    monkeypatch: pytest.MonkeyPatch,
):
    random_seeds = iter([111, 222])
    monkeypatch.setattr(data_source.random, "randint", lambda *_: next(random_seeds))
    req = Req(model="nai-diffusion-5-full")

    async def respond(request: httpx.Request):
        seed = json.loads(request.content)["parameters"]["seed"]
        await asyncio.sleep(0.01 if seed == 111 else 0)
        return httpx.Response(200, content=zipped_image(f"image-{seed}".encode()))

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            return await asyncio.gather(
                generate_image(client, req), generate_image(client, req),
            )

    assert asyncio.run(run()) == [
        GeneratedImage(image=b"image-111", seed=111),
        GeneratedImage(image=b"image-222", seed=222),
    ]
    assert req.seed == ""


def test_wrapper_still_caches_raw_image_bytes(tmp_path: Path):
    output = b"mock-image-data"
    cache = ImageHistoryCache(
        tmp_path, enabled=True, ttl_days=1, max_size_mb=1,
    )

    def respond(_request: httpx.Request):
        return httpx.Response(200, content=zipped_image(output))

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(respond),
        ) as client:
            async def get_client():
                return client

            return await wrapped_generate(
                Req(model="nai-diffusion-5-full", seed="0"), Config(),
                client_getter=get_client, image_cache=cache, owner_id="test-user",
            )

    assert asyncio.run(run()) == GeneratedImage(image=output, seed=0)
    files = list((cache.base_dir / "generations").iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == output


def test_seed_output_is_next_to_each_image_without_full_parameter_record():
    content = build_image_output([b"first-image", b"second-image"], [0, 9876])
    assert [type(item) for item in content] == [Image, Plain, Image, Plain]
    assert [item.text.strip() for item in content if isinstance(item, Plain)] == [
        "seed=0", "seed=9876",
    ]


def test_mismatched_image_seed_counts_are_not_silently_truncated():
    with pytest.raises(ValueError, match="zip"):
        build_image_output([b"image"], [])


@pytest.mark.parametrize(("seeds", "expected"), [
    ([0], ["seed=0"]),
    ([123, 456], ["seed[1]=123", "seed[2]=456"]),
])
def test_parameter_report_uses_actual_seeds(seeds: list[int], expected: list[str]):
    req = Req(model="nai-diffusion-5-full")
    report = format_generation_report("", req, seeds=seeds)
    assert [line for line in report.splitlines() if line.startswith("seed")] == expected
    assert "(random)" not in report
    assert req.seed == ""


def test_invalid_zip_does_not_return_a_successful_generation():
    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test",
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=b"not-a-zip"),
            ),
        ) as client:
            with pytest.raises(GenerateError):
                await generate_image(client, Req(model="nai-diffusion-5-full"))

    asyncio.run(run())
