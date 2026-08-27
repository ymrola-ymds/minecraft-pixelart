"""Command-line interface for minecraft-pixelart."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import NoReturn, Sequence
import numpy as np

from mcpixelart.commands import generate_commands
from mcpixelart.datapack import write_datapack
from mcpixelart.errors import ImageProcessError, PixelArtError, UsageError
from mcpixelart.imaging import process_image
from mcpixelart.layout import Placement
from mcpixelart.mapping import map_pixels_to_blocks
from mcpixelart.palette import load_palette
from mcpixelart.preview import save_preview

NAME_PATTERN = re.compile(r"^[a-z0-9_.-]+$")
FUNCTION_PATTERN = re.compile(r"^[a-z0-9_./-]+$")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def sanitize_resource_name(stem: str) -> str:
    """Sanitize input file stem to valid Minecraft resource name [a-z0-9_.-]."""
    s = stem.lower()
    s = re.sub(r"[\s\+]+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    s = s.strip("._-")
    if not s:
        # Fallback for non-ASCII (e.g. Japanese) names
        h = hashlib.md5(stem.encode("utf-8")).hexdigest()[:6]
        return f"pixelart_{h}"
    return s


def validate_resource_name(name: str, label: str, allow_slash: bool = False) -> None:
    pattern = FUNCTION_PATTERN if allow_slash else NAME_PATTERN
    if not pattern.match(name):
        allowed_chars = "小文字英数字, _, ., -" + (", /" if allow_slash else "")
        raise UsageError(
            f"{label} '{name}' は Minecraft の命名規則に違反しています。使用可能文字: {allowed_chars}"
        )


def find_available_images() -> list[Path]:
    """Find image files in images/ directory and current directory."""
    images_dir = Path("images")
    found_paths: list[Path] = []
    seen = set()

    if images_dir.exists() and images_dir.is_dir():
        for p in images_dir.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                if p.resolve() not in seen:
                    found_paths.append(p)
                    seen.add(p.resolve())

    current_dir = Path(".")
    for p in current_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            if p.resolve() not in seen:
                found_paths.append(p)
                seen.add(p.resolve())

    return sorted(found_paths, key=lambda x: str(x))


def prompt_select_image(is_interactive: bool) -> str:
    """Prompt user to select an image from available images if not specified."""
    if not is_interactive:
        raise UsageError("入力画像 (IMAGE) が指定されていません。画像パスを指定してください。")

    images = find_available_images()
    if not images:
        raise ImageProcessError(
            "画像ファイルが見つかりません。images/ フォルダに画像 (.png 等) を配置するか、引数で画像パスを指定してください。"
        )

    print("入力画像を選択してください:")
    for idx, img_path in enumerate(images, start=1):
        print(f"  {idx}) {img_path}")

    while True:
        try:
            choice = input(f"選択 [1-{len(images)}] (既定: 1): ").strip()
        except EOFError:
            return str(images[0])

        if choice == "":
            return str(images[0])
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(images):
                return str(images[num - 1])

        print(f"1 から {len(images)} の数値を入力してください。\n", file=sys.stderr)


def prompt_orientation_and_facing(
    specified_orientation: str | None,
    specified_facing: str | None,
    is_interactive: bool,
) -> tuple[str, str]:
    """Resolve orientation and facing through CLI arguments or interactive prompts."""
    # Case 1: --facing specified without --orientation -> wall + specified facing
    if specified_orientation is None and specified_facing is not None:
        return "wall", specified_facing

    # Case 2: --orientation floor -> floor + default facing (ignored in floor)
    if specified_orientation == "floor":
        if specified_facing is not None:
            print("警告: 床配置 (--orientation floor) では --facing の指定は無視されます。", file=sys.stderr)
        return "floor", "south"

    # Case 3: Both specified
    if specified_orientation == "wall" and specified_facing is not None:
        return "wall", specified_facing

    # Case 4: Needs prompt or default fallback
    if not is_interactive:
        if specified_orientation is None and specified_facing is None:
            print("警告: 配置の向きが未指定のため、既定値（壁・南向き）を採用しました。", file=sys.stderr)
            return "wall", "south"
        elif specified_orientation == "wall" and specified_facing is None:
            print("警告: 壁の正面が未指定のため、既定値（南向き）を採用しました。", file=sys.stderr)
            return "wall", "south"

    # Interactive prompt
    if specified_orientation is None and specified_facing is None:
        while True:
            try:
                print("配置の向きを選んでください。")
                print("  1) 壁・南向き（垂直 / 南から見る）  [既定]")
                print("  2) 壁・北向き（垂直 / 北から見る）")
                print("  3) 壁・東向き（垂直 / 東から見る）")
                print("  4) 壁・西向き（垂直 / 西から見る）")
                print("  5) 床（水平・地面に平行）")
                choice = input("選択 [1]: ").strip()
            except EOFError:
                return "wall", "south"

            if choice in ("", "1"):
                return "wall", "south"
            elif choice == "2":
                return "wall", "north"
            elif choice == "3":
                return "wall", "east"
            elif choice == "4":
                return "wall", "west"
            elif choice == "5":
                return "floor", "south"
            else:
                print("1 から 5 の数値を入力してください。\n", file=sys.stderr)

    if specified_orientation == "wall" and specified_facing is None:
        while True:
            try:
                print("壁の正面を選んでください。")
                print("  1) 南向き（南から見る）  [既定]")
                print("  2) 北向き（北から見る）")
                print("  3) 東向き（東から見る）")
                print("  4) 西向き（西から見る）")
                choice = input("選択 [1]: ").strip()
            except EOFError:
                return "wall", "south"

            if choice in ("", "1"):
                return "wall", "south"
            elif choice == "2":
                return "wall", "north"
            elif choice == "3":
                return "wall", "east"
            elif choice == "4":
                return "wall", "west"
            else:
                print("1 から 4 の数値を入力してください。\n", file=sys.stderr)

    return "wall", "south"


def prompt_gravity_blocks(
    specified_gravity: str | None,
    is_interactive: bool,
) -> bool:
    """Resolve whether to use gravity blocks through argument or interactive prompt."""
    if specified_gravity == "use":
        return True
    elif specified_gravity == "exclude":
        return False

    if not is_interactive:
        print("警告: 落下ブロックの設定が未指定のため、既定値（使わない）を採用しました。", file=sys.stderr)
        return False

    while True:
        try:
            print("砂・砂利・コンクリートパウダーなどの落下ブロックを使いますか。")
            print("下に空間があると落ちて絵が崩れます。")
            print("  1) 使わない（パレットから外す）  [既定]")
            print("  2) 使う")
            choice = input("選択 [1]: ").strip()
        except EOFError:
            return False

        if choice in ("", "1"):
            return False
        elif choice == "2":
            return True
        else:
            print("1 または 2 を入力してください。\n", file=sys.stderr)


def get_default_palette_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "palette" / "palette_26.2.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixelart.py",
        description="画像を Minecraft Java Edition 26.2 用のデータパックに変換します。",
    )

    parser.add_argument(
        "image",
        metavar="IMAGE",
        nargs="?",
        default=None,
        help="入力画像ファイルのパス (未指定時は images/ から選択)",
    )
    parser.add_argument("-W", "--width", type=int, required=True, help="横のブロック数（回転前）")
    parser.add_argument("-H", "--height", type=int, required=True, help="縦のブロック数（回転前）")

    parser.add_argument(
        "--orientation",
        choices=["floor", "wall"],
        default=None,
        help="配置の向き (floor: 水平・床 / wall: 垂直・壁)",
    )
    parser.add_argument(
        "--facing",
        choices=["south", "north", "east", "west"],
        default=None,
        help="壁の正面方角 (south / north / east / west)",
    )
    parser.add_argument(
        "--rotate",
        type=int,
        choices=[0, 90, 180, 270],
        default=0,
        help="時計回りの回転角度 (0, 90, 180, 270)",
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        default=False,
        help="左右反転（回転の後に適用）",
    )
    parser.add_argument(
        "--coords",
        choices=["relative", "absolute"],
        default="relative",
        help="座標指定方式 (relative / absolute)",
    )
    parser.add_argument(
        "--origin",
        type=int,
        nargs=3,
        metavar=("X", "Y", "Z"),
        default=None,
        help="絶対座標時の開始原点 (X Y Z)",
    )
    parser.add_argument(
        "--pack-name",
        default=None,
        help="データパックのフォルダ名 (未指定時は画像ファイル名から自動設定)",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help="名前空間 (未指定時は画像ファイル名から自動設定)",
    )
    parser.add_argument(
        "--function",
        default=None,
        help="エントリ関数名 (既定: build)",
    )
    parser.add_argument(
        "--out",
        default="./output",
        help="出力ルートディレクトリ (既定: ./output)",
    )
    parser.add_argument(
        "--preview",
        default=None,
        help="プレビュー画像の保存先パス (既定: <out>/previews/<画像名>.png)",
    )
    parser.add_argument(
        "--palette",
        default=None,
        help="パレット JSON ファイルのパス",
    )
    parser.add_argument(
        "--max-commands",
        type=int,
        default=65000,
        help="mcfunction ファイルあたりの最大コマンド数 (既定: 65000)",
    )
    parser.add_argument(
        "--gravity-blocks",
        choices=["use", "exclude"],
        default=None,
        help="落下ブロック（砂・砂利等）の利用 (use / exclude)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="対話質問をスキップし、すべて既定値を採用する",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code != 0 else 0

    try:
        # Basic validation
        if args.width <= 0 or args.height <= 0:
            raise UsageError("幅 (--width) および高さ (--height) は 1 以上の整数を指定してください。")

        is_interactive = (not args.yes) and sys.stdin.isatty() and sys.stdout.isatty()

        # Image path resolution
        image_path = args.image
        if not image_path:
            image_path = prompt_select_image(is_interactive=is_interactive)

        # Determine automatic names from image file stem
        stem = Path(image_path).stem
        default_res_name = sanitize_resource_name(stem)

        pack_name = args.pack_name if args.pack_name is not None else default_res_name
        namespace = args.namespace if args.namespace is not None else default_res_name
        function_name = args.function if args.function is not None else "build"

        validate_resource_name(pack_name, "データパック名 (--pack-name)")
        validate_resource_name(namespace, "名前空間 (--namespace)")
        validate_resource_name(function_name, "関数名 (--function)", allow_slash=True)

        if args.coords == "absolute":
            if args.origin is None:
                raise UsageError("絶対座標 (--coords absolute) を指定した場合は --origin X Y Z が必須です。")
            origin = tuple(args.origin)
        else:
            if args.origin is not None:
                print("警告: 相対座標 (--coords relative) では --origin の指定は無視されます。", file=sys.stderr)
            origin = None

        # Prompt / resolve orientation & facing
        orientation, facing = prompt_orientation_and_facing(
            args.orientation,
            args.facing,
            is_interactive=is_interactive,
        )

        # Prompt / resolve gravity blocks
        use_gravity = prompt_gravity_blocks(
            args.gravity_blocks,
            is_interactive=is_interactive,
        )

        if orientation == "wall" and use_gravity:
            print("警告: 壁配置で落下ブロックを使用しています。下に支えが無いと落下します。", file=sys.stderr)

        # Print resolved settings
        facing_ja = {"south": "南向き", "north": "北向き", "east": "東向き", "west": "西向き"}.get(facing, facing)
        orient_str = "床（水平）" if orientation == "floor" else f"壁・{facing_ja}（垂直）"
        gravity_str = "使う" if use_gravity else "使わない"
        print(f"画像: {image_path}")
        print(f"向き: {orient_str} / 落下ブロック: {gravity_str}")
        print(f"データパック名: {pack_name} / 関数: {namespace}:{function_name}")

        # Palette path
        palette_path = Path(args.palette) if args.palette else get_default_palette_path()

        # Load Palette
        palette = load_palette(palette_path, use_gravity_blocks=use_gravity)

        # Process image
        rgb_grid, opaque_grid, orig_size = process_image(
            image_path=image_path,
            width=args.width,
            height=args.height,
            rotation=args.rotate,
            mirror_horizontal=args.mirror,
        )

        final_h, final_w = opaque_grid.shape
        orig_w, orig_h = orig_size

        # Check aspect ratio discrepancy
        orig_aspect = orig_w / orig_h
        target_aspect = args.width / args.height
        aspect_diff = abs(target_aspect - orig_aspect) / orig_aspect
        if aspect_diff >= 0.10:
            print(
                f"警告: 指定サイズのアスペクト比 (横 {args.width} × 縦 {args.height}, 比率: {target_aspect:.2f}) が"
                f"元画像 (横 {orig_w} × 縦 {orig_h}, 比率: {orig_aspect:.2f}) と大きく異なります。絵が歪む可能性があります。",
                file=sys.stderr,
            )

        if final_w > orig_w or final_h > orig_h:
            print(
                f"警告: 指定サイズ (横 {final_w} × 縦 {final_h}) が元画像サイズ (横 {orig_w} × 縦 {orig_h}) より大きいため拡大処理になります。",
                file=sys.stderr,
            )

        print(f"配置サイズ: 横 {final_w} ブロック × 縦 {final_h} ブロック (元画像: {orig_w}×{orig_h})")

        # Map to block indices
        grid = map_pixels_to_blocks(rgb_grid, opaque_grid, palette)

        unique_blocks = set(np.unique(grid))
        unique_blocks.discard(-1)
        print(f"使用ブロック種類数: {len(unique_blocks)} 種類 (パレット総数: {len(palette.ids)} 種類)")

        # Create Placement
        placement = Placement(
            orientation=orientation,  # type: ignore[arg-type]
            facing=facing,  # type: ignore[arg-type]
            coords=args.coords,
            origin=origin,
        )

        # Generate commands
        commands = generate_commands(grid, palette, placement)
        total_commands = len(commands)
        print(f"生成コマンド数: {total_commands} 行")

        if total_commands > 65536:
            print(
                f"警告: 総コマンド数 ({total_commands}) が 65536 を超えています。Minecraft の maxCommandChainLength を超えるコマンドは実行されません。\n"
                f"ゲーム内で '/gamerule maxCommandChainLength {total_commands}' を実行して上限を引き上げてください。",
                file=sys.stderr,
            )

        # Save Preview (default to <out>/previews/<stem>.png)
        out_root = Path(args.out)
        preview_path = Path(args.preview) if args.preview else out_root / "previews" / f"{stem}.png"
        saved_preview = save_preview(grid, palette, preview_path)
        print(f"プレビュー保存: {saved_preview}")

        # Write Datapack
        desc = f"minecraft-pixelart {Path(image_path).name} {final_w}x{final_h}"
        datapack_dir, num_parts = write_datapack(
            commands=commands,
            out_dir=out_root,
            pack_name=pack_name,
            namespace=namespace,
            function_name=function_name,
            description=desc,
            max_commands=args.max_commands,
        )

        split_info = f" ({num_parts} ファイルに分割)" if num_parts > 0 else ""
        print(f"データパック出力: {datapack_dir}{split_info}")
        print(f"実行コマンド: /function {namespace}:{function_name}")
        print("完了しました。")
        return 0

    except KeyboardInterrupt:
        print("\n処理が中断されました。", file=sys.stderr)
        return 1
    except UsageError as e:
        print(f"エラー: {e.message}", file=sys.stderr)
        return e.exit_code
    except PixelArtError as e:
        print(f"エラー: {e.message}", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
