"""Offline chat replay and official character payload contract checks."""

import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import Config
from src.data_source import _convert_req_to_official_format
from src.handlers_shared import extract_batch_count, merge_nai_params
from src.input_parser import parse_position
from src.models import Req, ReqAdditionMultiRole
from src.params import _collect_images_with_replies, parse_params, parse_req

ROOT = Path(__file__).resolve().parents[1]


def request(text, presets=None):
    pairs, _, _ = merge_nai_params(presets or [], text)
    return asyncio.run(parse_req(pairs, [], Config(), is_whitelisted=True))


def load_method(name, class_name="Plugin"):
    """Exercise the actual main.py methods without importing the AstrBot app."""
    tree = ast.parse((ROOT / "main.py").read_text("utf-8-sig"))
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in plugin.body if getattr(node, "name", "") == name)
    method.decorator_list = []
    for node in ast.walk(method):
        if isinstance(node, ast.ImportFrom):
            node.level = 0  # .src.foo -> src.foo in this standalone test namespace
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), method,
    ], type_ignores=[])
    namespace = {
        "asyncio": asyncio, "COMMAND": "nai", "logger": logging.getLogger("test"),
        "parse_req": parse_req, "_collect_images_with_replies": _collect_images_with_replies,
        "LibraryImage": lambda uri: SimpleNamespace(uri=uri),
    }
    exec(compile(ast.fix_missing_locations(module), str(ROOT / "main.py"), "exec"), namespace)
    return namespace[name]


def test_multiline_chat_replay_keeps_weights_newlines_and_chinese():
    body = (
        "1girl, solo,\n\n"
        "tag=white hair, blue eyes,\n"
        "{white dress,\nstanding},\n"
        "model=5f\n"
        "The girl holds a flower. Light falls across her face.\n"
        "source# target#\n\n"
        "花园，阳光"
    )
    req = request("/nai\n" + body)
    assert req.tag == body.replace("1girl, solo,\n\ntag=", "1girl, solo,, ").replace("model=5f\n", "")
    assert req.model == "nai-diffusion-5-full"
    assert request("/nai 1girl, solo").tag == "1girl, solo"


def test_character_sections_global_return_and_parameters_do_not_switch_section():
    req = request(
        "model=5f\n2girls, garden\n"
        "角色2=右\ngirl, black hair\nseed=42\nblack jacket\n"
        "角色1=左\ngirl, white hair\n角色1=B3\nwhite dress\n"
        "负面1=black hair\nblack jacket\n"
        "negative=blurry\nwatermark\n"
        "负面2=white dress\n"
        "tag=sunlight"
    )
    assert req.tag == "2girls, garden, sunlight"
    assert req.negative == "blurry\nwatermark"
    assert req.seed == "42"
    roles = req.addition.multi_role_list
    assert [role.number for role in roles] == [1, 2]
    assert roles[0].prompt == "girl, white hair\nwhite dress"
    assert roles[1].prompt == "girl, black hair\nblack jacket"
    assert roles[0].negative_prompt == "black hair\nblack jacket"
    body = _convert_req_to_official_format(req)
    p = body["parameters"]
    assert body["input"] == p["v4_prompt"]["caption"]["base_caption"] == req.tag
    assert p["v4_negative_prompt"]["caption"]["base_caption"] == req.negative
    assert p["use_coords"] is p["v4_prompt"]["use_coords"] is True
    assert p["v4_prompt"]["use_order"] is True
    for index, role in enumerate(roles):
        center = {"x": [.3, .7][index], "y": .5}
        assert p["characterPrompts"][index] == {
            "prompt": role.prompt, "uc": role.negative_prompt, "center": center,
        }
        assert p["v4_prompt"]["caption"]["char_captions"][index] == {
            "char_caption": role.prompt, "centers": [center],
        }
        assert p["v4_negative_prompt"]["caption"]["char_captions"][index] == {
            "char_caption": role.negative_prompt, "centers": [center],
        }


@pytest.mark.parametrize(("position", "expected"), [
    ("左", (.3, .5)), ("right", (.7, .5)), ("中", (.5, .5)),
    ("左上", (.3, .3)), ("右下", (.7, .7)), ("B3", (.3, .5)),
    ("A1", (.1, .1)), ("E5", (.9, .9)), ("0.2,0.65", (.2, .65)),
    ("自动", None),
])
def test_positions(position, expected):
    assert parse_position(position) == expected


@pytest.mark.parametrize("position", ["nan,.5", "inf,0", "-.1,.5", "1.1,0", "A6", "side", ".2,.3,.4"])
def test_invalid_position(position):
    with pytest.raises(ValueError, match="位置"):
        parse_position(position)


@pytest.mark.parametrize(("text", "error"), [
    ("角色1=左\na\n角色1=右\nb", "位置重复且冲突"),
    ("负面1=blurry", "缺少正向"),
    ("角色1=左\n负面1=bad", "缺少正向"),
    ("角色1=自动\na\n角色2=右\nb", "不能混用自动"),
    ("role=A1|a\n角色1=左\nb", "不能混用"),
    ("model=nai3\n角色1=左\na", "V3"),
    ("model=5m\n角色1=左\na\n负面1=bad", "Medium"),
    ("1girl\n\nmodle=5f", "第 3 行"),
])
def test_actionable_errors(text, error):
    with pytest.raises(ValueError, match=error):
        request(text)


def test_model_coordinates_and_legacy_roles_are_real_characters():
    for model, expected in [("5f", {"x": .2, "y": .65}), ("45f", {"x": .3, "y": .7})]:
        p = _convert_req_to_official_format(
            request(f"model={model}\nrole1=0.2,0.65\nfirst")
        )["parameters"]
        assert p["characterPrompts"][0]["center"] == expected
    p = _convert_req_to_official_format(request(
        "model=5f\nrole=B3|white hair|black hair\nrole=D3|black hair|white hair",
    ))["parameters"]
    assert len(p["characterPrompts"]) == 2
    assert p["characterPrompts"][1]["uc"] == "white hair"
    # Persisted/LLM legacy objects only have the old position field.
    req = Req(model="nai-diffusion-5-full")
    req.addition.multi_role_list = [ReqAdditionMultiRole(prompt="legacy", position="A2")]
    assert _convert_req_to_official_format(req)["parameters"]["characterPrompts"][0]["center"] == {
        "x": .1, "y": .3,
    }


def test_automatic_characters_and_late_model_override():
    req = request("角色1=自动\na\nrole2=auto\nb")
    p = _convert_req_to_official_format(req)["parameters"]
    assert p["use_coords"] is p["v4_prompt"]["use_coords"] is False
    assert len(p["characterPrompts"]) == 2
    req.model = "nai-diffusion-3"
    with pytest.raises(ValueError, match="V3"):
        _convert_req_to_official_format(req)


def test_preset_scalars_prompts_and_whole_character_overrides():
    req = request(
        "model=5f\n角色1=左\ndirect white hair",
        [
            "model=45f\npreset1\n角色1=右\nold black hair\n负面1=old negative",
            "model=nai3\npreset2\n角色2=右\nsecond",
        ],
    )
    assert req.tag == "preset2, preset1"
    assert req.model == "nai-diffusion-5-full"
    roles = req.addition.multi_role_list
    assert roles[0].prompt == "direct white hair"
    assert roles[0].negative_prompt == ""
    assert roles[1].prompt == "second"
    with pytest.raises(ValueError, match="不能混用"):
        request("角色1=左\nfirst", ["role=A1|legacy"])
    assert extract_batch_count(["n=2"], "n=3\nbody", max_n=4) == 3
    assert request("tag=modle=5f").tag == "modle=5f"
    assert request("tag=1girl\ntag=blue eyes\nwhite hair").tag == "1girl, blue eyes\nwhite hair"


def test_main_manual_entry_preset_and_numbered_image_library(monkeypatch):
    from src import params
    from astrbot.api.message_components import Image

    async def resolve(image):
        return image.uri

    monkeypatch.setattr(params, "resolve_first_image", lambda images: resolve(images.pop(0)))
    config = Config()
    config.defaults.default_preset = "default"
    plugin = SimpleNamespace(
        config=config,
        _check_resource_admin=lambda _: False,
        _get_resource_owner=lambda _: "owner",
        _get_user_id=lambda _: "user",
        preset_manager=SimpleNamespace(get_preset=lambda *_: SimpleNamespace(
            content="model=5f\npreset line1\npreset line2",
        )),
        image_library=SimpleNamespace(
            is_accessible=lambda *args: args[0] == "1",
            read_data_uri=lambda *args, **kwargs: "library-data",
        ),
    )
    event = SimpleNamespace(
        message_str="/nai\ns=default\nbody1\nbody2\ni2i=1\nseed=42",
        message_obj=SimpleNamespace(message=[]),
    )
    # LibraryImage must be recognized as an AstrBot image at the parser boundary.
    method = load_method("_parse_args")
    class LibraryImage(Image):
        def __init__(self, uri):
            self.uri = uri
    method.__globals__["LibraryImage"] = LibraryImage
    req, count, names, _, _ = asyncio.run(method(plugin, event, True))
    assert req.tag == "preset line1\npreset line2, body1\nbody2"
    assert req.addition.image_to_image_base64 == "library-data"
    assert req.seed == "42" and count == 1 and names == ["default"]
    event.message_str = "nai\nbody"
    assert asyncio.run(method(plugin, event, True))[2] == ["default"]


def test_alias_permissions_and_image_order_are_preserved():
    config = Config()
    config.permission.whitelist_only_fields = ["role"]
    with pytest.raises(ValueError, match="白名单"):
        asyncio.run(parse_req("角色1=左\nfirst", [], config))
    pairs, _, _ = merge_nai_params([], "v_t=1\nv_t_i_e=0.2\nv_t=other\nv_t_r_s=0.7")
    assert pairs == [
        ("vibe_transfer", "1"), ("vibe_transfer_info_extract", "0.2"),
        ("vibe_transfer", "other"), ("vibe_transfer_ref_strength", "0.7"),
    ]
    assert list(parse_params("负面=模糊\n水印")) == [("negative", "模糊\n水印")]


def test_uploaded_images_follow_parameter_order(monkeypatch):
    from src import params
    from astrbot.api.message_components import Image
    from src.params import parse_req_with_remaining_images

    async def resolve(images):
        return images.pop(0).label

    monkeypatch.setattr(params, "resolve_first_image", resolve)
    images = [Image(), Image(), Image()]
    for index, image in enumerate(images):
        image.label = f"image-{index}"
    pairs, _, _ = merge_nai_params([], "v_t=true\ni2i=true\nprompt")
    req, remaining = asyncio.run(parse_req_with_remaining_images(pairs, images, Config(), True))
    assert req.addition.vibe_transfer_list[0].base64 == "image-0"
    assert req.addition.image_to_image_base64 == "image-1"
    assert remaining == [images[2]]


def test_ai_tool_preserves_the_same_multiline_body_and_restores_event():
    tool_call = load_method("call", "STNaiGenerateImageTool")
    tool_call.__globals__.update(
        STNaiGenerateImageArgs=SimpleNamespace(model_validate=lambda args: SimpleNamespace(**args)),
        _unwrap_tool_context=lambda event: (None, event),
        format_readable_error=str,
    )
    seen = []
    sent = []

    async def handler(event):
        seen.append(event.message_str)
        yield "offline-result"

    async def send(value):
        sent.append(value)

    event = SimpleNamespace(message_str="original request", send=send)
    tool = SimpleNamespace(nai_command_handler_init=handler)
    body = "2girls,\n\n角色1=左\nwhite hair\nwhite dress\n\n角色2=右\nblack hair"
    result = asyncio.run(tool_call(tool, event, instructions="```text\n/nai\n" + body + "\n```"))
    assert seen == ["nai\n" + body]
    assert sent == ["offline-result"]
    assert event.message_str == "original request"
    assert "已执行" in result
