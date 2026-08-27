# minecraft-pixelart

画像を Minecraft (Java Edition 26.2) のブロック配置に変換し、データパックとして書き出す CLI ツールです。

> [!NOTE]
> - 本ツールは **Java Edition 26.x**（26.1 〜 26.3 スナップショット等）に対応しています。Bedrock Edition (統合版) には対応していません。
> - Mod は不要で、生成されたデータパックをワールドの `datapacks/` に入れるだけで使用できます。

---

## 必要な環境

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/)（推奨）または Python 仮想環境

---

## 実行方法

### 1. uv を使用する場合（推奨）

依存パッケージ（pillow, numpy）のインストール不要で、そのまま直接実行できます（PEP 723 対応）。

```bash
# 画像パスを指定して実行（例: cat.png の場合 -> output/cat に出力され、/function cat:build で実行）
uv run pixelart.py images/cat.png -W 100 -H 100

# 画像を省略して対話的に選択
uv run pixelart.py -W 100 -H 100

# ワールドの datapacks フォルダへ直接出力する場合
uv run pixelart.py images/cat.png -W 100 -H 100 --out "C:/Users/<ユーザー名>/AppData/Roaming/.minecraft/saves/<ワールド名>/datapacks"
```

### 2. 通常の Python を使用する場合

```bash
pip install pillow numpy
python pixelart.py images/cat.png -W 100 -H 100
```

---

## ディレクトリ構成と個別化仕様

- `images/`: 元画像（PNG等）を配置するフォルダ。引数で画像パスを省略した場合、このフォルダ内の画像が対話選択肢として一覧表示されます。
- `output/previews/<画像名>.png`: 各画像のプレビュー画像保存先（画像ごとに個別保存）。
- `output/<画像名>/`: 各画像の Minecraft データパックフォルダ（複数画像を変換しても上書きされません）。

---

## 主なオプション

| オプション | 既定値 | 説明 |
|---|---|---|
| `IMAGE` | （省略可） | 入力画像ファイルのパス。未指定時は `images/` から対話選択 |
| `-W`, `--width` | （必須） | 横のブロック数（回転前） |
| `-H`, `--height` | （必須） | 縦のブロック数（回転前） |
| `--orientation` | 対話 / `wall` | `wall`（垂直・壁）または `floor`（水平・床） |
| `--facing` | 対話 / `south` | 壁の正面方角（`south` / `north` / `east` / `west`） |
| `--rotate` | `0` | 時計回りの回転角度（`0`, `90`, `180`, `270`） |
| `--mirror` | 無効 | 左右反転（回転の後に適用） |
| `--coords` | `relative` | `relative`（相対座標）または `absolute`（絶対座標） |
| `--origin X Y Z` | なし | `--coords absolute` 時の開始座標 |
| `--gravity-blocks` | 対話 / `exclude` | 落下ブロック（砂・砂利等）を使うか（`use` / `exclude`） |
| `--pack-name` | 画像名から自動設定 | データパックのフォルダ名（未指定時は入力ファイル名） |
| `--namespace` | 画像名から自動設定 | 関数名前空間（未指定時は入力ファイル名） |
| `--function` | `build` | エントリ関数名 |
| `--out` | `./output` | 出力ディレクトリ |
| `--preview` | `<out>/previews/<画像名>.png` | プレビュー画像の出力先 |
| `-y`, `--yes` | 無効 | 対話質問をスキップし、すべて既定値を採用 |

---

## データパックの配置とワールドでの実行手順

### 1. データパックの配置（階層構造の注意点）

出力されたデータパックフォルダ（例: `output/cat`）を、セーブデータの `datapacks/` フォルダ内に配置します。

> [!IMPORTANT]
> **階層構造に注意してください！**  
> `datapacks` フォルダの直下に直接 `data` や `pack.mcmeta` を展開してはいけません。必ず **データパック名（`cat` 等）のフォルダ** が必要です。

```text
.minecraft/saves/<ワールド名>/datapacks/
└── cat/                          ← ★このフォルダごと配置してください
    ├── pack.mcmeta
    └── data/
        └── cat/
            └── function/
                └── build.mcfunction
```

- ⭕ **正しい配置**: `.../datapacks/cat/pack.mcmeta`
- ❌ **誤った配置**: `.../datapacks/pack.mcmeta` (データパックとして認識されません)
- ❌ **誤った配置**: `.../datapacks/output/cat/pack.mcmeta` (二重フォルダ)

### 2. ワールドでの実行

1. ワールドに入ります（ワールド起動中の場合はチャットで `/reload` を実行）。
2. ドット絵を出したい位置に立って、チャットで以下を実行します：
   ```mcfunction
   /function <画像名>:build
   ```
   *(例: `cat.png` から作った場合 -> `/function cat:build`)*

---

## トラブルシューティング

### ❓ 「不明な関数です (Unknown function)」と表示される場合

#### チェック 1: `/datapack list` でデータパックが認識されているか
ゲーム内で `/datapack list` を実行します。
- **一覧に表示されない場合**:
  上記の「階層構造」がずれている可能性があります。`datapacks` の直下に `cat` などの個別フォルダがあるか確認してください。
- **赤色（無効）で表示されている場合**:
  `pack.mcmeta` のバージョン形式がプレイ中の Minecraft と一致していません（下記チェック 2 を参照）。

#### チェック 2: `pack.mcmeta` のバージョン形式
本ツールは 26.x 世代に対応するよう `min_format: [101, 1]`, `max_format: 120` を出力します。
- Minecraft のゲーム内で `/version` コマンドを実行すると、現在のデータパックフォーマット番号を確認できます（例: 26.1 は `101.1`、26.2 は `107.1`、26.3 スナップショットは `108`）。
- もし古い安定版（1.21.4 等）で動かす場合は、`pack.mcmeta` を開き `"pack_format": 61` のように該当バージョンの整数値に変更して保存し、`/reload` を実行してください。

---

### ⚠️ 大きなドット絵で途中でブロック配置が止まる場合

総コマンド数が Minecraft の既定コマンドチェーン上限（既定 65536）を超える場合、途中で配置が停止します。
ゲーム内で以下のコマンドを実行して上限を引き上げてください。

```mcfunction
/gamerule maxCommandChainLength 2000000
```
