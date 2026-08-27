# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow",
#     "numpy",
# ]
# ///

"""Maintainer tool: Extract block palette and colors from Minecraft client.jar."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="client.jar からテクスチャ色を抽出し、パレット JSON を生成します。"
    )
    parser.add_argument("--jar", required=True, help="Minecraft client.jar のパス")
    parser.add_argument("--version", default="26.2", help="Minecraft バージョン (既定: 26.2)")
    parser.add_argument("--rules", default="data/palette/rules_26.2.json", help="タグ付け規則 JSON")
    parser.add_argument("--out", default="data/palette/palette_26.2.json", help="出力先 JSON パス")
    return parser.parse_args()


def load_rules(rules_path: str | Path) -> dict:
    path = Path(rules_path)
    if not path.exists():
        return {"exact_matches": {}, "suffix_patterns": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assign_tags(block_id: str, rules: dict) -> list[str]:
    exact_matches = rules.get("exact_matches", {})
    if block_id in exact_matches:
        return list(exact_matches[block_id])

    tags: set[str] = set()
    suffix_patterns = rules.get("suffix_patterns", [])
    matched_suffix = False

    for item in suffix_patterns:
        suffix = item.get("suffix", "")
        if block_id.endswith(suffix):
            tags.update(item.get("tags", []))
            matched_suffix = True

    if not matched_suffix:
        # Fallback to functional for unknown blocks
        tags.add("functional")

    return sorted(tags)


def resolve_model_textures(zf: zipfile.ZipFile, model_name: str) -> dict[str, str]:
    textures: dict[str, str] = {}
    current = model_name
    visited = set()

    while current and current not in visited:
        visited.add(current)
        if current.startswith("minecraft:"):
            current = current[len("minecraft:"):]
        if not current.startswith("block/"):
            current = f"block/{current}"

        model_path = f"assets/minecraft/models/{current}.json"
        if model_path not in zf.namelist():
            break

        try:
            with zf.open(model_path) as f:
                model_data = json.load(f)
        except Exception:
            break

        if "textures" in model_data:
            for k, v in model_data["textures"].items():
                if k not in textures:
                    textures[k] = v

        current = model_data.get("parent", "")

    # Resolve texture variable references (e.g. "all": "#particle")
    for _ in range(5):
        changed = False
        for k, v in textures.items():
            if v.startswith("#"):
                ref = v[1:]
                if ref in textures and not textures[ref].startswith("#"):
                    textures[k] = textures[ref]
                    changed = True
        if not changed:
            break

    return textures


def choose_side_texture(textures: dict[str, str]) -> str | None:
    for candidate in ("side", "all", "texture", "north", "top", "front"):
        if candidate in textures:
            tex = textures[candidate]
            if not tex.startswith("#"):
                return tex
    return None


def extract_mean_rgb(zf: zipfile.ZipFile, texture_name: str) -> list[int] | None:
    if texture_name.startswith("minecraft:"):
        texture_name = texture_name[len("minecraft:"):]
    if not texture_name.startswith("textures/"):
        texture_name = f"textures/{texture_name}"
    if not texture_name.endswith(".png"):
        texture_name = f"{texture_name}.png"

    path_in_zip = f"assets/minecraft/{texture_name}"
    if path_in_zip not in zf.namelist():
        return None

    try:
        with zf.open(path_in_zip) as f:
            with Image.open(f) as img:
                img_rgba = img.convert("RGBA")
                w, h = img_rgba.size
                # If animated texture, crop first square frame (w x w)
                if h > w:
                    img_rgba = img_rgba.crop((0, 0, w, w))
                arr = np.array(img_rgba, dtype=np.float32)

        alpha = arr[..., 3]
        opaque_mask = alpha > 0
        if not np.any(opaque_mask):
            return None

        rgb = arr[opaque_mask, :3]
        mean_rgb = np.mean(rgb, axis=0)
        return [int(round(c)) for c in mean_rgb]

    except Exception:
        return None


def main() -> int:
    args = parse_args()
    jar_path = Path(args.jar)
    if not jar_path.exists():
        print(f"エラー: JAR ファイルが見つかりません: {jar_path}", file=sys.stderr)
        return 1

    rules = load_rules(args.rules)

    print(f"JAR を読み込み中: {jar_path} ...")
    blocks_out: list[dict] = []

    with zipfile.ZipFile(jar_path, "r") as zf:
        blockstate_files = [
            n for n in zf.namelist()
            if n.startswith("assets/minecraft/blockstates/") and n.endswith(".json")
        ]

        for bs_file in sorted(blockstate_files):
            block_name = Path(bs_file).stem
            block_id = f"minecraft:{block_name}"

            try:
                with zf.open(bs_file) as f:
                    bs_data = json.load(f)
            except Exception:
                continue

            model_name = None
            if "variants" in bs_data:
                first_val = next(iter(bs_data["variants"].values()), None)
                if isinstance(first_val, list) and first_val:
                    model_name = first_val[0].get("model")
                elif isinstance(first_val, dict):
                    model_name = first_val.get("model")
            elif "multipart" in bs_data:
                parts = bs_data.get("multipart", [])
                if parts:
                    apply_val = parts[0].get("apply")
                    if isinstance(apply_val, list) and apply_val:
                        model_name = apply_val[0].get("model")
                    elif isinstance(apply_val, dict):
                        model_name = apply_val.get("model")

            if not model_name:
                continue

            textures = resolve_model_textures(zf, model_name)
            tex_name = choose_side_texture(textures)
            if not tex_name:
                continue

            mean_rgb = extract_mean_rgb(zf, tex_name)
            if not mean_rgb:
                continue

            tags = assign_tags(block_id, rules)
            blocks_out.append({
                "id": block_id,
                "texture": tex_name,
                "rgb": mean_rgb,
                "tags": tags,
            })

    out_data = {
        "schema": 1,
        "minecraft_version": args.version,
        "source": {
            "jar": jar_path.name,
            "sha1": "generated",
        },
        "blocks": blocks_out,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"パレット JSON を出力しました: {out_path} ({len(blocks_out)} ブロック収録)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
