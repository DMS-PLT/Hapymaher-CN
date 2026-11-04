# -*- coding: utf-8 -*-
"""FD OP A段 + B段演出层 (L03~L10, 0:33.38 ~ 1:06.42):
  - L03 WakingHollowReality : 眨眼对焦苏醒 + 『空虚な現実/空虚的现实』抽离色彩化作冷灰镂空玻璃态
  - L04+L05 WonderlandCardsLie: 纯白茶会扑克红心飞舞 + 『君がいない』半透虚影 + 『嘘をつく/编织谎言』双影错位闪烁
  - L06 BlueSwallowtailPetals: 漫天绯红花瓣与沧蓝凤蝶振翅交织
  - L07+L08 WineglassOverflowDye: 『ワイングラス/红酒杯』字芯内液态红酒摇曳斟满 + 『溢れ出て 紅く染め上げる』酒滴飞溅逐字染红!
  - L09+L10 EchoingFarewellEden: 『さよなら 繰り返して』多重回声残影 + 61.83s 昼夜反转 + 禁忌伊甸哥特荆棘缠绕与幽翠荧光!
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out, composite_alpha,
    char_sprites, char_halo, apply_rose_breeze,
)
from effects.lyric import LyricLine


def _draw_twin_divider(canvas: Image.Image, x0: float, x1: float, y_mid: float,
                       alpha_mul: float, col=(204, 38, 66)):
    """为纯白茶会双行并列版式绘制精致的哥特绯红细丝菱钻分隔线 (z=22)。"""
    w = max(48, int(x1 - x0 + 24))
    h = 24
    SS = 2
    im = Image.new("RGBA", (w * SS, h * SS), (*col, 0))
    d = ImageDraw.Draw(im)
    cy = (h // 2) * SS
    lx0, lx1 = 12 * SS, (w - 12) * SS
    mx = (w * SS) // 2
    al = int(148 * alpha_mul)
    ag = int(210 * alpha_mul)
    if al <= 3:
        return
    d.line([(lx0, cy), (mx - 10 * SS, cy)], fill=(*col, al), width=2)
    d.line([(mx + 10 * SS, cy), (lx1, cy)], fill=(*col, al), width=2)
    for cx_d, r_d in ((lx0, 3.0), (mx, 4.6), (lx1, 3.0)):
        rr = r_d * SS
        d.polygon([(cx_d, cy - rr), (cx_d + rr, cy), (cx_d, cy + rr), (cx_d - rr, cy)],
                  fill=(*col, ag))
    out = im.resize((w, h), Image.Resampling.LANCZOS)
    composite_alpha(canvas, out, x0 - 12, y_mid - h * 0.5, 1.0)


def _draw_petal(d: ImageDraw.ImageDraw, x: float, y: float, rad: float, ang: float, rgba):
    ca, sa = math.cos(ang), math.sin(ang)
    rx, ry = rad * 1.36, rad * 0.72
    d.polygon([
        (x + ca * rx, y + sa * rx),
        (x - sa * ry, y + ca * ry),
        (x - ca * rx * 0.82, y - sa * rx * 0.82),
        (x + sa * ry, y - ca * ry),
    ], fill=rgba)


def _draw_micro_bfly(d: ImageDraw.ImageDraw, cx: float, cy: float, size: float,
                     flap: float, angle: float, rgba):
    ca, sa = math.cos(angle), math.sin(angle)

    def _rot(px, py):
        return (cx + px * ca - py * sa, cy + px * sa + py * ca)

    ws = size * (0.35 + 0.65 * abs(flap))
    for sgn in (-1.0, 1.0):
        d.polygon([_rot(0, 0), _rot(sgn * ws * 1.15, -size * 0.85),
                   _rot(sgn * ws * 1.28, -size * 0.15), _rot(sgn * ws * 0.35, size * 0.12)], fill=rgba)
        d.polygon([_rot(0, size * 0.08), _rot(sgn * ws * 0.90, size * 0.22),
                   _rot(sgn * ws * 0.68, size * 0.90), _rot(sgn * ws * 0.15, size * 0.45)], fill=rgba)


# =====================================================================
#  [L03] 眨眼苏醒 + 『空虚な現実 / 空虚的现实』抽离色彩冷灰玻璃镂空 (33.38s ~ 36.84s)
# =====================================================================
class WakingHollowReality(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_hollow = 35.15    # 『空虚な現実に』起唱时刻!

        # 眨眼苏醒微动钩子
        def _blink_hook(i: int, t: float):
            dt = t - self.start
            if 0.0 <= dt <= 0.42:
                # 模拟睁眼瞬间轻微纵向舒展定位
                u = ease_out(dt / 0.42)
                return 0.0, (1.0 - u) * 5.0, 0.55 + 0.45 * u
            return 0.0, 0.0, 1.0

        jp_line.motion_hook = _blink_hook
        cn_line.motion_hook = _blink_hook

        # 预烘『空虚な現実 (idx 8..12) / 空虚的现实 (idx 6..10)』抽离色彩后的冷灰半透空壳精灵!
        self.jp_hollow = self._prep_hollow(jp_line, font_jp, range(8, 13), 0)
        self.cn_hollow = self._prep_hollow(cn_line, font_cn, range(6, 11), C.CN_SYNTH_BOLD)

    @staticmethod
    def _prep_hollow(line, font, idx_range, sb):
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, _, _, _, _, cx, cy, _ = line.chars[i]
                sh, gh = char_sprites(
                    line.text[i], font,
                    fill_top=(192, 200, 212), fill_bot=(138, 146, 162),
                    glow_col=(110, 124, 148), glow_r=7.5,
                    outline=2.2, outline_col=(26, 30, 38),
                    shadow_col=(12, 14, 20), shadow_alpha=0.55,
                    synth_bold=sb,
                )
                out[i] = (sh, gh, cx - sh.width * 0.5, cy - sh.height * 0.5)
        return out

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_hollow or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02 or self.jp.exit_progress(t) > 0.25:
            return

        w_h = ease_out(clamp01((t - self.t_hollow) / 0.48)) * fo * 0.88
        for line, h_map in ((self.jp, self.jp_hollow), (self.cn, self.cn_hollow)):
            for i, (sh, gh, hx, hy) in h_map.items():
                dx, dy, a_ch, _ = line.char_state(i, t)
                if a_ch > 0.04:
                    composite_alpha(canvas, gh, hx + dx, hy + dy, a_ch * w_h * 0.75)
                    composite_alpha(canvas, sh, hx + dx, hy + dy, a_ch * w_h)


# =====================================================================
#  [L04 + L05] 仙境扑克红心飞舞 + 『君がいない』虚影 + 『嘘をつく』双影错位 (37.44s ~ 45.10s)
# =====================================================================
class WonderlandCardsLie(Layer):
    z = 34

    def __init__(self, jp4, cn4, jp5, cn5, font_jp, font_cn):
        self.jp4, self.cn4 = jp4, cn4
        self.jp5, self.cn5 = jp5, cn5
        self.start = jp4.start
        self.end = cn5.end

        # L04『君がいない (0..4) / 你已不在 (8..11)』唱过即泛起 58% 半透追忆虚影
        def _hook4_jp(i: int, t: float):
            if i <= 4 and t >= 38.45:
                u = ease_out(clamp01((t - 38.45) / 0.45))
                return 0.0, -2.5 * u, 1.0 - 0.38 * u
            return 0.0, 0.0, 1.0

        def _hook4_cn(i: int, t: float):
            if 8 <= i <= 11 and t >= 38.65:
                u = ease_out(clamp01((t - 38.65) / 0.45))
                return 0.0, -2.5 * u, 1.0 - 0.38 * u
            return 0.0, 0.0, 1.0

        jp4.motion_hook = _hook4_jp
        cn4.motion_hook = _hook4_cn

        # L05 双行并列分隔线坐标 + 『嘘をつく (6..9) / 编织谎言 (8..11)』紫红欺瞒幻影
        self.x5_0 = min(jp5.bbox_x0, cn5.bbox_x0) + 22
        self.x5_1 = max(jp5.bbox_x1, cn5.bbox_x1) - 22
        self.y5_mid = 0.5 * (jp5.y + jp5.font.size + cn5.y) + 2

        self.jp5_lie = self._prep_lie_ghosts(jp5, font_jp, range(6, 10), 0)
        self.cn5_lie = self._prep_lie_ghosts(cn5, font_cn, range(8, 12), C.CN_SYNTH_BOLD)

        # 生成仙境微型扑克牌与红心花瓣粒子池 (呼应有子 & 彼女背景飞舞纸牌!)
        rng = random.Random(3744)
        self.cards = []
        for k in range(28):
            in_l4 = (k < 14)
            ln = (jp4 if k % 2 == 0 else cn4) if in_l4 else (jp5 if k % 2 == 0 else cn5)
            tb = rng.uniform(ln.start + 0.15, ln.end - 1.15)
            life = rng.uniform(1.05, 1.65)
            x0 = rng.uniform(ln.bbox_x0 + 28, ln.bbox_x1 - 28)
            y0 = ln.y + rng.uniform(6.0, 42.0)
            vx = rng.uniform(-26.0, 26.0)
            vy = rng.uniform(-24.0, 18.0)
            sz = rng.uniform(5.5, 8.2)
            rot0 = rng.uniform(0.0, math.tau)
            vrot = rng.uniform(-3.6, 3.6)
            kind = k % 3  # 0: 扑克牌片, 1: 红心 ♥, 2: 绯红小花瓣
            self.cards.append((tb, life, x0, y0, vx, vy, sz, rot0, vrot, kind))

    @staticmethod
    def _prep_lie_ghosts(line, font, idx_range, sb):
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, _, _, _, _, cx, cy, _ = line.chars[i]
                sg, _ = char_sprites(
                    line.text[i], font,
                    fill_top=(182, 36, 156), fill_bot=(136, 20, 118),
                    glow_col=(220, 96, 198), glow_r=6.0,
                    outline=1.4, outline_col=(255, 245, 252),
                    shadow_alpha=0.0, synth_bold=sb,
                )
                out[i] = (sg, cx - sg.width * 0.5, cy - sg.height * 0.5)
        return out

    @staticmethod
    def _draw_heart(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, rgba):
        pts = []
        for k in range(18):
            th = k * (math.tau / 18.0)
            px = r * (math.sin(th) ** 3)
            py = -r * (0.81 * math.cos(th) - 0.31 * math.cos(2 * th) - 0.12 * math.cos(3 * th))
            pts.append((cx + px, cy + py))
        d.polygon(pts, fill=rgba)

    def draw_under(self, canvas: Image.Image, t: float):
        if self.jp5.is_active(t):
            fo5 = 1.0 - ease_in_out(self.jp5.exit_progress(t))
            a_in5 = ease_out(clamp01((t - self.jp5.start) / 0.42))
            _draw_twin_divider(canvas, self.x5_0, self.x5_1, self.y5_mid, a_in5 * fo5)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return

        # 1) L05『嘘をつく (43.25s+) / 编织谎言』双影错位闪烁!
        if self.jp5.is_active(t) and t >= 43.22 and self.jp5.exit_progress(t) < 0.25:
            fo5 = 1.0 - ease_in_out(self.jp5.exit_progress(t))
            dt_l = t - 43.22
            # 两次诡谲错位脉冲 + 持续微颤双影
            shimmer = 0.45 + 0.55 * abs(math.sin(dt_l * 9.5)) * math.exp(-dt_l * 0.65)
            shift_x = 6.2 * math.sin(dt_l * 13.0) * math.exp(-dt_l * 0.45) + 3.2
            for line, l_map in ((self.jp5, self.jp5_lie), (self.cn5, self.cn5_lie)):
                for i, (sg, gx, gy) in l_map.items():
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.05:
                        composite_alpha(canvas, sg, gx + dx + shift_x, gy + dy - 2.2, a_ch * 0.46 * shimmer * fo5)
                        composite_alpha(canvas, sg, gx + dx - shift_x * 0.7, gy + dy + 2.0, a_ch * 0.34 * shimmer * fo5)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

        # 2) 仙境扑克小牌片与红心粒子
        im = Image.new("RGBA", (canvas.width, canvas.height), (212, 34, 68, 0))
        d = ImageDraw.Draw(im)
        has_c = False
        for tb, life, x0, y0, vx, vy, sz, rot0, vrot, kind in self.cards:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                ca_a = math.sin(math.pi * u) * 0.85
                if ca_a <= 0.03:
                    continue
                has_c = True
                px = x0 + vx * age + 5.0 * math.sin(age * 4.5 + rot0)
                py = y0 + vy * age
                ang = rot0 + vrot * age
                if kind == 0:
                    # 微型斜旋扑克牌 (白底绯红框 + 中心红菱点)
                    cs, sn = math.cos(ang), math.sin(ang)
                    rw, rh = sz * 0.82 * max(0.35, abs(math.cos(age * 3.2))), sz * 1.15
                    corners = [
                        (px - rw * cs + rh * sn, py - rw * sn - rh * cs),
                        (px + rw * cs + rh * sn, py + rw * sn - rh * cs),
                        (px + rw * cs - rh * sn, py + rw * sn + rh * cs),
                        (px - rw * cs - rh * sn, py - rw * sn + rh * cs),
                    ]
                    d.polygon(corners, fill=(255, 250, 252, int(235 * ca_a)),
                              outline=(204, 28, 58, int(225 * ca_a)))
                    pr = sz * 0.32
                    d.polygon([(px, py - pr), (px + pr * 0.8, py), (px, py + pr), (px - pr * 0.8, py)],
                              fill=(214, 24, 54, int(235 * ca_a)))
                elif kind == 1:
                    self._draw_heart(d, px, py, sz * 0.92, (218, 28, 62, int(218 * ca_a)))
                else:
                    _draw_petal(d, px, py, sz * 0.78, ang, (212, 32, 64, int(210 * ca_a)))
        if has_c:
            canvas.alpha_composite(im)


# =====================================================================
#  [L06] 漫天绯红花瓣雨与 0:47 沧蓝凤蝶交织 (45.40s ~ 48.05s)
# =====================================================================
class BlueSwallowtailPetals(Layer):
    z = 34

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end

        rng = random.Random(4540)
        self.items = []
        for k in range(24):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(self.start + 0.05, self.end - 0.85)
            life = rng.uniform(0.90, 1.45)
            x0 = rng.uniform(ln.bbox_x0 + 24, ln.bbox_x1 - 24)
            y0 = ln.y + rng.uniform(6.0, 40.0)
            is_bfly = (k % 3 == 0) and (tb >= 45.95)
            vx = rng.uniform(-24.0, 28.0)
            vy = rng.uniform(-26.0, -8.0) if is_bfly else rng.uniform(14.0, 38.0)
            sz = rng.uniform(6.0, 8.8) if is_bfly else rng.uniform(4.4, 7.2)
            ph = rng.uniform(0.0, math.tau)
            self.items.append((tb, life, x0, y0, vx, vy, is_bfly, sz, ph))

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        im = Image.new("RGBA", (canvas.width, canvas.height), (48, 152, 238, 0))
        d = ImageDraw.Draw(im)
        has_i = False
        for tb, life, x0, y0, vx, vy, is_bfly, sz, ph in self.items:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                al = math.sin(math.pi * u) * fo
                if al <= 0.03:
                    continue
                has_i = True
                px = x0 + vx * age + 5.5 * math.sin(age * 4.8 + ph)
                py = y0 + vy * age
                if is_bfly:
                    _draw_micro_bfly(d, px, py, sz, math.sin(t * 16.5 + ph),
                                     -0.25 + 0.2 * math.cos(age * 3.0), (24, 148, 236, int(228 * al)))
                else:
                    _draw_petal(d, px, py, sz, ph + age * 3.6, (218, 28, 58, int(218 * al)))
        if has_i:
            canvas.alpha_composite(im)


# =====================================================================
#  [L07 + L08] 『ワイングラス/红酒杯』字芯液态红酒摇曳斟满 + 『溢れ出て 紅く染め上げる』满溢染红!
# =====================================================================
class WineglassOverflowDye(Layer):
    z = 35

    def __init__(self, jp7, cn7, jp8, cn8, font_jp, font_cn):
        self.jp7, self.cn7 = jp7, cn7
        self.jp8, self.cn8 = jp8, cn8
        self.start = jp7.start
        self.end = cn8.end

        # 双行并列分隔线参数
        self.x7_0 = min(jp7.bbox_x0, cn7.bbox_x0) + 22
        self.x7_1 = max(jp7.bbox_x1, cn7.bbox_x1) - 22
        self.y7_mid = 0.5 * (jp7.y + jp7.font.size + cn7.y) + 2

        self.x8_0 = min(jp8.bbox_x0, cn8.bbox_x0) + 22
        self.x8_1 = max(jp8.bbox_x1, cn8.bbox_x1) - 22
        self.y8_mid = 0.5 * (jp8.y + jp8.font.size + cn8.y) + 2

        # ---- L07: 接管整行渲染! 『ワイングラス (idx 9..14) / 红酒杯 (idx 7..9)』单遍无重影实时荡漾注酒! ----
        jp7.suppress_spans.append((jp7.start - 0.05, jp7.end + 0.05))
        cn7.suppress_spans.append((cn7.start - 0.05, cn7.end + 0.05))
        self.jp7_glass = self._prep_wine_pair(jp7, font_jp, range(9, 15), 0)
        self.cn7_glass = self._prep_wine_pair(cn7, font_cn, range(7, 10), C.CN_SYNTH_BOLD)

        # ---- L08: 接管整行渲染! 从初态浅褐玫瑰墨 -> 54.35s『紅く染め上げる』逐字满溢浸染为艳丽深绯红! ----
        jp8.suppress_spans.append((jp8.start - 0.05, jp8.end + 0.05))
        cn8.suppress_spans.append((cn8.start - 0.05, cn8.end + 0.05))

        self.jp8_pale = self._build_pale_chars(jp8, font_jp, 0)
        self.cn8_pale = self._build_pale_chars(cn8, font_cn, C.CN_SYNTH_BOLD)
        self.jp8_vivid = self._build_vivid_wine_chars(jp8, font_jp, True, 0)
        self.cn8_vivid = self._build_vivid_wine_chars(cn8, font_cn, False, C.CN_SYNTH_BOLD)

        # 53.15s~55.80s 飞溅满溢的红酒液滴池
        rng = random.Random(5290)
        self.drops = []
        for k in range(30):
            ln = jp8 if (k % 2 == 0) else cn8
            tb = rng.uniform(53.05, 55.25)
            life = rng.uniform(0.65, 1.15)
            x0 = rng.uniform(ln.bbox_x0 + 28, ln.bbox_x1 - 28)
            y0 = ln.y + rng.uniform(12.0, 38.0)
            vx = rng.uniform(-22.0, 26.0)
            vy = rng.uniform(-26.0, 8.0)
            rad = rng.uniform(2.4, 4.8)
            self.drops.append((tb, life, x0, y0, vx, vy, rad))

    @staticmethod
    def _prep_wine_pair(line, font, idx_range, sb):
        """返回 {idx: (empty_np, wine_np, glow_im, halo_im, px, py)} 用于单遍实时绘制字芯液面波浪!"""
        th = C.CRIMSON_THEME
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, g_orig, h_orig, px, py, cx, cy, _ = line.chars[i]
                # 空杯水晶态: 与整句完全一致的瓷白净边 + 晶莹香槟浅玫粉杯腔!
                s_emp, _ = char_sprites(
                    line.text[i], font,
                    fill_top=(238, 178, 192), fill_bot=(218, 146, 164),
                    glow_col=th["glow_cn" if line.is_cn else "glow_jp"], glow_r=8.8,
                    outline=th["outline_w"], outline_col=th["outline_col"],
                    shadow_col=th["shadow_col"], shadow_alpha=th["shadow_alpha"],
                    synth_bold=sb,
                )
                # 醇厚红酒态: 同款瓷白净边内盛满深邃勃艮第红酒液!
                s_win, _ = char_sprites(
                    line.text[i], font,
                    fill_top=(206, 6, 30), fill_bot=(108, 2, 16),
                    glow_col=th["glow_cn" if line.is_cn else "glow_jp"], glow_r=8.8,
                    outline=th["outline_w"], outline_col=th["outline_col"],
                    shadow_col=th["shadow_col"], shadow_alpha=th["shadow_alpha"],
                    synth_bold=sb,
                )
                out[i] = (
                    np.array(s_emp, dtype=np.float32),
                    np.array(s_win, dtype=np.float32),
                    g_orig,
                    h_orig,
                    cx - s_emp.width * 0.5,
                    cy - s_emp.height * 0.5,
                )
        return out

    @staticmethod
    def _build_pale_chars(line, font, sb):
        return LyricLine._build_chars(
            line.text, font, line.anchor_x, line.y, line.align, line.spacing,
            fill_top=(148, 92, 102), fill_bot=(112, 62, 72),
            glow_col=(222, 176, 184), outline_w=2.2, outline_col=(255, 250, 252),
            shadow_col=(168, 118, 126), shadow_alpha=0.28,
            active_col=(228, 82, 108), make_halo=(line.mode == "karaoke"), synth_bold=sb,
        )

    @staticmethod
    def _build_vivid_wine_chars(line, font, make_halo, sb):
        return LyricLine._build_chars(
            line.text, font, line.anchor_x, line.y, line.align, line.spacing,
            fill_top=(222, 6, 32), fill_bot=(126, 2, 18),
            glow_col=(255, 48, 78), outline_w=2.3, outline_col=(255, 248, 250),
            shadow_col=(176, 16, 40), shadow_alpha=0.42,
            active_col=(255, 24, 58), make_halo=make_halo, synth_bold=sb,
        )

    def _render_l7_line(self, dst: Image.Image, line, w_map, t: float, ox: int, oy: int):
        """单遍无重影渲染 L07 整句, 其中『ワイングラス / 红酒杯』字芯内实时荡漾上升红酒液面!"""
        u_fill = ease_in_out(clamp01((t - 50.82) / 1.18))
        # 第一遍: 辉光与在唱高光
        for i, (s, g, h_im, px, py, _, _, is_sp) in enumerate(line.chars):
            if is_sp:
                continue
            dx, dy, a, pulse = line.char_state(i, t)
            if a <= 0.004:
                continue
            composite_alpha(dst, g, px + dx - ox, py + dy - oy, a)
            if h_im is not None and pulse > 0.01:
                composite_alpha(dst, h_im, px + dx - ox, py + dy - oy, a * pulse * 0.90)

        # 第二遍: 字芯 (普通字直接绘制, 红酒杯字实时合成正弦荡漾红酒液面)
        for i, (s, _, _, px, py, _, _, is_sp) in enumerate(line.chars):
            if is_sp:
                continue
            dx, dy, a, _ = line.char_state(i, t)
            if a <= 0.004:
                continue
            if i not in w_map:
                composite_alpha(dst, s, px + dx - ox, py + dy - oy, a)
            else:
                emp_np, win_np, _, _, wx, wy = w_map[i]
                gh, gw, _ = emp_np.shape
                xs = np.arange(gw, dtype=np.float32)
                y_bot, y_top = gh * 0.76, gh * 0.24
                base_y = y_bot - (y_bot - y_top) * u_fill
                slosh = (2.6 * (1.0 - 0.30 * u_fill)) * np.sin(xs * 0.24 - t * 9.5 + i * 0.9)
                meniscus = (base_y + slosh)[None, :]
                ys = np.arange(gh, dtype=np.float32)[:, None]
                in_wine = np.clip((ys - meniscus + 1.0) / 1.8, 0.0, 1.0)[..., None]
                mixed = emp_np * (1.0 - in_wine) + win_np * in_wine
                sp = Image.fromarray(mixed.astype(np.uint8))
                composite_alpha(dst, sp, wx + dx - ox, wy + dy - oy, a)

    def _render_l8_dyed_line(self, dst: Image.Image, line, pale_chars, vivid_chars, t: float, ox: int, oy: int):
        """52.90s~56.33s: 红酒满溢波前从左向右将每字由浅褐玫瑰墨浸染为鲜艳宝石绯红!"""
        n = max(1, len(pale_chars))
        # 53.85s (『紅く染め上げる』前拍) 启动满溢浸染波, 55.15s 全句染透!
        wave_pos = ((t - 53.75) / 1.35) * (n + 2)

        # 第一遍: 辉光
        for i in range(n):
            sp_p, gl_p, hl_p, px, py, _, _, is_sp = pale_chars[i]
            if is_sp:
                continue
            sp_v, gl_v, hl_v, _, _, _, _, _ = vivid_chars[i]
            dx, dy, a, pulse = line.char_state(i, t)
            if a <= 0.005:
                continue
            u_dye = ease_in_out(clamp01((wave_pos - i) / 2.2))
            if u_dye < 0.995:
                composite_alpha(dst, gl_p, px + dx - ox, py + dy - oy, a * (1.0 - u_dye))
            if u_dye > 0.005:
                composite_alpha(dst, gl_v, px + dx - ox, py + dy - oy, a * u_dye)
            hl = hl_v if u_dye > 0.5 else hl_p
            if hl is not None and pulse > 0.01:
                composite_alpha(dst, hl, px + dx - ox, py + dy - oy, a * pulse * 0.90)

        # 第二遍: 字芯平滑浸染
        for i in range(n):
            sp_p, _, _, px, py, _, _, is_sp = pale_chars[i]
            if is_sp:
                continue
            sp_v, _, _, _, _, _, _, _ = vivid_chars[i]
            dx, dy, a, _ = line.char_state(i, t)
            if a <= 0.005:
                continue
            u_dye = ease_in_out(clamp01((wave_pos - i) / 2.2))
            if u_dye < 0.995:
                composite_alpha(dst, sp_p, px + dx - ox, py + dy - oy, a * (1.0 - u_dye))
            if u_dye > 0.005:
                composite_alpha(dst, sp_v, px + dx - ox, py + dy - oy, a * u_dye)

    def draw_under(self, canvas: Image.Image, t: float):
        if self.jp7.start <= t <= self.jp7.end:
            fo7 = 1.0 - ease_in_out(self.jp7.exit_progress(t))
            _draw_twin_divider(canvas, self.x7_0, self.x7_1, self.y7_mid,
                               ease_out(clamp01((t - self.jp7.start) / 0.40)) * fo7)
        if self.jp8.start <= t <= self.jp8.end:
            fo8 = 1.0 - ease_in_out(self.jp8.exit_progress(t))
            _draw_twin_divider(canvas, self.x8_0, self.x8_1, self.y8_mid,
                               ease_out(clamp01((t - self.jp8.start) / 0.40)) * fo8, col=(224, 18, 48))

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return

        # 1) L07 区间: 单遍高清渲染『優しさで満たした ワイングラス / 以温柔斟满的 红酒杯』及退场波纹
        if self.jp7.start <= t <= self.jp7.end:
            u_ex7 = self.jp7.exit_progress(t)
            if u_ex7 <= 0.005:
                self._render_l7_line(canvas, self.jp7, self.jp7_glass, t, 0, 0)
                self._render_l7_line(canvas, self.cn7, self.cn7_glass, t, 0, 0)
            else:
                for line, w_map in ((self.jp7, self.jp7_glass), (self.cn7, self.cn7_glass)):
                    bx0 = max(0, line.bbox_x0 - 24)
                    by0 = max(0, line.bbox_y0 - 16)
                    bx1 = min(canvas.width, line.bbox_x1 + 24)
                    by1 = min(canvas.height, line.bbox_y1 + 16)
                    st = Image.new("RGBA", (bx1 - bx0, by1 - by0), (198, 22, 46, 0))
                    self._render_l7_line(st, line, w_map, t, bx0, by0)
                    warped = apply_rose_breeze(st, u_ex7, phase_seed=line.start * 2.9, dir_x=-1.0)
                    composite_alpha(canvas, warped, bx0, by0 - 5.5 * (u_ex7 ** 1.3), 1.0)

        # 2) L08 区间: 渲染红酒满溢逐字染红 + 飞溅酒珠
        if self.jp8.start <= t <= self.jp8.end:
            u_ex = self.jp8.exit_progress(t)
            fo8 = 1.0 - ease_in_out(u_ex)
            if u_ex <= 0.005:
                self._render_l8_dyed_line(canvas, self.jp8, self.jp8_pale, self.jp8_vivid, t, 0, 0)
                self._render_l8_dyed_line(canvas, self.cn8, self.cn8_pale, self.cn8_vivid, t, 0, 0)
            else:
                for line, pc, vc in ((self.jp8, self.jp8_pale, self.jp8_vivid),
                                     (self.cn8, self.cn8_pale, self.cn8_vivid)):
                    bx0 = max(0, line.bbox_x0 - 24)
                    by0 = max(0, line.bbox_y0 - 16)
                    bx1 = min(canvas.width, line.bbox_x1 + 24)
                    by1 = min(canvas.height, line.bbox_y1 + 16)
                    st = Image.new("RGBA", (bx1 - bx0, by1 - by0), (220, 14, 40, 0))
                    self._render_l8_dyed_line(st, line, pc, vc, t, bx0, by0)
                    warped = apply_rose_breeze(st, u_ex, phase_seed=line.start * 2.7, dir_x=1.0)
                    composite_alpha(canvas, warped, bx0, by0 - 5.0 * u_ex, 1.0)

            # 飞溅并受重力下坠的红酒液滴
            d_im = Image.new("RGBA", (canvas.width, canvas.height), (218, 12, 38, 0))
            dd = ImageDraw.Draw(d_im)
            has_d = False
            for tb, life, x0, y0, vx, vy, rad in self.drops:
                age = t - tb
                if 0.0 <= age <= life:
                    u = age / life
                    da = math.sin(math.pi * (u ** 0.72)) * fo8
                    if da > 0.03:
                        has_d = True
                        px = x0 + vx * age
                        py = y0 + vy * age + 48.0 * (age ** 2)
                        dd.ellipse([px - rad, py - rad * 1.25, px + rad, py + rad * 1.25],
                                   fill=(222, 10, 36, int(225 * da)))
                        # 液滴晶莹高光点
                        hr = rad * 0.35
                        dd.ellipse([px - rad * 0.3 - hr, py - rad * 0.35 - hr,
                                    px - rad * 0.3 + hr, py - rad * 0.35 + hr],
                                   fill=(255, 228, 234, int(210 * da)))
            if has_d:
                canvas.alpha_composite(d_im)


# =====================================================================
#  [L09 + L10] 『さよなら 繰り返して』回声重影 + 61.83s 昼夜极性反转 + 禁忌伊甸哥特荆棘缠绕!
# =====================================================================
class EchoingFarewellEden(Layer):
    z = 36

    def __init__(self, jp9, cn9, jp10, cn10, font_jp, font_cn):
        self.jp9, self.cn9 = jp9, cn9
        self.jp10, self.cn10 = jp10, cn10
        self.start = jp9.start
        self.end = jp10.end
        self.t_flip = 62.667     # 修正时间轴：对应旧版 61.83s 的同一视频帧
        self.t_grimoire = 65.250 # 原片切入幽翠荧光荆棘魔导书特写!

        # L09 双行并列分隔线
        self.x9_0 = min(jp9.bbox_x0, cn9.bbox_x0) + 22
        self.x9_1 = max(jp9.bbox_x1, cn9.bbox_x1) - 22
        self.y9_mid = 0.5 * (jp9.y + jp9.font.size + cn9.y) + 2

        # ---- L10 昼夜双极翻转: 61.80s 后接管默认 crimson 层, 丝滑翻转为暗夜珍珠象牙白字形! ----
        jp10.suppress_spans.append((self.t_flip - 0.04, jp10.end + 0.05))
        cn10.suppress_spans.append((self.t_flip - 0.04, cn10.end + 0.05))

        nt = C.NIGHT_THEME
        self.jp10_night = LyricLine._build_chars(
            jp10.text, font_jp, jp10.anchor_x, jp10.y, jp10.align, jp10.spacing,
            nt["jp_top"], nt["jp_bot"], nt["glow_jp"], nt["outline_w"], nt["outline_col"],
            nt["shadow_col"], nt["shadow_alpha"], nt["active_glow"], True, 0,
        )
        self.cn10_night = LyricLine._build_chars(
            cn10.text, font_cn, cn10.anchor_x, cn10.y, cn10.align, cn10.spacing,
            nt["cn_top"], nt["cn_bot"], nt["glow_cn"], nt["outline_w"], nt["outline_col"],
            nt["shadow_col"], nt["shadow_alpha"], nt["active_glow"], False, C.CN_SYNTH_BOLD,
        )

        # 64.40s 幽翠禁忌伊甸魔导书荧光粒子
        rng = random.Random(6090)
        self.eden_sparks = []
        for k in range(22):
            ln = jp10 if (k % 2 == 0) else cn10
            tb = rng.uniform(62.40, 65.45)
            life = rng.uniform(0.95, 1.55)
            x0 = rng.uniform(ln.bbox_x0 + 28, ln.bbox_x1 - 28)
            y0 = ln.y + rng.uniform(6.0, 42.0)
            vx = rng.uniform(-16.0, 16.0)
            vy = rng.uniform(-24.0, -8.0)
            rad = rng.uniform(2.0, 3.8)
            is_cyan = (tb >= 65.000) or (k % 3 == 0)
            self.eden_sparks.append((tb, life, x0, y0, vx, vy, rad, is_cyan))

    @staticmethod
    def _draw_thorny_vine(canvas: Image.Image, line, progress: float, alpha_mul: float, emerald_glow: float):
        """2x 超采样在字行背后生长带弯钩尖刺的哥特黑红荆棘藤蔓 (z=22, 61.95s~66.2s)!"""
        if progress <= 0.02 or alpha_mul <= 0.02:
            return
        x0 = line.bbox_x0 + 18
        x1 = line.bbox_x1 - 18
        w = max(60, int(x1 - x0))
        h = 54
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (32, 8, 16, 0))
        d = ImageDraw.Draw(im)
        cy = (h * 0.5) * SS

        reach = int(w * SS * ease_out(progress))
        if reach < 12:
            return

        # 64.42s 荆棘古书切镜时泛起幽翠绿底晕 (呼应古书中央青翠光核!)
        if emerald_glow > 0.03:
            eg = Image.new("RGBA", (w * SS, h * SS), (42, 236, 188, 0))
            ed = ImageDraw.Draw(eg)
            ed.line([(10 * SS, cy), (reach, cy)], fill=(42, 236, 188, int(92 * emerald_glow * alpha_mul)), width=8)
            eg = eg.filter(ImageFilter.GaussianBlur(5.0 * SS))
            im.alpha_composite(eg)

        # 双股交缠哥特深红黑荆棘主茎 + 锐利玫瑰弯刺!
        pts1, pts2 = [], []
        step = 6 * SS
        for px in range(8 * SS, reach, step):
            u = px / max(1.0, w * SS)
            y1 = cy + 6.5 * SS * math.sin(u * math.pi * 4.2)
            y2 = cy - 5.2 * SS * math.sin(u * math.pi * 4.2 + 0.9)
            pts1.append((px, y1))
            pts2.append((px, y2))

        a_stem = int(205 * alpha_mul)
        a_hi = int(175 * alpha_mul)
        if len(pts1) >= 2:
            d.line(pts1, fill=(38, 6, 14, a_stem), width=4)
            d.line(pts1, fill=(178, 18, 44, a_hi), width=2)
            d.line(pts2, fill=(46, 8, 18, int(a_stem * 0.85)), width=3)

            # 每隔数节生长一枚锋利玫瑰荆棘弯刺
            for idx in range(1, len(pts1) - 1, 2):
                tx, ty = pts1[idx]
                sgn = 1.0 if (idx % 4 == 1) else -1.0
                tip = (tx + 5.5 * SS, ty + sgn * 8.5 * SS)
                d.polygon([
                    (tx - 2.5 * SS, ty),
                    tip,
                    (tx + 2.2 * SS, ty),
                ], fill=(196, 22, 48, a_stem))

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, x0, line.y + line.font.size * 0.56 - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if self.jp9.is_active(t):
            fo9 = 1.0 - ease_in_out(self.jp9.exit_progress(t))
            _draw_twin_divider(canvas, self.x9_0, self.x9_1, self.y9_mid,
                               ease_out(clamp01((t - self.jp9.start) / 0.40)) * fo9)

        # L10 暗夜段 (61.90s~66.35s): 哥特荆棘藤蔓从左向右蜿蜒生长!
        if self.t_flip <= t <= self.jp10.end:
            fo10 = 1.0 - ease_in_out(self.jp10.exit_progress(t))
            u_grow = clamp01((t - 62.792) / 1.65)
            em_w = math.sin(math.pi * clamp01((t - 65.167) / 1.90))
            self._draw_thorny_vine(canvas, self.jp10, u_grow, fo10, em_w)
            self._draw_thorny_vine(canvas, self.cn10, u_grow, fo10, em_w)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return

        # 1) L09: 『さよなら (idx 4..7) 繰り返して (idx 9..13)』层层荡开的回声重影!
        if self.jp9.is_active(t) and t >= 57.68 and self.jp9.exit_progress(t) < 0.20:
            fo9 = 1.0 - ease_in_out(self.jp9.exit_progress(t))
            dt_e = t - 57.68
            wave = (dt_e * 1.45) % 1.0
            echo_a = math.sin(math.pi * wave) * 0.36 * fo9
            if echo_a > 0.015:
                off = 5.0 + 13.0 * ease_out(wave)
                for line, i0 in ((self.jp9, 4), (self.cn9, 6)):
                    for i in range(i0, len(line.chars)):
                        s_core, _, _, px, py, _, _, is_sp = line.chars[i]
                        if is_sp:
                            continue
                        dx, dy, a_ch, _ = line.char_state(i, t)
                        if a_ch > 0.05:
                            composite_alpha(canvas, s_core, px + dx - off, py + dy - off * 0.28, a_ch * echo_a)
                            composite_alpha(canvas, s_core, px + dx + off * 0.65, py + dy + off * 0.22, a_ch * echo_a * 0.65)

        # 2) L10: 61.80s 起执行昼(深绯红) -> 夜(珍珠象牙白) 极性平滑翻转 + 幽翠伊甸荧光微粒!
        if self.t_flip - 0.04 <= t <= self.jp10.end:
            u_flip = ease_in_out(clamp01((t - (self.t_flip - 0.04)) / 0.18))
            u_ex = self.jp10.exit_progress(t)
            fo10 = 1.0 - ease_in_out(u_ex)

            if u_ex <= 0.005:
                if u_flip < 0.995:
                    # 渐隐白昼绯红字
                    tmp_d = Image.new("RGBA", (canvas.width, canvas.height), (198, 22, 46, 0))
                    self.jp10.render_to_buffer(tmp_d, t, 0, 0)
                    self.cn10.render_to_buffer(tmp_d, t, 0, 0)
                    composite_alpha(canvas, tmp_d, 0, 0, 1.0 - u_flip)
                if u_flip > 0.005:
                    if u_flip > 0.995:
                        self.jp10.render_to_buffer(canvas, t, 0, 0, chars_override=self.jp10_night)
                        self.cn10.render_to_buffer(canvas, t, 0, 0, chars_override=self.cn10_night)
                    else:
                        tmp_n = Image.new("RGBA", (canvas.width, canvas.height), (255, 252, 252, 0))
                        self.jp10.render_to_buffer(tmp_n, t, 0, 0, chars_override=self.jp10_night)
                        self.cn10.render_to_buffer(tmp_n, t, 0, 0, chars_override=self.cn10_night)
                        composite_alpha(canvas, tmp_n, 0, 0, u_flip)
            else:
                for line, n_chars in ((self.jp10, self.jp10_night), (self.cn10, self.cn10_night)):
                    bx0 = max(0, line.bbox_x0 - 24)
                    by0 = max(0, line.bbox_y0 - 16)
                    bx1 = min(canvas.width, line.bbox_x1 + 24)
                    by1 = min(canvas.height, line.bbox_y1 + 16)
                    st = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
                    line.render_to_buffer(st, t, bx0, by0, chars_override=n_chars)
                    warped = apply_rose_breeze(st, u_ex, phase_seed=line.start * 3.1,
                                               dir_x=(1.0 if line.align == "left" else -1.0))
                    composite_alpha(canvas, warped, bx0, by0 - 5.0 * u_ex, 1.0)

            # 禁忌伊甸幽翠与绯红星火微粒
            sp_im = Image.new("RGBA", (canvas.width, canvas.height), (72, 244, 198, 0))
            sd = ImageDraw.Draw(sp_im)
            has_s = False
            for tb, life, x0, y0, vx, vy, rad, is_cyan in self.eden_sparks:
                age = t - tb
                if 0.0 <= age <= life:
                    u = age / life
                    sa = math.sin(math.pi * u) * fo10
                    if sa > 0.03:
                        has_s = True
                        px = x0 + vx * age + 4.5 * math.sin(age * 4.5)
                        py = y0 + vy * age
                        rgb = (62, 246, 204) if is_cyan else (238, 38, 72)
                        r2 = rad * 2.0
                        sd.ellipse([px - r2, py - r2, px + r2, py + r2], fill=(*rgb, int(92 * sa)))
                        sd.ellipse([px - rad * 0.65, py - rad * 0.65, px + rad * 0.65, py + rad * 0.65],
                                   fill=(245, 255, 252, int(230 * sa)))
            if has_s:
                canvas.alpha_composite(sp_im)
