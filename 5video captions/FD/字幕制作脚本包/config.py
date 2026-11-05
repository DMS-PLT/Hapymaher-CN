# -*- coding: utf-8 -*-
"""ハピメア FD (-Fragmentation Dream-) OP《幻想楼閣》特效字幕全局配置。"""
import os

# ---- 视频参数 ----
W, H = 1920, 1080
FPS = 24
BASE_VIDEO = "../op.mkv"
ASS_FILE = "../FDop.ass"
DUR = 131.962

# ---- 同族配对金文字体 (华康金文体 W5 日文 + 华康金文体简体 W3 微增重) ----
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

FONT_SIZE_JP = 45
FONT_SIZE_CN = 42
CN_SYNTH_BOLD = 1                  # 2x 超采样下 1px 描边增重 (=0.5px), 对齐日文 W5 视觉字重

# ---- 基础安全边距 ----
MARGIN_X = 88
TOP_Y = 52
BOT_Y = 944

CHAR_SPACING_JP = 3
CHAR_SPACING_CN = 3
SPACE_ADV_RATIO = 0.48             # 句中气口留白宽度比例

# ---- 入场与退场动态参数 ----
SYL_FADE = 0.17
CN_CHAR_STEP = 0.025
CN_SLIDE_X = 14.0
LINE_FADE = 0.34
RISE = 9.5
FADE_OUT = 0.40

# =====================================================================
#  昼夜双极哥特配色体系 (FD 独有: 纯白瓷茶会绯红墨 vs 暗夜荆棘象牙白)
# =====================================================================
# 1) 暗夜/中调场景主题 ("night"): 珍珠象牙白 -> 淡蔷薇光泽 + 深酒红描边与玫瑰辉光
NIGHT_THEME = dict(
    jp_top=(255, 253, 252),
    jp_bot=(238, 222, 234),
    cn_top=(254, 250, 252),
    cn_bot=(234, 218, 230),
    outline_col=(28, 10, 18),
    outline_w=2.4,
    shadow_col=(10, 3, 8),
    shadow_alpha=0.70,
    glow_jp=(168, 28, 62),
    glow_cn=(154, 32, 68),
    active_glow=(255, 112, 148),
)

# 2) 纯白茶会场景主题 ("crimson"): 对齐原片角色名牌『鳥海有子/蓮乃咲』的深绯红酒字芯 + 瓷白净边 (零黑边脏感!)
CRIMSON_THEME = dict(
    jp_top=(198, 22, 46),
    jp_bot=(136, 12, 32),
    cn_top=(192, 20, 44),
    cn_bot=(132, 12, 30),
    outline_col=(255, 250, 252),
    outline_w=2.2,
    shadow_col=(188, 68, 88),
    shadow_alpha=0.34,
    glow_jp=(242, 126, 148),
    glow_cn=(236, 122, 144),
    active_glow=(255, 42, 78),
)
