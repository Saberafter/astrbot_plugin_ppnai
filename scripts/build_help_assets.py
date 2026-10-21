"""Rebuild selected topic images and their checksums without a running bot."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import pillowmd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "branch_help_assets"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    sources = {p.stem: p for p in ASSETS.glob("*.md")}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", action="append", choices=sorted(sources))
    args = parser.parse_args()
    selected = set(args.topic or sources)
    path = ASSETS / "manifest.json"
    manifest = json.loads(path.read_text("utf-8"))
    # Historical source line ranges are unused and become stale after doc edits.
    manifest.pop("chunks", None)
    source = (ROOT / "docs" / "USAGE.md").read_bytes().replace(b"\r\n", b"\n")
    manifest["source_sha256"] = digest(source)
    manifest["source_lines"] = len(source.splitlines())
    style = pillowmd.MdStyle()
    renderer = f"pillowmd {version('pillowmd')}, Pillow {version('Pillow')}, autoPage=False"
    for topic, markdown in sorted(sources.items()):
        png = ASSETS / f"{topic}.png"
        if topic in selected:
            result = style.Render(
                text=markdown.read_text("utf-8"),
                useImageUrl=False,
                autoPage=False,
            )
            if len(result.images) != 1:
                raise ValueError(f"Expected one help image for {topic}")
            result.images[0].save(png, format="PNG")
        image_data = png.read_bytes()
        with Image.open(png) as image:
            size = list(image.size)
            image.verify()
        entry = manifest["images"][topic]
        entry.update({
            "size": size,
            "bytes": len(image_data),
            "sha256": digest(image_data),
            "markdown_sha256": digest(markdown.read_bytes().replace(b"\r\n", b"\n")),
        })
        if topic in selected:
            entry["renderer"] = renderer
            print(f"Rebuilt {topic}: {size[0]}x{size[1]}, {len(image_data)} bytes")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
