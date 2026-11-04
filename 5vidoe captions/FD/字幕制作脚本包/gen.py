#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハピメア FD (-Fragmentation Dream-) OP《幻想楼閣》特效字幕渲染主入口。"""
import os
import sys
import subprocess
from PIL import Image, ImageFont

import config as C
from assparse import load_lines
from effects.base import with_underlay
from effects.lyric import LyricLine
from effects.prologue import (
    SpotlightPiercingDarkness,
    GrimoirePageTurn,
    SapphireDreamTrace,
    CorridorEpigraph,
)
from effects.abpart import (
    WakingHollowReality,
    WonderlandCardsLie,
    BlueSwallowtailPetals,
    WineglassOverflowDye,
    EchoingFarewellEden,
)
from effects.chorus import (
    ThornsAndBloodTrail,
    BurningChestRose,
    SlashScarsMelt,
    EcstasyStarlightRipples,
    YandereLoveKillFlash,
    HeartLockboxCage,
    ClosedRoomWarmWorld,
    EternalGoldenStream,
    EncoreVelvetCurtain,
)

fJP = ImageFont.truetype(C.FONT_PATH_JP, C.FONT_SIZE_JP)
fCN = ImageFont.truetype(C.FONT_PATH_CN, C.FONT_SIZE_CN)

LINES = load_lines()
layers = []
jp_layers = []
cn_layers = []


# =====================================================================
#  全片 20 句昼夜双极配色 + 角色名牌零碰撞安全区版式规划:
#    - L00~L03 : 暗夜序幕 & 梦醒教室 -> night 象牙白, 左上日文 + 右下中文
#    - L04(有子): 纯白茶会, 左立绘+中右名牌 -> crimson 绯红墨, 右上日文 + 右下中文
#    - L05(彼女): 纯白茶会, 右立绘+左下『彼女』 -> crimson 绯红墨, 左上双行并列!
#    - L06(蓝蝶): 纯白花瓣凤蝶 -> crimson 绯红墨, 左上日文 + 右下中文
#    - L07(咲)  : 纯白茶会, 左立绘+右上『蓮乃咲』 -> crimson 绯红墨, 右下双行并列!
#    - L08(弥生): 纯白茶会, 右立绘+左下『弥生』 -> crimson 绯红墨, 左上双行并列!
#    - L09(景子): 纯白茶会, 左立绘+中右『平坂景子』 -> crimson 绯红墨, 右上双行并列!
#    - L10(舞亚): 60.90s crimson 入场 -> 61.83s 帧同步翻转为 night 暗夜荆棘象牙白!
#    - L11~L19  : 副歌高潮 -> night 象牙白 (+ 高亮切镜无框柔光云护航, 完美避让左下原画署名)
# =====================================================================
def _spec_for_line(li: int):
    # 返回: (theme, jp_align, jp_x, jp_y, cn_align, cn_x, cn_y, cn_slide_dir)
    if li in (0, 1, 2, 3):
        return ("night", "left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y, -1.0)
    elif li == 4:
        return ("crimson", "right", C.W - C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y - 2, -1.0)
    elif li == 5:
        return ("crimson", "left", C.MARGIN_X, 48, "left", C.MARGIN_X, 118, 1.0)
    elif li == 6:
        return ("crimson", "left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y - 2, -1.0)
    elif li == 7:
        return ("crimson", "right", C.W - C.MARGIN_X, 864, "right", C.W - C.MARGIN_X, 934, -1.0)
    elif li == 8:
        return ("crimson", "left", C.MARGIN_X, 48, "left", C.MARGIN_X, 118, 1.0)
    elif li == 9:
        return ("crimson", "right", C.W - C.MARGIN_X, 42, "right", C.W - C.MARGIN_X, 110, -1.0)
    elif li == 10:
        return ("crimson", "left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y, -1.0)
    else:
        return ("night", "left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y, -1.0)


for L in LINES:
    theme, jp_al, jp_x, jp_y, cn_al, cn_x, cn_y, cn_sdir = _spec_for_line(L.li)
    jl = LyricLine(
        L.jp, fJP, anchor_x=jp_x, y=jp_y, start=L.start, end=L.end,
        align=jp_al, mode="karaoke", syls=L.syls, theme=theme, is_cn=False,
        spacing=C.CHAR_SPACING_JP, synth_bold=0,
    )
    cl = LyricLine(
        L.cn, fCN, anchor_x=cn_x, y=cn_y, start=L.start, end=L.end,
        align=cn_al, mode="cn_slide", theme=theme, is_cn=True,
        spacing=C.CHAR_SPACING_CN, synth_bold=C.CN_SYNTH_BOLD, slide_dir=cn_sdir,
    )
    jp_layers.append(jl)
    cn_layers.append(cl)
    layers.extend([jl, cl])


# =====================================================================
#  1. 序幕 + 0:25 纯白走廊原生题记挂载 (0:00.68 ~ 0:30.24)
# =====================================================================
layers.extend(with_underlay(SpotlightPiercingDarkness(jp_layers[0], cn_layers[0], fJP, fCN)))
layers.extend(with_underlay(GrimoirePageTurn(jp_layers[1], cn_layers[1])))
layers.append(SapphireDreamTrace(jp_layers[2], cn_layers[2], fJP, fCN))
layers.append(CorridorEpigraph())

# =====================================================================
#  2. A 段 + B 段纯白茶会与禁忌伊甸挂载 (0:33.38 ~ 1:06.42)
# =====================================================================
layers.append(WakingHollowReality(jp_layers[3], cn_layers[3], fJP, fCN))
layers.extend(with_underlay(WonderlandCardsLie(
    jp_layers[4], cn_layers[4], jp_layers[5], cn_layers[5], fJP, fCN
)))
layers.append(BlueSwallowtailPetals(jp_layers[6], cn_layers[6]))
layers.extend(with_underlay(WineglassOverflowDye(
    jp_layers[7], cn_layers[7], jp_layers[8], cn_layers[8], fJP, fCN
)))
layers.extend(with_underlay(EchoingFarewellEden(
    jp_layers[9], cn_layers[9], jp_layers[10], cn_layers[10], fJP, fCN
)))

# =====================================================================
#  3. 副歌高潮幻想楼阁全分镜挂载 (1:06.68 ~ 1:42.80)
# =====================================================================
layers.extend(with_underlay(ThornsAndBloodTrail(jp_layers[11], cn_layers[11], fJP, fCN)))
layers.extend(with_underlay(BurningChestRose(jp_layers[12], cn_layers[12], fJP, fCN)))
layers.extend(with_underlay(SlashScarsMelt(jp_layers[13], cn_layers[13], fJP, fCN)))
layers.extend(with_underlay(EcstasyStarlightRipples(jp_layers[14], cn_layers[14], fJP, fCN)))
layers.extend(with_underlay(YandereLoveKillFlash(jp_layers[15], cn_layers[15], fJP, fCN)))
layers.extend(with_underlay(HeartLockboxCage(jp_layers[16], cn_layers[16])))
layers.extend(with_underlay(ClosedRoomWarmWorld(jp_layers[17], cn_layers[17], fJP, fCN)))
layers.extend(with_underlay(EternalGoldenStream(jp_layers[18], cn_layers[18], fJP, fCN)))
layers.extend(with_underlay(EncoreVelvetCurtain(jp_layers[19], cn_layers[19], fJP, fCN)))

# 按图层深度排序
layers.sort(key=lambda l: l.z)

def render_frame(t: float) -> Image.Image:
    canvas = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    for layer in layers:
        layer.draw(canvas, t)
    return canvas


def main():
    def _overlay_frame_count():
        """按基底最后一个视频帧生成裸流，避免 VFR 基底提前结束时管道被切断。"""
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_packets", "-show_entries", "packet=pts_time",
                "-of", "csv=p=0",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), C.BASE_VIDEO),
            ],
            text=True,
        )
        last_pts = max(float(x) for x in out.splitlines() if x.strip())
        # 多留 1 帧越过末尾静止段，确保 overlay 能输出基底的最后一个主帧。
        return int(round(last_pts * C.FPS)) + 2

    N = _overlay_frame_count()
    _T0 = float(os.environ.get("PREVIEW_T0", 0.0))
    _T1 = float(os.environ.get("PREVIEW_END", N / C.FPS + 1.0))
    fi0 = max(0, round(_T0 * C.FPS))
    fi1 = min(N, round(_T1 * C.FPS))

    out = sys.stdout.buffer
    for fi in range(fi0, fi1):
        t = fi / C.FPS
        canvas = render_frame(t)
        out.write(canvas.tobytes())
        if (fi - fi0) % 120 == 0:
            print(f"frame {fi}/{N}  t={t:.1f}s", file=sys.stderr)

    print("overlay done", file=sys.stderr)


if __name__ == "__main__":
    main()
