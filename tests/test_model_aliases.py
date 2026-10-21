import asyncio

import pytest

from src.config import Config
from src.data_source import _convert_req_to_official_format
from src.handlers_shared import merge_nai_params
from src.models import NAI5_MEDIUM_MODEL
from src.params import parse_req

SHORT_MODELS = [
    ("5m", NAI5_MEDIUM_MODEL, 14),
    ("5f", "nai-diffusion-5-full", 23),
    ("45f", "nai-diffusion-4-5-full", 23),
    ("nai5m", NAI5_MEDIUM_MODEL, 14),
    ("nai5f", "nai-diffusion-5-full", 23),
    ("nai45f", "nai-diffusion-4-5-full", 23),
]


@pytest.mark.parametrize("default_model", [NAI5_MEDIUM_MODEL, "nai-diffusion-5-full"])
@pytest.mark.parametrize(("alias", "model", "steps"), SHORT_MODELS)
def test_short_alias_switches_only_current_request(
    default_model: str, alias: str, model: str, steps: int,
):
    config = Config()
    config.defaults.model = default_model
    config.defaults.steps = 23
    config.defaults.negative_prompt = "custom negative"
    before = config.model_dump()

    req = asyncio.run(parse_req(f"model={alias}\ntag=test", [], config))
    body = _convert_req_to_official_format(req)
    assert req.model == body["model"] == model
    assert body["parameters"]["steps"] == steps
    if model != NAI5_MEDIUM_MODEL:
        assert body["parameters"]["negative_prompt"] == "custom negative"

    next_req = asyncio.run(parse_req("tag=next request", [], config))
    assert next_req.model == default_model
    assert config.model_dump() == before


@pytest.mark.parametrize(("alias", "model", "steps"), SHORT_MODELS)
def test_direct_short_alias_overrides_preset_model(alias: str, model: str, steps: int):
    config = Config()
    config.defaults.steps = 23
    raw, _, explicit = merge_nai_params(
        ["model=nai5_medium\ntag=preset"],
        f"model={alias}",
    )
    req = asyncio.run(parse_req(raw, [], config))
    assert "model" in explicit
    assert req.model == model
    assert int(req.steps) == steps
    assert req.tag == "preset"


@pytest.mark.parametrize("alias", [alias for alias, _, _ in SHORT_MODELS])
def test_short_alias_preserves_model_permission(alias: str):
    config = Config()
    config.permission.whitelist_only_fields = ["model"]
    with pytest.raises(ValueError, match="白名单"):
        asyncio.run(parse_req(f"model={alias}\ntag=test", [], config))
