# -*- coding: utf-8 -*-
"""ハピメア 本体 OP《夢の無限回廊》特效字幕全局配置。"""
import os

# ---- 视频参数 ----
W, H = 1920, 1080
FPS = 24
BASE_VIDEO = "../op.mkv"
ASS_FILE = "../op.ass"
DUR = 135.628

# ---- 同族配对字体 (华康金文体 W5 日文 + 华康金文体简体 W3 微增重) ----
_HERE = os.path.dirname(os.path.abspath(__file__))

def _resolve(cands):
    for p in cands:
        ap = p if os.path.isabs(p) else os.path.normpath(os.path.join(_HERE, p))
        if os.path.exists(ap):
            return ap
    raise FileNotFoundError(f"找不到字体: {cands}")

FONT_PATH_JP = _resolve([
    "../../字体/DFKinBun-W5.ttc",
    "../../DFKinBun-W5.ttc",
])
FONT_PATH_CN = _resolve([
    "../../字体/DFJinWenW3-GB.ttf",
    "../../DFJinWenW3-GB.ttf",
])

FONT_SIZE_JP = 46
FONT_SIZE_CN = 43
CN_SYNTH_BOLD = 1                  # 2x 超采样下 1px 描边增重 (=0.5px), 对齐日文 W5 视觉字重

# ---- 基础安全版式 ----
MARGIN_X = 88                      # 左右安全边距
TOP_Y = 56                         # 顶部日文 Y 坐标
BOT_Y = 944                        # 底部中文 Y 坐标 (稳居安全框内)
B_STACK_JP_Y = 54                  # B 段左上双行并列: 日文 Y (避开底部巨幅角色名牌)
B_STACK_CN_Y = 118                 # B 段左上双行并列: 中文 Y

CHAR_SPACING_JP = 3
CHAR_SPACING_CN = 3
SPACE_ADV_RATIO = 0.52             # 半句气口空格宽度比例

# ---- 入场与原片水波烟散退场参数 ----
SYL_FADE = 0.18
CN_CHAR_STEP = 0.026
CN_SLIDE_X = 15.0
LINE_FADE = 0.36
RISE = 10.0
FADE_OUT = 0.44                    # 原生横向正弦水波纹 + 青烟蒸发退场时长

# ---- 哥特童话配色 (对齐本体名牌的珍珠白->淡蔷薇纵向光泽与深酒红描边) ----
JP_TOP_COL = (255, 253, 252)
JP_BOT_COL = (238, 224, 235)
CN_TOP_COL = (254, 250, 252)
CN_BOT_COL = (234, 218, 232)

OUTLINE_COL = (28, 12, 20)
SHADOW_COL = (10, 4, 10)
GLOW_JP = (158, 30, 64)
GLOW_CN = (146, 34, 70)
ACTIVE_GLOW = (255, 118, 152)
