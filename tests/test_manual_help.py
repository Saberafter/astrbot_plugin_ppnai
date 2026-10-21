import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import manual_help


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("message, topic", [
    ("/nai", "home"),
    ("nai", "home"),
    (" /NAI  ", "home"),
    ("/nai 预设", "presets"),
    ("/nai 参数", "params"),
    ("/nai 识图", "vision"),
    ("/nai CS", "characters"),
    ("/nai 画图", "draw"),
])
def test_exact_help_commands(message, topic):
    query = manual_help.help_query(message)
    assert query is not None
    assert manual_help.TOPICS[query.casefold()] == topic


@pytest.mark.parametrize("message", [
    "/nai tag=1girl",
    "/nai\nmodel=nai-diffusion-5-full\ntag=1girl",
    "/nai画图",
    "/nai预设列表",
    "/nai 预设 tag=1girl",
    "/nai unknown-topic",
])
def test_drawing_commands_are_not_consumed(message):
    assert manual_help.help_query(message) is None


def test_all_shipped_help_images_are_valid():
    source = manual_help.MANUAL_PATH.read_bytes().replace(b"\r\n", b"\n")
    manifest = manual_help.verified_manifest(hashlib.sha256(source).hexdigest())
    assert set(manifest["images"]) == set(manual_help.ALIASES)
    for topic, image in manifest["images"].items():
        assert manual_help.verified_image(topic, image["sha256"]).startswith(b"\x89PNG")
        assert (manual_help.ASSETS / f"{topic}.md").is_file()


class Event:
    def plain_result(self, text):
        return ("text", text)

    def chain_result(self, components):
        return ("image", components)


def collect_help(plugin, event, query=""):
    async def collect():
        return [item async for item in manual_help.handle_manual_help(plugin, event, query)]

    return asyncio.run(collect())


def test_text_help_works_with_windows_line_endings(monkeypatch, tmp_path):
    manual = tmp_path / "USAGE.md"
    source = manual_help.MANUAL_PATH.read_bytes().replace(b"\r\n", b"\n")
    manual.write_bytes(source.replace(b"\n", b"\r\n"))
    monkeypatch.setattr(manual_help, "MANUAL_PATH", manual)
    plugin = SimpleNamespace(config=SimpleNamespace(general=SimpleNamespace(help_t2i=False)))
    result = collect_help(plugin, Event())
    assert result and all(item[0] == "text" for item in result)
    assert "暂时不可用" not in "".join(item[1] for item in result)


def test_missing_image_falls_back_to_topic_text(monkeypatch, tmp_path):
    source = b"manual\n"
    manual = tmp_path / "USAGE.md"
    manual.write_bytes(source)
    (tmp_path / "home.md").write_text("Topic text", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "images": {"home": {"sha256": "missing-image"}},
    }), encoding="utf-8")
    monkeypatch.setattr(manual_help, "MANUAL_PATH", manual)
    monkeypatch.setattr(manual_help, "ASSETS", tmp_path)
    plugin = SimpleNamespace(config=SimpleNamespace(general=SimpleNamespace(help_t2i=True)))
    assert collect_help(plugin, Event()) == [("text", "Topic text")]


def test_stale_manual_links_to_fork(monkeypatch, tmp_path):
    manual = tmp_path / "USAGE.md"
    manual.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(manual_help, "MANUAL_PATH", manual)
    plugin = SimpleNamespace(config=SimpleNamespace(general=SimpleNamespace(help_t2i=False)))
    result = collect_help(plugin, Event())
    assert "Saberafter/astrbot_plugin_ppnai" in result[0][1]


def test_obsolete_help_is_removed():
    assert not (ROOT / "src" / "quick_help.py").exists()
    assert not list((ROOT / "docs" / "help_assets").glob("*"))
