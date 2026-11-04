# -*- coding: utf-8 -*-
"""全局配置 —— 所有尺寸/帧率/字体/颜色/版式集中在这里, 改参数不用翻代码。"""
import os

# ---- 视频 ----
W, H = 1920, 1080
FPS = 24                       # opre.mkv 实测 24fps (旧脚本误写 30)
BASE_VIDEO = "../opre.mkv"     # 渲染基底 (无字幕源)
DUR = 103.0                    # opre.mkv 实测时长 (秒); 实际按基底自动裁剪

# ---- 字体 ----
# 日文优先用华康金文体 W5 (与原片角色卡/片尾原生字体同系, 日文零缺字)
# 中文优先用华康金文体简体 W3 (同族配对, 简体零缺字, 渲染时自动微增字重对齐 W5)
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_JP_CANDIDATES = [
    "../../字体/DFKinBun-W5.ttc",
    "../../DFKinBun-W5.ttc",
    "../../TW-Kai-98_1.ttf",
    "/root/fonts/TW-Kai.ttf",
]
_FONT_CN_CANDIDATES = [
    "../../字体/DFJinWenW3-GB.ttf",
    "../../DFJinWenW3-GB.ttf",
    "../../TW-Kai-98_1.ttf",
    "/root/fonts/TW-Kai.ttf",
]
def _resolve(cands):
    for p in cands:
        ap = p if os.path.isabs(p) else os.path.normpath(os.path.join(_HERE, p))
        if os.path.exists(ap):
            return ap
    raise FileNotFoundError(f"找不到字体, 候选: {cands}")

FONT_PATH_JP = _resolve(_FONT_JP_CANDIDATES)
FONT_PATH_CN = _resolve(_FONT_CN_CANDIDATES)
FONT_PATH = FONT_PATH_JP           # 兼容旧引用
FONT_SIZE_JP = 46
FONT_SIZE_CN = 44
CN_SYNTH_BOLD = 1                  # 2x超采样下 1px 描边增重 (=0.5px), 对齐日文 W5 字重

# ---- 版式 ----
# 左下角 y=972..1050 在 L00/L04 有原片 HAPYMAHER 水印, 上提至 y=896 完美避让且落入安全框
JP_RIGHT, JP_TOP = 1836, 58        # 日文: 右上, 右对齐
CN_LEFT, CN_BOTTOM = 96, H - 184   # 中文: 左下, 左对齐 (避开 y>972 原生角标)
CHAR_SPACING = 3                   # 日文字间距 (px)
CHAR_SPACING_CN = 3                # 中文字间距 (px)

# ---- 入场与演唱动画 ----
CHAR_DELAY = 0.045                 # 非卡拉OK行逐字入场间隔
CHAR_FADE = 0.30                   # 单字淡入时长
SYL_FADE = 0.15                    # 卡拉OK音节淡入时长
KARAOKE_LEAD = 0.26                # 日文卡拉OK单字提前浮现导前量 (秒), 在唱高光仍严守音节原拍
MIN_FULL_DWELL = 0.34              # 句末最后一字完全亮起后、开始淡出前的最短完整驻留时长 (秒)
LINE_FADE = 0.32                   # 中文滑入单字淡入时长
CN_CHAR_STEP = 0.022               # 中文逐字微错开间隔 (秒)
CN_SLIDE_X = 14.0                  # 中文入场左滑距离 (px)
RISE = 12.0                        # 日文入场上浮距离 (px)
FADE_OUT = 0.26                    # 句尾淡出时长

# ---- 颜色 ----
WHITE = (255, 251, 249)            # 日文填充 (暖象牙白)
CN_COL = (248, 241, 246)           # 中文填充 (淡樱白)
OUTLINE = (34, 16, 24)             # 深酒红黑描边
SHADOW_COL = (14, 6, 12)           # 抗亮底柔影色
GLOW_JP = (168, 28, 54)            # 日文辉光 (深绯红)
GLOW_CN = (152, 34, 62)            # 中文辉光
ACTIVE_GLOW = (255, 110, 138)      # 卡拉OK在唱音节脉冲高光
RED_FILL = (224, 42, 64)           # 石榴渗红主色
VIOLET_GLOW = (172, 52, 232)       # L04 舞亚紫炎辉光
