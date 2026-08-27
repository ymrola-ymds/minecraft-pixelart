# /// script
# dependencies = [
#   "pillow",
#   "numpy",
# ]
# ///

import os
from PIL import Image

# ==========================================
# 設定
# ==========================================
IMAGE_PATH = "mieru.png"   # 入力画像
GRID_W = 240                             # 元画像の横マス数
GRID_H = 300                             # 元画像の縦マス数
DATAPACK_NAME = "pixelart_240x300"       # データパックフォルダ名

# 回転設定（お好みの向きを指定してください）
# 0   : 回転なし（元の向き）
# 90  : 時計回りに90度回転
# 180 : 180度回転（上下逆）
# 270 : 反時計回りに90度回転（時計回りに270度）
ROTATION = 90

# 左右反転したい場合は True
MIRROR_HORIZONTAL = False

# 開始位置設定
MODE = "relative"  # "relative" または "absolute"
START_X = 0
START_Y = 64
START_Z = 0
# ==========================================

PALETTE = {
    # コンクリート
    "minecraft:white_concrete": (207, 213, 214),
    "minecraft:orange_concrete": (224, 97, 0),
    "minecraft:magenta_concrete": (169, 48, 159),
    "minecraft:light_blue_concrete": (35, 137, 198),
    "minecraft:yellow_concrete": (241, 175, 21),
    "minecraft:lime_concrete": (94, 169, 24),
    "minecraft:pink_concrete": (214, 101, 143),
    "minecraft:gray_concrete": (54, 57, 61),
    "minecraft:light_gray_concrete": (125, 125, 115),
    "minecraft:cyan_concrete": (21, 119, 136),
    "minecraft:purple_concrete": (100, 31, 156),
    "minecraft:blue_concrete": (44, 46, 143),
    "minecraft:brown_concrete": (96, 60, 32),
    "minecraft:green_concrete": (73, 91, 36),
    "minecraft:red_concrete": (142, 32, 32),
    "minecraft:black_concrete": (8, 10, 15),

    # テラコッタ
    "minecraft:terracotta": (150, 92, 66),
    "minecraft:white_terracotta": (209, 178, 161),
    "minecraft:orange_terracotta": (161, 83, 37),
    "minecraft:magenta_terracotta": (149, 88, 108),
    "minecraft:light_blue_terracotta": (113, 108, 137),
    "minecraft:yellow_terracotta": (186, 133, 35),
    "minecraft:lime_terracotta": (103, 117, 52),
    "minecraft:pink_terracotta": (161, 78, 78),
    "minecraft:gray_terracotta": (57, 42, 35),
    "minecraft:light_gray_terracotta": (135, 106, 97),
    "minecraft:cyan_terracotta": (86, 91, 91),
    "minecraft:purple_terracotta": (118, 70, 86),
    "minecraft:blue_terracotta": (74, 60, 91),
    "minecraft:brown_terracotta": (77, 51, 35),
    "minecraft:green_terracotta": (76, 83, 42),
    "minecraft:red_terracotta": (143, 61, 46),
    "minecraft:black_terracotta": (37, 22, 16),

    # 羊毛
    "minecraft:white_wool": (233, 236, 236),
    "minecraft:orange_wool": (240, 118, 19),
    "minecraft:magenta_wool": (189, 68, 179),
    "minecraft:pink_wool": (237, 141, 172),
    "minecraft:yellow_wool": (248, 197, 39),

    # 白系
    "minecraft:smooth_quartz": (235, 229, 222),
    "minecraft:snow_block": (249, 254, 254),
}

def rgb_distance(c1, c2):
    r_mean = (c1[0] + c2[0]) / 2.0
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return (2 + r_mean / 256.0) * (dr**2) + 4.0 * (dg**2) + (2 + (255 - r_mean) / 256.0) * (db**2)

def find_closest_block(rgb):
    min_dist = float("inf")
    best_block = "minecraft:white_concrete"
    for block, col in PALETTE.items():
        dist = rgb_distance(rgb, col)
        if dist < min_dist:
            min_dist = dist
            best_block = block
    return best_block

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"エラー: 画像 '{IMAGE_PATH}' が見つかりません。")
        return

    img = Image.open(IMAGE_PATH).convert("RGB")
    orig_w, orig_h = img.size

    # 1. 各マスの中心から色を取得
    grid_img = Image.new("RGB", (GRID_W, GRID_H))
    for gz in range(GRID_H):
        py = int((gz + 0.5) * orig_h / GRID_H)
        for gx in range(GRID_W):
            px = int((gx + 0.5) * orig_w / GRID_W)
            grid_img.putpixel((gx, gz), img.getpixel((px, py)))

    # 2. 回転・反転処理
    if ROTATION == 90:
        grid_img = grid_img.transpose(Image.Transpose.ROTATE_270) # 時計回り90度
    elif ROTATION == 180:
        grid_img = grid_img.transpose(Image.Transpose.ROTATE_180)
    elif ROTATION == 270:
        grid_img = grid_img.transpose(Image.Transpose.ROTATE_90)  # 反時計回り90度

    if MIRROR_HORIZONTAL:
        grid_img = grid_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    final_w, final_h = grid_img.size
    print(f"配置サイズ: 横 {final_w} ブロック × 縦 {final_h} ブロック")

    # プレビュー保存（回転後の見た目確認用）
    grid_img.save("preview.png")

    # 3. ブロックマッピング & /fill 圧縮
    block_grid = []
    for z in range(final_h):
        row = []
        for x in range(final_w):
            rgb = grid_img.getpixel((x, z))
            row.append(find_closest_block(rgb))
        block_grid.append(row)

    commands = []
    for z in range(final_h):
        x_start = 0
        while x_start < final_w:
            b = block_grid[z][x_start]
            x_end = x_start
            while x_end + 1 < final_w and block_grid[z][x_end + 1] == b:
                x_end += 1

            if x_start == x_end:
                if MODE == "relative":
                    cmd = f"setblock ~{x_start} ~ ~{z} {b}"
                else:
                    cmd = f"setblock {START_X + x_start} {START_Y} {START_Z + z} {b}"
            else:
                if MODE == "relative":
                    cmd = f"fill ~{x_start} ~ ~{z} ~{x_end} ~ ~{z} {b}"
                else:
                    cmd = f"fill {START_X + x_start} {START_Y} {START_Z + z} {START_X + x_end} {START_Y} {START_Z + z} {b}"
            commands.append(cmd)
            x_start = x_end + 1

    # 4. データパック出力（function / functions の両方に書き出し）
    for sub in ["function", "functions"]:
        f_dir = os.path.join(DATAPACK_NAME, "data", "pixelart", sub)
        os.makedirs(f_dir, exist_ok=True)
        with open(os.path.join(f_dir, "build.mcfunction"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(commands))

    print(f"回転完了！ コマンド行数: {len(commands):,} 行")

if __name__ == "__main__":
    main()