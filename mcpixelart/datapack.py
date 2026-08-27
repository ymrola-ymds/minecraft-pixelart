"""Minecraft datapack generation with pack.mcmeta and function splitting."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from mcpixelart.errors import DataPackError


def write_datapack(
    commands: list[str],
    out_dir: str | Path,
    pack_name: str,
    namespace: str,
    function_name: str,
    description: str,
    max_commands: int = 65000,
) -> tuple[Path, int]:
    """Write Minecraft Java Edition 26.2 compatible datapack.

    Writes to both 'function' and 'functions' folders.
    Splits into part_XXXX.mcfunction files if command count exceeds max_commands.

    Args:
        commands: List of command strings to write.
        out_dir: Base output directory.
        pack_name: Datapack directory name.
        namespace: Minecraft function namespace.
        function_name: Entry function name.
        description: Description string for pack.mcmeta.
        max_commands: Max commands per mcfunction file before splitting.

    Returns:
        tuple of (datapack_dir_path, part_file_count)

    Raises:
        DataPackError: If writing files fails.
    """
    if max_commands <= 0:
        raise DataPackError("max_commands は 1 以上の整数である必要があります。")

    pack_dir = Path(out_dir) / pack_name
    data_dir = pack_dir / "data" / namespace

    try:
        pack_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write pack.mcmeta (supports 26.1 [101, 1] to 26.x [120])
        mcmeta_content = {
            "pack": {
                "description": description,
                "min_format": [101, 1],
                "max_format": 120,
            }
        }
        mcmeta_path = pack_dir / "pack.mcmeta"
        with open(mcmeta_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(mcmeta_content, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # 2. Prepare function and functions target directories
        target_dirs = [
            data_dir / "function",
            data_dir / "functions",
        ]

        total_commands = len(commands)
        is_split = total_commands > max_commands

        for fn_dir in target_dirs:
            fn_dir.mkdir(parents=True, exist_ok=True)

            sub_dir = fn_dir / function_name
            # If function_name contains slashes or parts, ensure parent exists
            sub_dir.parent.mkdir(parents=True, exist_ok=True)

            # Clean up existing part_*.mcfunction in sub_dir to prevent leftover old parts
            if sub_dir.exists() and sub_dir.is_dir():
                for old_part in sub_dir.glob("part_*.mcfunction"):
                    old_part.unlink()

            entry_file = fn_dir / f"{function_name}.mcfunction"
            entry_file.parent.mkdir(parents=True, exist_ok=True)

            if not is_split:
                # Direct write into entry mcfunction
                with open(entry_file, "w", encoding="utf-8", newline="\n") as f:
                    for cmd in commands:
                        f.write(f"{cmd}\n")
            else:
                sub_dir.mkdir(parents=True, exist_ok=True)
                part_calls: list[str] = []

                num_parts = (total_commands + max_commands - 1) // max_commands
                for i in range(num_parts):
                    part_num = i + 1
                    part_filename = f"part_{part_num:04d}.mcfunction"
                    part_file_path = sub_dir / part_filename

                    start_idx = i * max_commands
                    end_idx = min(start_idx + max_commands, total_commands)
                    part_cmds = commands[start_idx:end_idx]

                    with open(part_file_path, "w", encoding="utf-8", newline="\n") as f:
                        for cmd in part_cmds:
                            f.write(f"{cmd}\n")

                    part_calls.append(f"function {namespace}:{function_name}/part_{part_num:04d}")

                with open(entry_file, "w", encoding="utf-8", newline="\n") as f:
                    for call_cmd in part_calls:
                        f.write(f"{call_cmd}\n")

        part_count = (total_commands + max_commands - 1) // max_commands if is_split else 0
        return pack_dir, part_count

    except Exception as e:
        raise DataPackError(f"データパックの書き出しに失敗しました: {e}") from e
