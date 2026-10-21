import asyncio
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from src.config import Config, DefaultsConfig
from src.data_source import (
    GenerateError,
    _convert_req_to_official_format,
    generate_image,
)
from src.models import AVAILABLE_MODELS, NAI5_MEDIUM_MODEL, NAI5_MEDIUM_NEGATIVE, Req
from src.params import parse_req


def test_medium_can_be_selected_in_config_and_request():
    assert DefaultsConfig(model=NAI5_MEDIUM_MODEL).model == NAI5_MEDIUM_MODEL
    assert Req(model=NAI5_MEDIUM_MODEL).model == NAI5_MEDIUM_MODEL
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "_conf_schema.json").read_text("utf-8"),
    )
    assert NAI5_MEDIUM_MODEL in schema["defaults"]["items"]["model"]["options"]
    assert NAI5_MEDIUM_MODEL in DefaultsConfig.model_json_schema()["properties"]["model"]["options"]


@pytest.mark.parametrize("alias", [
    NAI5_MEDIUM_MODEL, "nai5m", "nai5_medium", "nai5_full_medium",
])
def test_command_aliases_and_conflicting_defaults(alias: str):
    config = Config()
    config.defaults.steps = 28
    config.defaults.sampler = "k_euler"
    config.defaults.cfg = 0.8
    config.defaults.negative_prompt = "custom negative"
    req = asyncio.run(parse_req(f"model={alias}\ntag=1girl", [], config, is_whitelisted=True))
    assert req.model == NAI5_MEDIUM_MODEL
    assert (req.steps, req.sampler, req.cfg, req.other) == ("14", "k_euler_ancestral", "0", "0")
    assert req.negative == NAI5_MEDIUM_NEGATIVE


@pytest.mark.parametrize("opus_free", [True, False])
def test_payload_uses_medium_constraints(opus_free: bool):
    req = Req(
        model=NAI5_MEDIUM_MODEL, tag="1girl", steps="50",
        sampler="k_dpmpp_2m", cfg="0.8", negative="custom", other="5",
    )
    body = _convert_req_to_official_format(req, opus_free_mode=opus_free)
    p = body["parameters"]
    assert body["model"] == NAI5_MEDIUM_MODEL
    assert p["steps"] == 14
    assert p["sampler"] == "k_euler_ancestral"
    assert p["cfg_rescale"] == 0
    assert p["sm"] is p["sm_dyn"] is False
    assert p["negative_prompt"] == NAI5_MEDIUM_NEGATIVE
    assert p["v4_negative_prompt"]["caption"]["base_caption"] == NAI5_MEDIUM_NEGATIVE
    assert p["ucPreset"] == 2
    assert p["params_version"] == 4


def test_final_boundary_normalizes_late_llm_overrides_and_report_values():
    req = Req(model="nai-diffusion-5-full", steps="28", cfg="0.7")
    req.model = NAI5_MEDIUM_MODEL
    req.steps = "40"
    req.sampler = "k_euler"
    req.negative = "late override"
    body = _convert_req_to_official_format(req)
    assert body["parameters"]["steps"] == 14
    assert (req.steps, req.cfg, req.negative) == ("14", "0", NAI5_MEDIUM_NEGATIVE)


@pytest.mark.parametrize("model", [m for m in AVAILABLE_MODELS if m != NAI5_MEDIUM_MODEL])
def test_existing_models_keep_custom_parameters(model: str):
    req = Req(
        model=model, steps="23", sampler="k_euler", cfg="0.4",
        negative="custom negative", other="3",
    )
    p = _convert_req_to_official_format(req)["parameters"]
    assert p["steps"] == 23
    assert p["sampler"] == "k_euler"
    assert p["cfg_rescale"] == 0.4
    assert p["negative_prompt"] == "custom negative"
    assert p["sm"] is p["sm_dyn"] is True
    assert p["params_version"] == 3
    assert p["ucPreset"] == 0


def test_adding_model_does_not_change_global_default():
    assert DefaultsConfig().model == "nai-diffusion-5-curated"


def test_unknown_models_still_fail_validation():
    with pytest.raises(ValidationError):
        Req(model="arbitrary-unknown-model")


def test_generation_round_trip_without_network_or_credentials():
    output = b"mock-generated-image"
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("image.png", output)
    calls = []

    def respond(request: httpx.Request):
        assert request.url.path == "/ai/generate-image"
        body = json.loads(request.content)
        assert body["model"] == NAI5_MEDIUM_MODEL
        assert body["parameters"]["steps"] == 14
        assert body["parameters"]["negative_prompt"] == NAI5_MEDIUM_NEGATIVE
        assert "authorization" not in request.headers
        calls.append(body)
        return httpx.Response(200, content=payload.getvalue())

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test",
            transport=httpx.MockTransport(respond),
        ) as client:
            return await generate_image(client, Req(model=NAI5_MEDIUM_MODEL, tag="test"))

    assert asyncio.run(run()) == output
    assert len(calls) == 1


def test_api_error_is_not_retried_or_changed_to_full():
    calls = []

    def respond(request: httpx.Request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(429, json={"message": "Concurrent generation requests"})

    async def run():
        async with httpx.AsyncClient(
            base_url="https://example.test",
            transport=httpx.MockTransport(respond),
        ) as client:
            return await generate_image(client, Req(model=NAI5_MEDIUM_MODEL))

    with pytest.raises(GenerateError) as error:
        asyncio.run(run())
    assert error.value.status_code == 429
    assert calls == [NAI5_MEDIUM_MODEL]
