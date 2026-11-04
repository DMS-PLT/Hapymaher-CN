#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハピメア 本体 OP《夢の無限回廊》特效字幕渲染主入口。"""
import os
import sys
import subprocess
from PIL import Image, ImageFont

import config as C
from assparse import load_lines
from effects.lyric import LyricLine
from effects.apart import (
    StorybookDreamTruth,
    EphemeralCrumble,
    PhantomTouchCandles,
    ConvexMirrorEternity,
)
from effects.bpart import (
    CheckerboardChaseEscape,
    HeroineTriadOverexpose,
)
from effects.chorus import (
    SpiralPrismEntry,
    PocketwatchMiracleMotes,
    WhiteRoseToBlueDream,
    ChiaroscuroBondReach,
    CrimsonInkBlotFinale,
    OutroTagline,
    with_underlay,
)

fJP = ImageFont.truetype(C.FONT_PATH_JP, C.FONT_SIZE_JP)
fCN = ImageFont.truetype(C.FONT_PATH_CN, C.FONT_SIZE_CN)

LINES = load_lines()
layers = []
jp_layers = []
cn_layers = []

# =====================================================================
#  全片动态安全区版式规划 (精准避让全部原生署名与 B段巨幅角色名牌!)
#    - L00, L01 (左下有『原画 克/月杜尋』): 日文左上 + 中文右下 (\ 对角呼应)
#    - L02, L03 (右下有『シナリオ 森崎亮人』& 青烛): 日文右上 + 中文左下 (/ 对角呼应, L03 上提留足镜面倒影净空)
#    - L04, L05 (B段下半屏 y=760..975 铺满五女主名牌): 左上哥特双行并列!
#    - L06 ~ L10 (副歌全屏无职员表): 日文左上 + 中文右下 (\ 经典对角)
#    - L11      (右下有『ディレクター / ムービーデザイン』): 日文右上 + 中文左下 (/ 对角避让)
# =====================================================================
def _layout_for_line(li: int):
    if li in (0, 1):
        return ("left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y, -1.0)
    elif li == 2:
        return ("right", C.W - C.MARGIN_X, C.TOP_Y, "left", C.MARGIN_X, C.BOT_Y, 1.0)
    elif li == 3:
        # L03 留出正下方 ~45px 凸面魔镜水波倒影空间
        return ("right", C.W - C.MARGIN_X, C.TOP_Y - 2, "left", C.MARGIN_X, C.BOT_Y - 30, 1.0)
    elif li == 4:
        # L04 右上哥特双行并列: 100% 避让有栖(左上脸庞)、莲乃咲及底部巨幅名牌, 且留出向右逃逸余量!
        return ("right", C.W - 126, 46, "right", C.W - 126, 116, -1.0)
    elif li == 5:
        # L05 左上哥特双行并列: 100% 稳居弥生/景子/舞亚左侧暗红蔷薇纹净空区!
        return ("left", C.MARGIN_X, 48, "left", C.MARGIN_X, 118, 1.0)
    elif li == 11:
        return ("right", C.W - C.MARGIN_X, C.TOP_Y, "left", C.MARGIN_X, C.BOT_Y, 1.0)
    else:
        return ("left", C.MARGIN_X, C.TOP_Y, "right", C.W - C.MARGIN_X, C.BOT_Y, -1.0)


for L in LINES:
    jp_align, jp_x, jp_y, cn_align, cn_x, cn_y, cn_sdir = _layout_for_line(L.li)
    jl = LyricLine(
        L.jp, fJP, anchor_x=jp_x, y=jp_y, start=L.start, end=L.end,
        align=jp_align, mode="karaoke", syls=L.syls,
        fill_top=C.JP_TOP_COL, fill_bot=C.JP_BOT_COL, glow_col=C.GLOW_JP,
        spacing=C.CHAR_SPACING_JP, synth_bold=0,
    )
    cl = LyricLine(
        L.cn, fCN, anchor_x=cn_x, y=cn_y, start=L.start, end=L.end,
        align=cn_align, mode="cn_slide",
        fill_top=C.CN_TOP_COL, fill_bot=C.CN_BOT_COL, glow_col=C.GLOW_CN,
        spacing=C.CHAR_SPACING_CN, synth_bold=C.CN_SYNTH_BOLD, slide_dir=cn_sdir,
    )
    jp_layers.append(jl)
    cn_layers.append(cl)
    layers.extend([jl, cl])

# =====================================================================
#  A 段分镜演出挂载 (L00 ~ L03, 27.31s ~ 44.57s)
# =====================================================================
# [L00] 羊皮纸绘本暖金浮尘 + 『夢(迷幻紫粉微蝶)』vs『まこと(冷澈银青实像)』
layers.append(StorybookDreamTruth(jp_layers[0], cn_layers[0], font_jp=fJP, font_cn=fCN))

# [L01] 34.86s 苍白之手坠入红黑棋盘:『とても儚く / 虚幻易碎』完整亮起后剥落化作金尘与猩红花瓣!
layers.append(EphemeralCrumble(jp_layers[1], cn_layers[1], t_crumble=34.86))

# [L02]『触れば消える』触碰泡沫半透淡隐 + 『刹那の光』四色幽冥烛火 (38.35s青/38.86s品红/39.50s琥珀/39.85s翠绿) 逐帧同步!
layers.append(PhantomTouchCandles(jp_layers[2], cn_layers[2], font_jp=fJP, font_cn=fCN))

# [L03] 40.60s 凸面黑魔镜实时水波倒影 + 句尾镜线收束锁住『永遠に残して / 将它永远留存』镜中独白!
layers.append(ConvexMirrorEternity(jp_layers[3], cn_layers[3]))

# =====================================================================
#  B 段分镜演出挂载 (L04 ~ L05, 44.57s ~ 63.48s -> 63.58s 圣白过曝入副歌)
# =====================================================================
# [L04] 右上双行暗丝绒衬底 + 48.42s 红白棋盘菱形切镜波 + 49.62s『逃げていく / 远逃而去』拉开残影逃逸!
layers.append(CheckerboardChaseEscape(jp_layers[4], cn_layers[4]))

# [L05] 左上双行三女主代表色流转 + 景子吉他琴弦拨动共振 + 63.30s 纯白圣光过曝消融!
layers.append(HeroineTriadOverexpose(jp_layers[5], cn_layers[5], font_jp=fJP, font_cn=fCN))

# =====================================================================
#  副歌分镜演出挂载 (L06 ~ L11, 63.48s ~ 109.08s) + 尾奏 2:00 猩红题记
# =====================================================================
# [L06] 黄金螺旋入场 + 双螺旋流光丝带 + 69.5s 咲镜面棱镜彩虹色散折射!
layers.extend(with_underlay(SpiralPrismEntry(jp_layers[6], cn_layers[6], font_jp=fJP, font_cn=fCN)))

# [L07] 72.8s 古铜金怀表星盘跳秒滴答 + 76.8s 彩窗暖金光斑与翠绿凤蝶微尘!
layers.extend(with_underlay(PocketwatchMiracleMotes(jp_layers[7], cn_layers[7], font_jp=fJP, font_cn=fCN)))

# [L08 + L09] 82.83s 纯白蔷薇轰然炸裂绯红花瓣 -> 86.46s 粉紫梦境光晕与有栖沧蓝幻蝶!
layers.extend(with_underlay(WhiteRoseToBlueDream(
    jp_layers[8], cn_layers[8], jp_layers[9], cn_layers[9], font_jp=fJP, font_cn=fCN
)))

# [L10] 暗黑棋盘舞台追光 + 『取り戻す/重新夺回』红线相扣牵引 + 93.23s/97.94s 双人剪影花瓣爆散!
layers.extend(with_underlay(ChiaroscuroBondReach(jp_layers[10], cn_layers[10])))

# [L11] 走马灯紫蓝幽光脉动 + 106.92s~109.08s 分形猩红血墨斑块染红吞噬退场!
layers.append(CrimsonInkBlotFinale(jp_layers[11], cn_layers[11], font_jp=fJP, font_cn=fCN))

# [尾奏 2:00 猩红题记] 119.50s~124.88s 原生级内嵌『这是一个甜蜜而又幸福的恶梦故事』
layers.append(OutroTagline())

# 图层按 z 轴排序
layers.sort(key=lambda l: l.z)

# =====================================================================
#  主渲染循环
# =====================================================================
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
    canvas = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    for layer in layers:
        layer.draw(canvas, t)
    out.write(canvas.tobytes())
    if (fi - fi0) % 120 == 0:
        print(f"frame {fi}/{N}  t={t:.1f}s", file=sys.stderr)

print("overlay done", file=sys.stderr)
