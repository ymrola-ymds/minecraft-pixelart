# 基本設計_ver2.0

## 本書の位置づけについて

本書は minecraft-pixelart **Ver2.0 の基本設計の正本**である。要件（`documents/00_requirements/requirements_ver2.0.md`）に基づき、Ver1.0（`documents/01_basic_design/basic_design_ver1.0.md`）のモジュール構成・データ構造・入出力仕様に対する 26.3 新規ブロック対応および透明ブロック制御の変更点を定義する。

## 前提

- 利用者の環境に Python 3.11 以上がインストール済みであること
- 実行手段:
  - `uv run pixelart.py ...`（推奨）
  - `pip install pillow numpy` 済みの環境で `python pixelart.py ...`
- 対象は Java Edition 26.3（26.1〜26.3 対応）。Bedrock Edition は作らない
- 最終成果物は Minecraft データパック（`pack.mcmeta`、`function` / `functions` 両書き）

## 全体構成

```
入力画像 ──▶ imaging ──▶ mapping ──▶ commands ──▶ datapack ──▶ データパック一式
                │           │            ▲
                │           │            │
                │        palette      layout（座標の振り方）
                │           │
                └────────▶ preview ──▶ preview.png
```

## ファイル構成

```
minecraft-pixelart/
├── README.md                       # PEP 723 配布の手順
├── pixelart.py                     # エントリ。PEP 723 ヘッダ + main() 呼び出しのみ
├── mcpixelart/
│   ├── __init__.py
│   ├── cli.py                      # 引数定義・検証・既定値・対話確認（向き/落下/透明）・実行制御
│   ├── imaging.py                  # 読み込み / 透明処理 / LANCZOS 縮小 / 回転・反転
│   ├── palette.py                  # パレット読み込み・フィルタ（落下/透明）・redmean最近傍
│   ├── mapping.py                  # 格子 → ブロック索引（空気は -1）
│   ├── layout.py                   # 向き・正面・相対/絶対 → 座標式
│   ├── commands.py                 # 横ランの圧縮 → fill / setblock 文字列
│   ├── datapack.py                 # pack.mcmeta・関数分割・function/functions 両書き
│   ├── preview.py                  # 割当後ブロック色のプレビュー画像
│   └── errors.py                   # 利用者向けエラー定義
├── data/palette/
│   ├── palette_26.3.json           # 26.3 同梱パレット（既定）
│   ├── rules_26.3.json             # 26.3 タグ付け規則
│   ├── palette_26.2.json           # 26.2 パレット（互換性維持用）
│   └── rules_26.2.json             # 26.2 タグ付け規則
├── tools/
│   └── build_palette.py            # client.jar → palette JSON（26.3辞書テクスチャ対応）
├── images/
└── documents/
```

## パレット仕様 (v2)

### 1. タグと除外フィルタ

基本の除外タグ集合:
`{liquid, functional, non_full_cube, ice, slime, honey, leaves}`

オプションによるタグ追加:
- `use_gravity_blocks == False` の場合: `exclude_tags` に `gravity` を追加
- `use_transparent_blocks == False` の場合: `exclude_tags` に `transparent` を追加

### 2. 新規追加ブロック（26.3 同梱パレット）

以下の 9 種のフルキューブ建材をパレットに追加（計 122 ブロック）:
- 辰砂（4種）:
  - `minecraft:cinnabar` (`[152, 83, 78]`, tags: `[]`)
  - `minecraft:polished_cinnabar` (`[153, 58, 55]`, tags: `[]`)
  - `minecraft:cinnabar_bricks` (`[148, 56, 54]`, tags: `[]`)
  - `minecraft:chiseled_cinnabar` (`[147, 55, 55]`, tags: `[]`)
- 板材（2種）:
  - `minecraft:poplar_planks` (`[150, 137, 127]`, tags: `[]`)
  - `minecraft:pale_oak_planks` (`[228, 218, 216]`, tags: `[]`)
- 樹脂（3種）:
  - `minecraft:resin_block` (`[217, 99, 25]`, tags: `[]`)
  - `minecraft:resin_bricks` (`[206, 88, 24]`, tags: `[]`)
  - `minecraft:chiseled_resin_bricks` (`[201, 84, 25]`, tags: `[]`)

※ 新規非フルキューブ（`*_shelf`, `*_stairs`, `*_slab`, `shelf_mushroom`, `straw_bed` 等）は `rules_26.3.json` で除外タグ（`non_full_cube`, `functional`）を付与。

## モジュール改修詳細

### 1. `mcpixelart/palette.py`
- `load_palette` のシグネチャを拡張:
  ```python
  def load_palette(
      palette_path: str | Path,
      use_gravity_blocks: bool = False,
      use_transparent_blocks: bool = False,
  ) -> Palette:
  ```
- `use_transparent_blocks` が False のとき、`exclude_tags.add("transparent")` を実行。

### 2. `mcpixelart/cli.py`
- 引数追加:
  ```python
  parser.add_argument(
      "--transparent-blocks",
      choices=["use", "exclude"],
      default=None,
      help="透明ブロック（ガラス・色付きガラス）の利用 (use / exclude, 既定: exclude)",
  )
  ```
- 対話プロンプト関数 `prompt_transparent_blocks(specified, is_interactive) -> bool`:
  - `use` → `True`
  - `exclude` → `False`
  - 未指定 & 非対話 → 警告表示して `False`（使わない）
  - 未指定 & 対話時 →
    ```text
    ガラス・色付きガラスなどの透明ブロックを使いますか。
    背景が透けて見えるため、壁や立体物で裏側が見える場合があります。
      1) 使わない（パレットから外す）  [既定]
      2) 使う
    ```
- 既定パレットパス: `data/palette/palette_26.3.json` に更新。

### 3. `mcpixelart/datapack.py`（pack.mcmeta）

Ver2.0 は Ver1.0 と同値を出力する。

```json
{
  "pack": {
    "description": "Pixel Art Datapack",
    "min_format": [101, 1],
    "max_format": 120
  }
}
```

- 古い整数 `pack_format` は書かない
- `load.json` / `tick.json` は置かない
- 実装の定数が正本と食い違う場合は実装を正本に合わせる（数値変更は正本更新とセット）

### 4. `data/palette/rules_26.3.json`（新規9種の登録）

再生成の再現性のため、次の 9 ID を `exact_matches` に `tags: []` で登録する（実装役）。

- `minecraft:cinnabar`
- `minecraft:polished_cinnabar`
- `minecraft:cinnabar_bricks`
- `minecraft:chiseled_cinnabar`
- `minecraft:poplar_planks`
- `minecraft:pale_oak_planks`
- `minecraft:resin_block`
- `minecraft:resin_bricks`
- `minecraft:chiseled_resin_bricks`

登録後、必要なら `tools/build_palette.py` で `palette_26.3.json` を再生成して正本の色と突き合わせる。

### 5. `tools/build_palette.py`

- 26.3 の `assets/minecraft/models/block/*.json` において、`textures` の値が `{"sprite": "...", "force_translucent": true}` 等の辞書構造である場合に対応。
- 既定の `--version` を `26.3`、`--rules` を `data/palette/rules_26.3.json`、`--out` を `data/palette/palette_26.3.json` に設定。
