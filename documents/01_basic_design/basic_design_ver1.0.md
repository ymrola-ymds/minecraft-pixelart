# 基本設計_ver1.0

## 本書の位置づけについて

本書は minecraft-pixelart **Ver1.0 の基本設計の正本**である。要件（`documents/00_requirements/requirements_ver1.0.md`）を、モジュール構成・データ構造・入出力仕様のレベルまで落とす。実装コードの詳細（関数の中身、変数名）は本書の対象外。

要件と食い違う記述が本書にあれば、要件が優先する。本書で新たに決めた細部は「本書で決めたこと」に、要件に無く判断が要るものは「確認したい点」に列挙する。

## 前提

- 利用者の環境に Python 3.11 以上がインストール済みであること
- パッケージ製品（pip install できる配布物）は作らない。GitHub から取得したファイル一式をそのまま実行する
- 実行手段は二通り。どちらも同じ結果になる
  - `uv run pixelart.py ...`（PEP 723 のインラインメタデータから pillow / numpy を自動解決）
  - `pip install pillow numpy` 済みの環境で `python pixelart.py ...`
- 対象は Java Edition 26.2 のみ。Bedrock Edition は作らない
- 最終成果物は Minecraft データパック。`.mcfunction` を `function` / `functions` の両方へ置く
- `data/<namespace>/load.json` と `tick.json` は置かない（手動で `/function` する）

## 全体構成

```
入力画像 ──▶ imaging ──▶ mapping ──▶ commands ──▶ datapack ──▶ データパック一式
                │           │            ▲
                │           │            │
                │        palette      layout（座標の振り方）
                │           │
                └────────▶ preview ──▶ preview.png
```

処理は一方向。対話は `cli.py` が引数を解釈した直後の確認だけで（「対話プロンプト」節）、変換が始まってからは何も尋ねない。ゲームやワールドには一切触れない（ファイル出力のみ）。

## ファイル構成

```
minecraft-pixelart/
├── README.md                       # PEP 723 配布の手順。pip-tools / venv テンプレは使わない。Bedrock しないと明示
├── pixelart.py                     # エントリ。PEP 723 ヘッダ + main() 呼び出しのみ
├── mcpixelart/
│   ├── __init__.py
│   ├── cli.py                      # 引数定義・検証・既定値・実行順序の制御
│   ├── imaging.py                  # 読み込み / 透明処理 / LANCZOS 縮小 / 回転・反転
│   ├── palette.py                  # パレット JSON 読み込み・既定フィルタ・最近傍探索
│   ├── mapping.py                  # 格子 → ブロック索引（空気は -1）
│   ├── layout.py                   # 向き・正面・相対/絶対 → 座標式
│   ├── commands.py                 # 横ランの圧縮 → fill / setblock 文字列
│   ├── datapack.py                 # pack.mcmeta・関数分割・function/functions 両書き
│   ├── preview.py                  # 割当後ブロック色のプレビュー画像
│   └── errors.py                   # 利用者向けエラー（終了コードの整理）
├── data/palette/
│   ├── palette_26.2.json           # 同梱パレット（配布物に含める）
│   └── rules_26.2.json             # タグ付け規則（生成時に使う。メンテナ用）
├── tools/
│   └── build_palette.py            # client.jar → palette JSON（メンテナ用。PEP 723）
├── tests/
└── documents/
```

`uv run pixelart.py` / `python pixelart.py` のいずれでも、`sys.path` にスクリプトのディレクトリが入るため `mcpixelart` パッケージと `data/` を相対で解決できる。パレットの既定パスは `<pixelart.py のあるディレクトリ>/data/palette/palette_26.2.json`。

## モジュール責務

| モジュール | 責務 | 主な入出力 |
|---|---|---|
| `cli.py` | 引数の解釈・検証、未指定項目の対話確認、パイプライン実行、進捗と警告の表示 | argv → 終了コード |
| `imaging.py` | 画像読み込み、アルファ分離、LANCZOS 縮小、回転・反転 | パス → `(rgb: uint8[H,W,3], opaque: bool[H,W])` |
| `palette.py` | パレット読み込み、既定フィルタ適用、redmean 最近傍 | JSON → `Palette(ids, rgb)`、色配列 → 索引配列 |
| `mapping.py` | 格子色 → ブロック索引。空気セルは `-1` | `(rgb, opaque, Palette)` → `int32[H,W]` |
| `layout.py` | 格子座標 `(c, r)` → ワールド座標式、ラン軸の決定 | 設定 → 座標文字列生成関数 |
| `commands.py` | 行ごとの同一ブロック連続の圧縮、コマンド文字列化 | `int32[H,W]` + layout → `list[str]` |
| `datapack.py` | ディレクトリ構築、`pack.mcmeta`、関数分割、両ディレクトリ書き出し | `list[str]` → ファイル群 |
| `preview.py` | 割当済み索引 → ブロック色の PNG | `int32[H,W]` + `Palette` → PNG |

## データ構造

```python
Palette:
    ids : list[str]           # 例 "minecraft:white_concrete"
    rgb : np.ndarray          # float32, shape (N, 3)
    version : str             # "26.2"

BlockGrid = np.ndarray        # int32, shape (H, W)。値は Palette の索引。-1 は空気

Run = (row: int, c_start: int, c_end: int, block: int)

Placement:                    # layout が組み立てる不変オブジェクト
    orientation : "floor" | "wall"
    facing      : "south" | "north" | "east" | "west"   # floor では未使用。4 方位すべて v1
    coords      : "relative" | "absolute"
    origin      : (x, y, z)                   # absolute のみ
```

## パレット

### JSON スキーマ

```json
{
  "schema": 1,
  "minecraft_version": "26.2",
  "source": { "jar": "client.jar", "sha1": "..." },
  "blocks": [
    { "id": "minecraft:white_concrete", "texture": "block/white_concrete",
      "rgb": [207, 213, 214], "tags": [] },
    { "id": "minecraft:glass", "texture": "block/glass",
      "rgb": [180, 202, 207], "tags": ["transparent"] },
    { "id": "minecraft:water", "texture": "block/water_still",
      "rgb": [63, 118, 228], "tags": ["liquid"] }
  ]
}
```

- 色は Python に埋め込まない。JSON を差し替えれば新バージョンに追随できる
- `rgb` は **side テクスチャの不透明画素のみ**の単純平均（草ブロックも side）
- 全ブロックを収録し、除外は `tags` で表現する。JSON を作る時点では何も除外しない。除外の判断はコード側（下記「既定フィルタ」）が持ち、生存向けフィルタ（v2）を除外集合の変更だけで足せるようにする

### タグ

`liquid` / `functional` / `non_full_cube` / `ice` / `slime` / `honey` / `leaves` / `transparent` / `gravity` / `light` / `flammable`

`rules_26.2.json` のカテゴリ → タグ対応。ガラスを残し、板ガラス・粉末雪・氷などを確実に外せるように、ID 完全一致と接尾辞を分ける。

| カテゴリ | 判定（例） | タグ | 既定 |
|---|---|---|---|
| 水・溶岩 | `water` / `lava` およびその派生 | `liquid` | 外す |
| 粉末雪 | 完全一致 `minecraft:powder_snow` | `liquid` | 外す |
| 氷・氷塊・青氷 | 完全一致 `ice` / `packed_ice` / `blue_ice` | `ice` | 外す |
| スライムブロック | 完全一致 `minecraft:slime_block` | `slime` | 外す |
| ハチミツブロック | 完全一致 `minecraft:honey_block` | `honey` | 外す |
| 葉 | 接尾辞 `_leaves` | `leaves` | 外す |
| ガラス（ブロック） | 完全一致 `minecraft:glass` | `transparent` のみ | **残す** |
| 色付きガラス（ブロック） | 接尾辞 `_stained_glass`（その後に `_pane` が続かない） | `transparent` のみ | **残す** |
| 板ガラス | 接尾辞 `_pane`（`glass_pane` / `*_stained_glass_pane`） | `non_full_cube` | 外す |
| 半ブロック・階段・柵・カーペット・ドア・鉄格子等 | 形状（`_slab` / `_stairs` / `_fence` / `_carpet` / `_door` / `_bars` 等） | `non_full_cube` | 外す |
| レッドストーン機器・コンテナ・作業台・TNT・スポナー・ベッド・ポータル・コマンド系 | ID リスト + 接尾辞 | `functional` | 外す |
| 砂・赤い砂・砂利・各色コンクリートパウダー | ID リスト | `gravity` | 対話（未指定なら尋ねる） |
| 発光ブロック | ID リスト | `light` | 記録のみ（v1 では絞らない） |
| 可燃 | タグ記録 | `flammable` | 記録のみ（v1 では絞らない） |

板ガラスは `transparent` だけを付けて残してはならない。`_stained_glass` より `_stained_glass_pane` を先に判定する。粉末雪は `gravity` ではなく `liquid` とする（要件の液体）。規則にも許可リストにも当たらない新規 ID は `functional` 扱いで既定から外す。

### 既定フィルタ

既定の除外集合は
`{liquid, functional, non_full_cube, ice, slime, honey, leaves}`。
これに該当するタグを一つでも持つブロックを候補から外す。ガラス・色付きガラスは `transparent` のみを持つため既定に残る（要件の例外規定と一致）。

この除外集合は **`palette.py` に定数として持つ**。パレット読み込み時に一括で適用する。ここに挙げたタグについては利用者に尋ねない。

これに加えて、**`gravity`（砂・赤い砂・砂利・各色コンクリートパウダー等）は落下して絵を壊すため、使うかどうかを利用者に決めさせる**。`--gravity-blocks` 未指定なら対話で尋ねる（「対話プロンプト」節）。`exclude` なら除外集合に `gravity` を加える。

`light` / `flammable` は **記録するが v1 では絞り込みに使わない**。v2 の生存向けフィルタで使う。

### 最近傍探索

要件どおり redmean を使う。種スクリプトと同一の式。

```
r̄ = (r1 + r2) / 2
d = (2 + r̄/256)·Δr² + 4·Δg² + (2 + (255-r̄)/256)·Δb²
```

実装は numpy でベクトル化する。格子の色を一意化（`np.unique`）してから、一意色をチャンクに分けて `(B, N)` の距離行列で `argmin` し、索引を格子へ戻す。**`(U, N)` を一枚で作らない**。1000×1000（一意色が最悪セル数まで）でも、常駐メモリは格子・索引・パレットと小さな `(B, N)` 程度に収める。チャンク幅 `B` は実装が決める（目安 4096）。

### パレット生成（メンテナ用 `tools/build_palette.py`）

配布物には生成済み JSON を同梱するため、利用者はこのツールを使わない。

1. `client.jar` を zip として開く
2. `assets/minecraft/blockstates/*.json` からブロック ID を列挙し、参照モデル名を取る（variants / multipart のうち最初の一件）
3. `assets/minecraft/models/block/*.json` を `parent` に沿って解決し、`textures` を合成する
4. side テクスチャを `side` → `all` → `texture` → `north` の優先順で選ぶ
5. `assets/minecraft/textures/<name>.png` を読む。`.mcmeta` を持つアニメーションテクスチャは先頭フレームのみ使う
6. アルファ 0 の画素を除いて RGB を平均する。不透明画素が無いブロックは収録しない
7. `rules_26.2.json`（ID の完全一致と接尾辞パターンで書いたタグ規則）を当ててタグを付ける
8. 規則にも既知の許可リストにも当たらない新規 ID は、警告を出したうえで `functional` 扱いにして既定から外す（安全側に倒す）

`--jar` `--version` `--rules` `--out` を取る。実行結果は JSON 差分としてレビューできる。

## 変換パイプライン

### 1. 読み込みと透明処理

- Pillow で開き `RGBA` へ変換する
- LANCZOS の縮小で透明部の色がにじむのを防ぐため、RGB を **アルファで乗算済み**にしてから縮小し、縮小後に `a > 0` のセルで除算して戻す
- アルファも同じサイズへ LANCZOS で縮小する
- **縮小後のアルファが 0 のセルを空気**とする。要件の「完全透明は空気、それ以外は不透明化して最近傍」と一致する

### 2. 縮小

`--width` × `--height`（ブロック数）へ LANCZOS で縮小する。元画像のピクセル数・アスペクト比は問わない。アスペクト比は保たない（指定サイズちょうどにする）。元画像より大きい指定は拡大になる。警告は出すが処理は続ける。

### 3. 回転・左右反転

- 回転は **時計回り**。`0 / 90 / 180 / 270`
- 反転は回転の**後**に左右反転（要件の流れ順）
- `--rotate` が 90 / 270 のとき、最終の配置サイズは幅と高さが入れ替わる。`--width` / `--height` は**回転前**の格子サイズを指す。最終サイズは標準出力に必ず表示する

### 4. ブロック割当

空気セル以外について、redmean 最近傍でパレット索引を決める。空気セルは `-1`。

### 5. ラン圧縮

**絵の横方向**（格子の列方向）に、同一ブロックが連続する区間をまとめる。

- 長さ 1 → `setblock`
- 長さ 2 以上 → `fill`
- 空気（`-1`）の区間はコマンドを出さない

### 6. 座標

格子は絵の左上を `(c=0, r=0)` とする（列 `c` が右、行 `r` が下）。

**原点（相対の実行位置 / 絶対の開始座標）**

- **床**: 絵の**左上**セル
- **壁**: 絵の**左下**セル（足元）。そこから上へ正立する。実行位置に立って `/function` すると、絵は足元から頭の方向へ伸びる

| 向き | 原点に来るセル | dx | dy | dz | ラン軸 |
|---|---|---|---|---|---|
| 床 (`floor`) | 左上 `(0, 0)` | `c` | `0` | `r` | X |
| 壁・南向き (`wall/south`, XY) | 左下 `(0, H-1)` | `c` | `H-1-r` | `0` | X |
| 壁・北向き (`wall/north`, XY) | 左下 `(0, H-1)` | `-c` | `H-1-r` | `0` | X |
| 壁・東向き (`wall/east`, ZY) | 左下 `(0, H-1)` | `0` | `H-1-r` | `-c` | Z |
| 壁・西向き (`wall/west`, ZY) | 左下 `(0, H-1)` | `0` | `H-1-r` | `c` | Z |

- `H` は回転・反転後の格子の高さ。壁の 4 方位はすべて v1。`north` はエラーにしない
- `facing` は「絵の正面が向く方角」＝**見る人が立つ側**
- 南向き: 南から見て正立。絵の左→右が +X
- 北向き: 南の左右反転。絵の左→右が -X。北から見て正立
- 東向き: 東から見て左→右が -Z
- 西向き: 西から見て左→右が +Z
- 床は上から北を上にして見たときに絵が正立する（絵の上端が北。原点が北西、+Z が南＝絵の下）
- 絶対座標は上表のオフセットを `--origin` の `X Y Z` に加算する

#### fill / setblock の形

オフセット 0 は `~`（`~0` と書かない）。負は `~-N`（符号と数字の間に空白を入れない）。正は `~N`。絶対はチルダ無しの整数。

```
setblock <x> <y> <z> <id>
fill <x1> <y1> <z1> <x2> <y2> <z2> <id>
```

相対の例（壁・南向き、原点が左下）:

```
setblock ~ ~ ~ minecraft:white_concrete
setblock ~3 ~12 ~ minecraft:glass
setblock ~-4 ~ ~ minecraft:white_concrete
fill ~ ~ ~ ~10 ~ ~ minecraft:white_concrete
fill ~-5 ~ ~ ~ ~8 ~ minecraft:glass
```

`fill` の始点・終点はラン軸の両端。他の 2 軸は同値。`replace` 等のモードは付けない。

### 7. プレビュー

割当後のブロック色で 1 セル = 1 ピクセルの RGBA PNG を書く。空気セルは完全透明。回転・反転を適用した後の見た目にする。出力先は `<out>/preview.png`（`--preview` で変更可）。

## データパック出力

### ディレクトリ

```
<out>/
├── preview.png
└── <pack-name>/
    ├── pack.mcmeta
    └── data/<namespace>/
        ├── function/
        │   ├── <function>.mcfunction
        │   └── <function>/part_0001.mcfunction ...
        └── functions/          # 同一内容
            ├── <function>.mcfunction
            └── <function>/part_0001.mcfunction ...
```

`data/<namespace>/load.json` と `tick.json`（および `tags/function/load.json` 等）は**置かない**。起動や毎 tick では走らせない。利用者が `/function <namespace>:<function>` する。

### pack.mcmeta

```json
{
  "pack": {
    "description": "minecraft-pixelart <入力ファイル名> <W>x<H>",
    "min_format": [107, 1],
    "max_format": 107
  }
}
```

古い整数の `pack_format` は書かない（要件どおり）。

### 関数分割

- 分割の閾値は 65000 コマンド（`--max-commands` で変更可）
- 総コマンド数が閾値以下：`<function>.mcfunction` にコマンドをそのまま書く。`part_*` は作らない
- 閾値を超える：コマンドを 65000 行ずつ `<function>/part_0001.mcfunction` … に分け、`<function>.mcfunction` には `function <namespace>:<function>/part_0001` を**生成順に**並べる
- 切り捨ては行わない。分割数に上限は設けない

### 書き出し規則

- 文字コード UTF-8（BOM 無し）、改行 LF、末尾に改行 1 個
- `function` と `functions` は同一内容を 2 回書く。片方だけの成功で終わらない
- 既存の同名データパックディレクトリがある場合は上書きする。**書き出し前に `<function>/` 内の既存 `part_*.mcfunction` を削除する**（再実行でコマンド数が減ったとき、古い part が残って二重配置になるのを防ぐ）
- 上書きの確認プロンプトは出さない（要件どおり）

## CLI 仕様

```
pixelart.py IMAGE --width W --height H [オプション]
```

| 引数 | 既定 | 説明 |
|---|---|---|
| `IMAGE` | 必須 | 入力画像のパス |
| `--width` / `-W` | 必須 | 横のブロック数（回転前） |
| `--height` / `-H` | 必須 | 縦のブロック数（回転前） |
| `--orientation` | 未指定なら質問 | `floor`（水平・地面に平行）/ `wall`（垂直）。`--facing` だけ指定されていれば質問せず `wall`。非対話時は `wall` |
| `--facing` | 未指定なら質問 | `south` / `north` / `east` / `west`。4 方位すべて有効。`north` はエラーにしない。`--facing` のみ指定時は尋ねず `wall` + その正面。非対話時は `south` |
| `--rotate` | `0` | `0` / `90` / `180` / `270`（時計回り） |
| `--mirror` | 無効 | 指定で左右反転 |
| `--coords` | `relative` | `relative` / `absolute` |
| `--origin X Y Z` | なし | `--coords absolute` のとき必須 |
| `--pack-name` | `pixelart` | データパックのディレクトリ名 |
| `--namespace` | `pixelart` | 名前空間 |
| `--function` | `build` | エントリ関数名 |
| `--out` | `./output` | 出力ルート |
| `--preview` | `<out>/preview.png` | プレビューの出力先 |
| `--palette` | 同梱 JSON | パレット JSON のパス |
| `--max-commands` | `65000` | 分割の閾値 |
| `--gravity-blocks` | 未指定なら質問 | `use` / `exclude`。落下ブロック（砂・砂利・コンクリートパウダー等）を候補に入れるか。非対話時は `exclude` |
| `--yes` / `-y` | 無効 | 質問せずすべて既定を採る（スクリプト・CI 用） |

### 検証

- `--width` / `--height` は 1 以上の整数
- `--origin` は `--coords absolute` のときに必須。`relative` のとき指定されたら無視して警告
- `--facing` のみ（`--orientation` なし）は `wall` + 指定正面として確定し、向きを尋ねない
- `--facing` は `--orientation floor` のとき無視して警告
- `--facing north` は正当。エラーにしない
- `--namespace` / `--function` / `--pack-name` は Minecraft のリソース位置に使える文字（`[a-z0-9_.-]`、関数名は `/` 可）に限る。違反はエラー
- 入力画像が読めない、パレット JSON が壊れている、パレット候補が 0 件になった場合はエラー

### 対話プロンプト

データパックは**座標と向きを焼き込む**。litematic のように「貼るときに位置と回転を選び直す」ことができない。落下ブロックも、置いた瞬間に絵が崩れて後から直せない。この 2 つは、未指定のまま黙って既定を採ると出力が無駄になるため、**対話で確認する**。

尋ねる条件（すべて満たすとき）:

- 該当のオプションがコマンドラインで指定されていない
- `--yes` が指定されていない
- 標準入力と標準出力の**両方が TTY** である

質問 1（`--orientation` も `--facing` も未指定のとき）:

```
配置の向きを選んでください。
  1) 壁・南向き（垂直 / 南から見る）  [既定]
  2) 壁・北向き（垂直 / 北から見る）
  3) 壁・東向き（垂直 / 東から見る）
  4) 壁・西向き（垂直 / 西から見る）
  5) 床（水平・地面に平行）
選択 [1]:
```

- 空入力（Enter）で 1（壁・南向き）
- `--facing` だけ指定されているときは**尋ねない**。`wall` + その正面で確定する
- `--orientation wall` だけ指定されていて `--facing` が無いときは、1〜4（南・北・東・西）のみを尋ねる
- `--orientation floor` が指定されていれば尋ねない

質問 2（`--gravity-blocks` 未指定時）:

```
砂・砂利・コンクリートパウダーなどの落下ブロックを使いますか。
下に空間があると落ちて絵が崩れます。
  1) 使わない（パレットから外す）  [既定]
  2) 使う
選択 [1]:
```

- 空入力（Enter）で 1（使わない）
- 床でも下が空洞なら落ちるため、向きにかかわらず尋ねる

共通の扱い:

- 範囲外の入力は再入力を求める。回数制限は設けない
- EOF（Ctrl+D / Ctrl+Z）を受けたら既定を採って続行する
- `Ctrl+C` は中断。何も書き出さずに終了コード `1`
- 質問した結果は、以降の処理と同じく標準出力の要約行に出す（`向き: 壁・東向き` `落下ブロック: 使わない`）

非対話（TTY でない、または `--yes`）のときは尋ねず既定を採り、**採用した値を警告行として出す**。パイプやリダイレクト、CI からの実行はここに入る。


### 標準出力

処理の各段で 1 行ずつ出す。最低限、最終配置サイズ、使用ブロック種類数、生成コマンド数、分割ファイル数、出力先パスを出す。

### 警告を出す条件

- 指定サイズが元画像より大きい（拡大になる）
- 総コマンド数が 65536 を超える（下記の注意）
- `--origin` / `--facing` の無視
- 非対話のため質問を省いて既定を採った（採用値も併記する）
- 落下ブロックを `use` にしたまま壁を選んだ（下に支えが無いと落ちる）

### 終了コード

`0` 正常 / `2` 引数の誤り / `1` それ以外の実行時エラー。

## 設計上の注意（利用者への伝達が要る点）

関数を 65000 行で分割しても、エントリから連続で呼ぶ以上、**同一 tick に実行されるコマンド総数は変わらない**。Minecraft の `maxCommandChainLength`（既定 65536）を超える大きな絵では、後半のコマンドが実行されない。

対策は設計外（v1 はファイルを出すだけ）とし、**総コマンド数が 65536 を超える場合に警告を出し、`/gamerule maxCommandChainLength <値>` の引き上げを促す**。この文言は README にも載せる。

## 非機能

- 想定規模は 1000×1000 セル（100 万セル）まで。この規模で数秒〜十数秒で終わること
- 色の照合とラン圧縮は numpy で処理する。セル単位の Python ループは避ける
- メモリは格子と索引配列のみ常駐（100 万セルで数十 MB）。コマンド文字列は生成後すぐ書き出す
- 外部ネットワークアクセスは行わない。Minecraft のインストールや jar も、利用時には要求しない

## テスト観点

| 区分 | 観点 |
|---|---|
| 座標 | 床では左上 `(0,0)` が原点。壁では左下 `(0, H-1)` が原点で `(0,0)` は `dy=H-1`。南・北・東・西 + 床の 5 通りで表と一致。北は `dx=-c`（南の左右反転）。相対は 0 が `~`、負が `~-N`（`~0` や `~ -N` は出さない） |
| 回転 | 90/270 で最終サイズが入れ替わる。回転→反転の順序。0 + 反転なしで恒等 |
| 透明 | アルファ 0 のみ空気。半透明は不透明化されて配置される。縮小で透明部の色がにじまない |
| ラン圧縮 | 長さ 1 は `setblock`、2 以上は `fill`。空気で分断される。行をまたいで結合しない |
| 分割 | 総数が閾値ちょうど（65000）で分割しない。65001 で 2 分割。エントリの呼び順 |
| パレット | 既定フィルタで液体（粉末雪含む）・機能・非フルキューブ（板ガラス含む）・氷・スライム・ハチミツ・葉が落ちる。ガラス・色付きガラスは残る。板ガラスは残らない。`--gravity-blocks exclude` で砂・砂利・コンクリートパウダーが落ち、`use` で残る |
| 対話 | 非 TTY / `--yes` で質問せず既定（壁・南向き / 落下ブロック使わない）を採り警告を出す。範囲外入力で再質問。EOF で既定。`--orientation wall` 指定時は正面（南・北・東・西）を尋ねる。`--facing` のみ指定時は尋ねず wall + その正面 |
| 出力 | `pack.mcmeta` の内容一致。`function` と `functions` が同一内容。LF と UTF-8。旧 part の削除。`load.json` / `tick.json` が無い |
| メモリ | 1000×1000 でも距離行列を一枚で持たず、分割 argmin で格子程度に収まる |
| CLI | 必須引数欠落で終了コード 2。`absolute` で `--origin` 無しはエラー |

種スクリプト `pixel-art.py` は仕様の参照元として残すが、テスト対象にはしない。

## 本書で決めたこと（要件に無かった細部）

1. 単一スクリプトではなくエントリ + `mcpixelart` パッケージ構成にする（PEP 723 配布は維持）
2. パレット JSON は全ブロックをタグ付きで収録し、除外はコード側の定数（既定除外集合）をパレット読み込み時に当てて行う。対話も CLI オプションも無い
3. 縮小はアルファ乗算済みで行い、縮小後アルファ 0 のセルを空気とする
4. 原点は床が絵の左上、壁が絵の左下（足元から正立）。5 通り（床 + 南・北・東・西）で本文・座標表・テストを一致させる
5. 壁正面は南・北・東・西の 4 つ。北は南の左右反転（絵の左→右が -X）。`north` はエラーにしない。東向きは -Z、西向きは +Z へ伸びる
6. 総コマンド数が閾値以下なら `part_*` を作らずエントリへ直接書く
7. 再実行時に古い `part_*.mcfunction` を削除する
8. 出力ルートの既定は `./output`
9. `--rotate` は時計回り。`--width` / `--height` は回転前の値
10. 配置の向き（水平／垂直）と落下ブロックの可否は、未指定なら対話で尋ねる。非対話（非 TTY / `--yes`）では既定（壁・南向き / 落下ブロック使わない）を採り警告を出す
11. 落下ブロックの非対話既定は「使わない」。要件の既定パレット（明示的な除外指定なし）より一段安全側に倒す
12. `--facing` のみ指定時は尋ねず `wall` + 指定正面
13. 最近傍の距離行列は分割 argmin する（1000×1000 でもメモリは格子程度）
14. `load.json` / `tick.json` は置かない
15. README は PEP 723 配布に合わせる。Bedrock はしない
16. fill / setblock の相対は 0 が `~`、負が `~-N`

## 確認したい点

| # | 内容 | 本書での暫定 |
|---|---|---|
| A | 壁の正面に `north` を出すか。レビュー役の「north はエラー」案 | **決着**。南・北・東・西の 4 つを v1 で出す。北は南の左右反転。`north` はエラーにしない（レビュー案は不採用）。要件の「南北」は XY の両方 |
| B | ~~砂・砂利・コンクリートパウダーは壁配置で落下する。既定パレットから外すか~~ | **決着**。未指定なら対話で尋ねる。非対話の既定は「使わない」。要件へ反映済み |
| C | 縮小はアスペクト比を保たない（指定サイズちょうど）でよいか | 保たない。要件の「指定サイズへ圧縮」に沿う |
| D | プレビューの拡大倍率オプションは要るか | v1 では 1 セル = 1 ピクセルのみ |
