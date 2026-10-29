#!/usr/bin/env python3
r"""check_align.py — 检查你 PS 改过的 title_chip 有没有跟原版对不上位。

背景：`title_chip` 里每个菜单项有**四个横排变体**（同一行 y、横向并排四格），
引擎按状态挑一格画：

| 格 | 原图长什么样 | 推测用途 |
|---|---|---|
| ① | 金色字，无左右小方块 | 普通 |
| ② | 白字 + 左右红白小方块 | 选中 / 悬停 |
| ③ | 白字 + 左右红白小方块 | 按下（原版**故意比 ①② 低 2px**，做按压手感） |
| ④ | 暗色、半透明，无方块 | 禁用（如无存档时的「继续开始」） |

**引擎换状态时画的是另一格，所以四格的字必须各自落在原位**；差 1px 就能看出来
（鼠标移上去文字「跳」一下）。这个脚本把每格的字顶和原版比，直接报差几像素。

用法：

    # 对比 原版 pb3  <->  你改完的 PNG
    uv run python tools/check_align.py \
        --orig "UI界面/chip/title_chip.pb3" --edit "UI界面/chip_png/title_chip.png"

    # 直接吃 pb3（比如已经编回去的）
    uv run python tools/check_align.py --orig ... --edit "UI界面/chip_new/title_chip.pb3"

`--edit` 给 pb3 时会自动认 Form A / Form B 两种形态。

⚠ 布局是**按 title_chip 量死**的（5 个按钮 × 4 格）。换别的图要改下面两张表。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pb3  # noqa: E402

# title_chip 的实测布局（1920x1920）
BANDS = [(1090, 1146), (1150, 1206), (1206, 1266), (1270, 1326), (1330, 1390)]
COLS = [(38, 248), (288, 540), (552, 808), (846, 1056)]
VARIANT = ["1普通", "2选中A", "3按下", "4禁用"]
SOLID = 150      # alpha 阈值：只算实心笔画，把外发光排除掉


def to_rgba_pixels(path: Path):
    """读 pb3 或 PNG，统一成 (w, h, pixel_accessor)"""
    d = path.read_bytes()
    if d[:4] == pb3.SIG:
        raw = bytearray(d)
        if not pb3.looks_plain(bytes(raw)):
            pb3.decrypt_pb3(raw)
        w, h, rgba = pb3.decode(bytes(raw))
        from PIL import Image
        return Image.frombytes("RGBA", (w, h), rgba).load(), w, h
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    return im.load(), im.width, im.height


def text_top(px, x0, x1, y0, y1, thr=SOLID):
    """格子里「文字」的最上一行 —— 中间 3/5 取样，避开左右两个方块标记"""
    m0, m1 = x0 + (x1 - x0) // 5, x1 - (x1 - x0) // 5
    ys = [y for y in range(y0, y1) if any(px[x, y][3] > thr for x in range(m0, m1))]
    return min(ys) if ys else None


def write_guide(orig: Path, out: Path) -> None:
    """生成一张透明底的「对齐参考线」PNG，可以当图层贴进 PS 对着摆。

    每格画两条横线（字顶实色 / 字底淡色，颜色按格子区分）+ 一条水平中心刻度。
    """
    from PIL import Image, ImageDraw

    px, w, h = to_rgba_pixels(orig)
    colors = [(255, 70, 70), (70, 255, 70), (80, 170, 255), (255, 235, 60)]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y0, y1 in BANDS:
        for ci, (x0, x1) in enumerate(COLS):
            m0, m1 = x0 + (x1 - x0) // 5, x1 - (x1 - x0) // 5
            ys = [y for y in range(y0, y1)
                  if any(px[x, y][3] > SOLID for x in range(m0, m1))]
            if not ys:
                continue
            t, b = min(ys), max(ys)
            xs = [x for x in range(x0, x1)
                  if any(px[x, y][3] > SOLID for y in range(t, b + 1))]
            c = colors[ci]
            d.line([(x0, t), (x1, t)], fill=c + (255,), width=1)     # 字顶
            d.line([(x0, b), (x1, b)], fill=c + (110,), width=1)     # 字底
            cx = (min(xs) + max(xs)) // 2
            d.line([(cx, t - 6), (cx, b + 6)], fill=c + (200,), width=1)
    img.save(out)
    print(f"参考线已存 {out}")
    print("  红=①普通  绿=②选中A  蓝=③按下  黄=④禁用；实线=字顶，淡线=字底，竖线=水平中心")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orig", required=True, help="原版 title_chip（pb3）")
    ap.add_argument("--edit", help="你改完的（PNG 或 pb3）；只生成参考线时可以不给")
    ap.add_argument("--guide", help="顺带生成对齐参考线 PNG 到这个路径")
    a = ap.parse_args()

    if a.guide:
        write_guide(Path(a.orig), Path(a.guide))
    if not a.edit:
        return 0 if a.guide else 1

    po, wo, ho = to_rgba_pixels(Path(a.orig))
    pe, we, he = to_rgba_pixels(Path(a.edit))
    if (wo, ho) != (we, he):
        print(f"✗ 尺寸不同：原版 {wo}x{ho}，你的 {we}x{he} —— 别动画布尺寸")
        return 1

    print(f"字顶对比（+ = 你的比原版低）   [原版分析过 {wo}x{ho}]")
    print(f"{'':8}" + "".join(f"{v:>13}" for v in VARIANT))
    bad = 0
    for bi, (y0, y1) in enumerate(BANDS, 1):
        cells = []
        for x0, x1 in COLS:
            t0 = text_top(po, x0, x1, y0, y1)
            t1 = text_top(pe, x0, x1, y0, y1)
            if t0 is None or t1 is None:
                cells.append(f"{'(空)':>13}")
                continue
            d = t1 - t0
            if d:
                bad += 1
            cells.append(f"{t0:>6}->{t1:<4}{d:+2d}")
        print(f"按钮{bi}   " + "".join(cells))

    print()
    if bad:
        print(f"⚠ {bad} 处对不上。差 1px 引擎画出来就能看出跳动 —— 建议回 PS 把它们各自对回原位。")
        print("  省事的做法：文字只画一次，然后**复制同一个图层**放到四格，只改颜色/描边/不透明度。")
        print("  每一格重新打字或手动挪，必然差 1~3px。")
    else:
        print("✓ 四格全部与原版对齐，悬停/按下都不会跳。")
    print()
    print("注：③（按下）在原版里**故意比 ①② 低 2px**。想保留原手感就该有这 -2；")
    print("    想四格完全一致、一丝不动，那把它也抹平即可 —— 看你要哪种。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
