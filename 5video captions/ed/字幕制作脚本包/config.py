# -*- coding: utf-8 -*-
"""ハピメア ED 中日双语字幕 —— 极简版全局配置。

版式约定: 中文左下 / 日文右上 (带柔和暗衬底, 避免与原片滚动 staff 署名糊在一起)。
"""
import os

# ---- 视频参数 ----
W, H = 1920, 1080
FPS = 24
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ed/

# ---- 字体 (全片统一使用 教育部标准楷书 TW-Kai) ----
FONT_PATH = os.path.normpath(os.path.join(ROOT, "..", "TW-Kai-98_1.ttf"))
if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"找不到字体: {FONT_PATH}")

FONT_SIZE_JP = 40
FONT_SIZE_CN = 40
JP_SPACING = 1.5
CN_SPACING = 1.5

# ---- 版式: 日文右上 / 中文左下 ----
JP_RIGHT = 34          # 日文右对齐距右边距
JP_TOP = 54            # 日文顶边 Y
CN_LEFT = 34           # 中文左对齐 X
CN_BOTTOM = 62         # 中文底边距画面底部

# ---- 配色 (楷书白字 + 深墨描边 + 柔影) ----
JP_FILL_TOP = (255, 255, 253)
JP_FILL_BOT = (240, 236, 242)
CN_FILL_TOP = (255, 252, 247)
CN_FILL_BOT = (233, 226, 236)
OUTLINE_COL = (16, 12, 18)
OUTLINE_W = 2
SHADOW_ALPHA = 0
HALO_ALPHA = 0.3          # 亮底上的暗色柔光, 保证白色楷书在白云/白花背景上依然清晰
PLATE_COL = (128, 20, 29)   # 暗红衬底 (贴合ハピメア的血色基调)
PLATE_ALPHA = 90          # 衬底峰值 alpha (0~255)
PLATE_PAD_X = 11           # 只比文字宽一点点, 不做大黑板
PLATE_PAD_Y = 7
PLATE_BLUR = 10            # 边缘柔化半径, 越小衬底越"贴身"
PLATE_RADIUS = 11

# ---- 动效 ----
FADE_IN = 0.3
FADE_OUT = 0.3
RISE = -8.0

# ---- 需要处理的目标: (字幕基名, 视频相对路径) ----
TARGETS = [
    ("本体/eda", "本体/eda.mkv"),
    ("FD/eda", "FD/eda.mkv"),
    ("FD/edb", "FD/edb.mkv"),
    ("FD/edc", "FD/edc.mkv"),
    ("FD/edd", "FD/edd.mkv"),
]
OUT_SUFFIX = "_中日字幕成片.mkv"
