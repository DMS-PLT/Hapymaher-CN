# -*- coding: utf-8 -*-
"""ハピメア RE OP 特效字幕渲染器 (重构版 v6 - A段演出升级)
============================================
使用方法:
  # 单句/区间快速预览 (推荐先看 A 段: 0 1 2 3 4)
  python preview_line.py 0 1 2 3 4

  # 完整渲染成片
  python render.py
"""
import sys
import os
import subprocess
from PIL import Image, ImageFont

import config as C
from assparse import load_lines
from effects.lyric import LyricLine
from effects.vine import VineUnder, VineChars, VineCharsFront  # noqa: F401
from effects.pomegranate import RedBleed
from effects.apart import (
    ThornPierce,
    RosePetals,
    MemoryStingMotes,
    NegativeFlashSync,
    VioletFlameStage,
)
from effects.bpart import (
    ChromaticEntry,
    AntiqueBoxFrame,
    MemoryAmnesia,
    BrokenKeyFracture,
    RestraintPress,
    WarpedStrobeShatter,
)
from effects.chorus import (
    ChorusBurstTear,
    MoonRibbonTrail,
    ButterflyDreamFarewell,
    CageBarsOpen,
    WishStarlightAura,
    KeyRepairSweep,
    RubyRingReach,
    OutroRedactedCards,
)

# =====================================================================
#  初始化同族配对字体 (日文 DFKinBun-W5 + 中文 DFJinWenW3-GB)
# =====================================================================
fJP = ImageFont.truetype(C.FONT_PATH_JP, C.FONT_SIZE_JP)
fCN = ImageFont.truetype(C.FONT_PATH_CN, C.FONT_SIZE_CN)

# =====================================================================
#  加载歌词 (opre.ass 是唯一事实来源)
# =====================================================================
LINES = load_lines()
assert len(LINES) == 18, f"预期 18 句, 实际 {len(LINES)}"

# =====================================================================
#  构建基础双语歌词图层
# =====================================================================
layers = []
jp_layers, cn_layers = [], []

for L in LINES:
    # L16 左下角有原片大块主题曲 Credit, 中文自动切到右下角避让
    cn_align = "right" if L.li == 16 else "left"
    cn_x = C.JP_RIGHT if L.li == 16 else C.CN_LEFT

    jl = LyricLine(
        L, L.jp, font=fJP, fill=C.WHITE, glow=C.GLOW_JP,
        align="right", x_edge=C.JP_RIGHT, y_edge=C.JP_TOP,
        mode="karaoke", spacing=C.CHAR_SPACING,
    )
    cl = LyricLine(
        L, L.cn, font=fCN, fill=C.CN_COL, glow=C.GLOW_CN,
        align=cn_align, x_edge=cn_x, y_edge=C.CN_BOTTOM,
        mode="cn_slide", spacing=C.CHAR_SPACING_CN, synth_bold=C.CN_SYNTH_BOLD,
    )
    jp_layers.append(jl)
    cn_layers.append(cl)
    layers += [jl, cl]

# =====================================================================
#  A 段分镜演出特效 (L00 ~ L04, 20.80s ~ 36.19s)
# =====================================================================

# ---- [L00] バラの棘が刺さる / 如蔷薇尖刺扎入心扉 (20.80s ~ 23.34s) ----
# 1) 3x 超采样蔷薇荆棘横藤 (右上日文跟随演唱推进 + 左下中文首尾呼应)
layers.append(VineUnder(
    jp_layers[0], color=(124, 28, 48), thorn_hi=(220, 76, 100),
    t0=LINES[0].start, grow=LINES[0].dur * 0.92,
    t_wither=LINES[0].end - C.FADE_OUT, wdur=C.FADE_OUT,
))
layers.append(VineUnder(
    cn_layers[0], color=(112, 30, 50), thorn_hi=(204, 70, 94),
    t0=LINES[0].start + 0.08, grow=1.15,
    t_wither=LINES[0].end - C.FADE_OUT, wdur=C.FADE_OUT,
))
# 2) 『棘』『刺』穿刺寒芒细线 + 刺痛微震 (呼应桌面红线穿刺标题)
layers.append(ThornPierce(jp_layers[0], cn_layers[0], jp_indices=(3, 5)))
# 3) 随字飘落的景深红蔷薇花瓣
layers.append(RosePetals(jp_layers[0], count=7, seed=10))

# ---- [L01] 痛みの記憶ふいに思い出して / 那份剧痛的记忆 蓦然浮上心头 (23.41s ~ 27.84s) ----
# 『痛み』色散刺痛重影 + 25.50s 切入有栖角色卡时升起的发光蓝蝶微尘
layers.append(MemoryStingMotes(jp_layers[1], font_jp=fJP, t_card_cut=25.625))

# ---- [L02] 赤く滲むザクロ / 渗出绯红汁液的石榴 (28.47s ~ 31.32s) ----
# 1) 深血红荆棘藤衬底
layers.append(VineUnder(
    jp_layers[2], color=(146, 24, 46), thorn_hi=(238, 72, 92),
    t0=LINES[2].start, grow=LINES[2].dur * 0.90,
    t_wither=LINES[2].end - C.FADE_OUT, wdur=C.FADE_OUT,
))
# 2) 日文整句有机毛细渗红 + 『滲(idx=2)』『ロ(idx=6)』凝结石榴红珠垂落
layers.append(RedBleed(
    jp_layers[2], font=fJP,
    drip_indices={2, 6}, delay=0.05, bleed_dur=0.58,
))
# 3) 左下中文『渗出绯红汁液』(idx=0..5) 对角同步渗红 + 『渗』『红』凝珠呼应
layers.append(RedBleed(
    cn_layers[2], font=fCN,
    char_indices=[0, 1, 2, 3, 4, 5], drip_indices={0, 3},
    delay=0.95, bleed_dur=0.75, synth_bold=C.CN_SYNTH_BOLD,
))
# 4) 暗红宴会厅飘落花瓣
layers.append(RosePetals(jp_layers[2], count=6, seed=28, color=(182, 18, 42)))

# ---- [L03] 果実の味が / 那果实的滋味 (31.34s ~ 32.60s) ----
# 精准咬合原片 32.333s~32.500s 青蓝负片反相闪白冲击帧
layers.append(NegativeFlashSync(
    jp_layers[3], cn_layers[3], font_jp=fJP, font_cn=fCN,
    t_flash_start=32.458, t_flash_end=32.625,
))

# ---- [L04] 懐かしくて唇を噛む / 令人怀念得紧咬双唇 (32.60s ~ 36.19s) ----
# 34.167s 舞亚唇燃紫白妖火光晕接管 + 升腾紫焰 + 35.30s『噛む』轻咬牙印
layers.append(VioletFlameStage(
    jp_layers[4], cn_layers[4], font_jp=fJP, font_cn=fCN,
    t_flame=34.292, t_bite=35.30,
))

# =====================================================================
#  B 段分镜演出特效 (L05 ~ L09, 36.19s ~ 53.19s -> 53.65s 碎裂入副歌)
# =====================================================================

# ---- L05 ~ L07 公共镜头质感: 日常 CG 入场边缘红青色散收敛 ----
for _bi in (5, 6, 7):
    layers.append(ChromaticEntry(jp_layers[_bi], font=fJP))
    layers.append(ChromaticEntry(cn_layers[_bi], font=fCN, max_shift=2.6, synth_bold=C.CN_SYNTH_BOLD))

# ---- [L05] 古ぼけた箱の中にある / 深藏于陈旧木匣之中 (36.19s ~ 40.11s) ----
# 37.25s 原片切入红黑古典金画框 (恰逢唱到『箱』): 四角合拢勾勒古典暗金双线角花木盒画框 + 金尘微粒
layers.append(AntiqueBoxFrame(jp_layers[5], t_appear=37.375))
layers.append(AntiqueBoxFrame(cn_layers[5], t_appear=37.500, pad_x=12, pad_y=5))

# ---- [L06] 入れていたことも忘れ / 连曾亲手封存也已遗忘 (40.11s ~ 43.91s) ----
# 42.55s 画框人物变空白无脸剪影:『忘れ』与『也已遗忘』同步失焦雾化为空洞残影并剥落白灰微尘
layers.append(MemoryAmnesia(
    jp_layers[6], cn_layers[6], font_jp=fJP, font_cn=fCN,
    jp_indices=(8, 9), cn_indices=(6, 7, 8, 9), t_erase=42.55,
))

# ---- [L07] 鍵が壊れてる蓋のままで / 钥匙早已残损 任匣盖虚掩 (43.91s ~ 47.85s) ----
# 44.37s『鍵』『壊』及中文『钥匙』『残损』斜对角咔嚓断裂错位 + 45.46s『蓋のままで』落下暗金盒盖压梁
layers.append(BrokenKeyFracture(
    jp_layers[7], cn_layers[7],
    jp_break=(0, 2), cn_break=(0, 1, 4, 5),
    t_break=44.37, lid_span=(6, 10), t_lid=45.46,
))

# ---- [L08] 無理に押さえつけた / 却仍强行将它死死按住 (47.85s ~ 51.23s) ----
# 49.05s 唱响『押さえつけた』时字面受重压下沉微颤 + 墨绿/暗红双色带刺铁丝横贯勒紧
layers.append(RestraintPress(jp_layers[8], cn_layers[8], t_press=49.05))
layers.append(RosePetals(jp_layers[8], count=6, seed=88, color=(188, 22, 46)))

# ---- [L09] 歪んだままで / 任其扭曲不堪 (51.23s ~ 53.19s -> 53.65s) ----
# 扭曲错位斜切构图 + 咬合 4 次黑白鼓点频闪红青色散冲击 + 53.08s 玻璃花瓣碎裂炸入副歌!
layers.append(WarpedStrobeShatter(
    LINES[9], jp_layers[9], cn_layers[9],
    font_jp_path=C.FONT_PATH_JP, font_cn_path=C.FONT_PATH_CN,
))

# =====================================================================
#  副歌高潮 (L10 ~ L17, 53.19s ~ 76.93s) & 片尾彩蛋 (94.83s ~ 96.50s)
# =====================================================================

# ---- [L10] 見忘れている / 明明早已忘却它的模样 (53.19s ~ 55.60s) ----
# 53.333s 巨型红玫瑰炸裂绯红光环 + 漫天景深花瓣 + 54.67s 落泪特写冰晶水波纹
layers.append(ChorusBurstTear(jp_layers[10], cn_layers[10], t_burst=53.458, t_tear=54.833))
layers.append(RosePetals(jp_layers[10], count=9, seed=1010, color=(212, 26, 56)))
layers.append(RosePetals(cn_layers[10], count=6, seed=1011, color=(202, 28, 56)))

# ---- [L11] 夢はそこにあるはず / 梦却定然仍在此处 (55.60s ~ 57.90s) ----
# 『夢/梦』左上银白新月微弧 + 流光紫粉丝带沿字底蜿蜒穿行
layers.append(MoonRibbonTrail(jp_layers[11], cn_layers[11]))

# ---- [L12] 夢とお別れする夢を / 那场与梦道别的梦 (57.90s ~ 60.81s) ----
# 59.833s 漫天紫粉荧光蝶爆发霓虹柔光接管 + 双『夢/梦』振翅发光小蝶飞升道别
layers.append(ButterflyDreamFarewell(
    jp_layers[12], cn_layers[12], font_jp=fJP, font_cn=fCN,
    t_swarm=59.958, jp_dream_idx=(0, 7), cn_dream_idx=(3, 7),
))

# ---- [L13 ~ L14] 貴方の檻から -> 見える景色の先を (60.81s ~ 65.34s 双句联动) ----
# L13『檻/牢笼』落下暗金笼栏 -> L14『景色の先を/风景的彼方』笼栏向左右敞开化光消融
layers.append(CageBarsOpen(
    jp_layers[13], cn_layers[13], jp_layers[14], cn_layers[14],
    t_bars_in=61.40, t_bars_open=64.10,
))
layers.append(RosePetals(jp_layers[13], count=7, seed=1313, color=(204, 28, 58)))

# ---- [L15] 見てほしいのと願うだけ / 唯愿你能亲眼望见 (65.34s ~ 68.63s) ----
# 66.6s 星空纯白逆光深海蓝护盾背板 + 67.40s『願/愿』暖金十字祈愿星涟漪
layers.append(WishStarlightAura(
    jp_layers[15], cn_layers[15], font_jp=fJP,
    jp_wish_idx=7, cn_wish_idx=1, t_wish=67.40,
))

# ---- [L16] 壊れた鍵は直してあるからね / 残损的钥匙 我已为你修好 (68.63s ~ 73.39s) ----
# 回收 B 段 L07 伏笔! 断裂的『壊』『鍵』与右下角『残损』『钥匙』在 69.80s 金钥匙特写暖金扫光中无缝焊合修复!
layers.append(KeyRepairSweep(
    jp_layers[16], cn_layers[16], font_jp=fJP, font_cn=fCN,
    jp_break=(0, 3), cn_break=(0, 1, 3, 4),
    t_sweep_start=69.958, sweep_dur=1.35,
))

# ---- [L17] ドアノブに手を伸ばして / 向着门扉握把 伸出手吧 (73.39s ~ 76.93s) ----
# 73.80s 红宝石金戒六芒十字星闪 + 75.18s『手を伸ばして / 伸出手吧』字距向光舒展延伸
layers.append(RubyRingReach(
    jp_layers[17], cn_layers[17], font_jp=fJP, font_cn=fCN,
    t_glint=73.958, t_reach=75.18,
))

# ---- [Outro] 88.167s ~ 98.854s 片尾全 7 处画面内嵌文字原生级视觉同化翻译 ----
layers.append(OutroRedactedCards(font_cn_path=C.FONT_PATH_CN))

# =====================================================================
#  图层排序
# =====================================================================
layers.sort(key=lambda l: l.z)

# =====================================================================
#  主循环
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
    if fi % 120 == 0:
        print(f"frame {fi}/{N}  t={t:.1f}s", file=sys.stderr)

print("overlay done", file=sys.stderr)
