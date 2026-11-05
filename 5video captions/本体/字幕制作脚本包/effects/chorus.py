# -*- coding: utf-8 -*-
"""ハピメア 本体 OP 副歌 (L06~L11, 63.48s~109.08s) + 尾奏 2:00 猩红题记演出层:
  - L06 SpiralPrismEntry       : 黄金螺旋入场 + 双螺旋流光丝带 + 70.5s 咲棱镜彩虹色散折射
  - L07 PocketwatchMiracleMotes: 72.8s 古铜金怀表刻度秒针滴答 + 77.5s 彩窗暖金光斑与翠绿凤蝶微尘
  - L08+L09 WhiteRoseToBlueDream: 82.83s 白蔷薇爆碎绯红花瓣 + 86.46s 粉紫梦境光晕与有栖沧蓝幻蝶
  - L10 ChiaroscuroBondReach   : 暗棋盘舞台追光 + 『取り戻す/重新夺回』双向牵引红线 + 93.23s/97.94s 双人剪影花瓣爆散
  - L11 CrimsonInkBlotFinale   : 情感终章暗紫呼吸 + 106.95s~109.08s 分形猩红血墨斑块吞噬退场
  - OutroTagline (119.50s~124.88s): 原生级内嵌『这是一个甜蜜而又幸福的恶梦故事』(『梦』字放大染血 + 逐行水波卷烟蒸发)
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out, composite_alpha, char_halo,
)


class _UnderlayAdapter(Layer):
    """将演出的背景衬底元素 (柔光护盾/双螺旋丝带/怀表星盘/舞台追光/红线) 置于 z=22 (文字 z=30 正后方),
    彻底避免前景叠加压暗字芯或二次重绘导致的辉光加倍。
    """
    z = 22

    def __init__(self, owner):
        self.owner = owner

    def draw(self, canvas: Image.Image, t: float):
        self.owner.draw_under(canvas, t)


def _soft_cushion(w: int, h: int, rgb=(68, 16, 34), alpha: int = 128, blur_r: float = 18.0) -> Image.Image:
    """生成边界严格衰减至 0 的解析椭球柔光云衬底 (绝无高斯截断矩形边痕!)。"""
    pad = 44
    W, H = w + pad * 2, h + pad * 2
    yy = np.linspace(-1.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :]
    # 超椭圆平滑距离场: r >= 1.0 处严格归零, 杜绝任何白底矩形边界!
    r2 = (np.abs(xx) ** 2.4) + (np.abs(yy) ** 2.0)
    falloff = np.clip(1.0 - r2, 0.0, 1.0) ** 2.2
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[..., 0] = rgb[0]
    arr[..., 1] = rgb[1]
    arr[..., 2] = rgb[2]
    arr[..., 3] = np.clip(falloff * alpha, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(arr)


def _draw_micro_butterfly(d: ImageDraw.ImageDraw, cx: float, cy: float, size: float,
                          flap: float, angle: float, col_rgba):
    """在 2x/1x 画布上绘制展翅振频的精致双翼微缩幻蝶。"""
    ca, sa = math.cos(angle), math.sin(angle)

    def _rot(px, py):
        return (cx + px * ca - py * sa, cy + px * sa + py * ca)

    w_span = size * (0.35 + 0.65 * abs(flap))
    # 左右上翼 + 左右下翼
    for sgn in (-1.0, 1.0):
        u_pts = [
            _rot(0.0, 0.0),
            _rot(sgn * w_span * 1.15, -size * 0.85),
            _rot(sgn * w_span * 1.30, -size * 0.15),
            _rot(sgn * w_span * 0.35, size * 0.12),
        ]
        l_pts = [
            _rot(0.0, size * 0.08),
            _rot(sgn * w_span * 0.92, size * 0.22),
            _rot(sgn * w_span * 0.68, size * 0.92),
            _rot(sgn * w_span * 0.15, size * 0.45),
        ]
        d.polygon(u_pts, fill=col_rgba)
        d.polygon(l_pts, fill=col_rgba)


# =====================================================================
#  [L06] 黄金螺旋入场 + 双螺旋流光丝带 + 咲镜面棱镜彩虹色散 (63.48s ~ 72.76s)
# =====================================================================
class SpiralPrismEntry(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end

        # 63.48s~65.05s 白银蔷薇强光帧柔光护盾
        jw = jp_line.bbox_x1 - jp_line.bbox_x0 + 40
        jh = jp_line.bbox_y1 - jp_line.bbox_y0 + 24
        cw = cn_line.bbox_x1 - cn_line.bbox_x0 + 40
        ch = cn_line.bbox_y1 - cn_line.bbox_y0 + 24
        self.jp_veil = _soft_cushion(jw, jh, rgb=(112, 34, 62), alpha=46, blur_r=26.0)
        self.cn_veil = _soft_cushion(cw, ch, rgb=(112, 34, 62), alpha=46, blur_r=26.0)

        # 黄金螺旋入场 + 『螺旋』唱段微回旋钩子 (避开 63.48s~63.56s L05 纯白余晖)
        def _make_spiral_hook(is_jp: bool):
            spiral_idx = (5, 6) if is_jp else (1, 10, 11)  # JP『螺旋』/ CN『旋..螺旋』

            def _hook(i: int, t: float):
                # 63.48 -> 63.56 轻缓起势, 无缝衔接 L05 白幕消融
                gate = clamp01((t - (self.start + 0.05)) / 0.20)
                t0 = self.start + 0.06 + i * 0.036
                u = clamp01((t - t0) / 0.68)
                inv = (1.0 - ease_out(u))
                rad = 26.0 * (inv ** 1.35)
                theta = inv * 3.1 + i * 0.52 * (1.0 if is_jp else -1.0)
                dx = rad * math.cos(theta)
                dy = rad * math.sin(theta) * 0.52

                # 唱到『螺旋』(67.35s~68.90s) 时字形轻柔回旋微漾
                if i in spiral_idx and 67.32 <= t <= 69.10:
                    w_sp = math.sin(math.pi * clamp01((t - 67.32) / 1.78))
                    ang = (t - 67.32) * 5.6 + i * 1.4
                    dx += 2.6 * w_sp * math.cos(ang)
                    dy += 1.8 * w_sp * math.sin(ang)
                return dx, dy, gate

            return _hook

        jp_line.motion_hook = _make_spiral_hook(True)
        cn_line.motion_hook = _make_spiral_hook(False)

        # 预缓存 69.5s~72.5s 咲棱镜彩虹光谱条纹覆盖层 (按虹彩四色光晕预烘)
        prism_cols = [
            (96, 238, 255),   # 冰青色散
            (116, 255, 196),  # 翠玉色散
            (255, 226, 132),  # 暖金色散
            (255, 118, 214),  # 蔷薇洋红色散
        ]
        self.jp_prism = self._prep_prism_halos(jp_line, font_jp, prism_cols, 0)
        self.cn_prism = self._prep_prism_halos(cn_line, font_cn, prism_cols, C.CN_SYNTH_BOLD)

    @staticmethod
    def _prep_prism_halos(line, font, cols, sb):
        out = {}
        for i, (_, _, _, _, _, cx, cy, is_sp) in enumerate(line.chars):
            if not is_sp:
                col = cols[i % len(cols)]
                h = char_halo(line.text[i], font, halo_col=col, blur_r=8.0, synth_bold=sb)
                out[i] = (h, cx - h.width * 0.5, cy - h.height * 0.5, col)
        return out

    def _draw_double_helix(self, canvas: Image.Image, line, t: float, fo: float):
        """在字行基线后方编织一条双螺旋流光丝带 (64.6s~72.4s)。"""
        if t < 64.20:
            return
        w_in = ease_out(clamp01((t - 64.20) / 0.85)) * fo
        if w_in <= 0.02:
            return

        x0 = line.bbox_x0 + 28
        x1 = line.bbox_x1 - 28
        w = max(40, int(x1 - x0))
        h = 44
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (235, 180, 220, 0))
        d = ImageDraw.Draw(im)
        cy = (h * 0.5) * SS

        # 67.3s『螺旋』处振幅与光泽推至高潮
        surge = 1.0 + 0.35 * math.sin(math.pi * clamp01((t - 67.10) / 2.20))
        amp = 8.2 * surge * SS
        n_pts = 64
        pts_a, pts_b = [], []
        phase = -t * 3.6
        for k in range(n_pts + 1):
            u = k / n_pts
            env = math.sin(math.pi * u) ** 0.75
            px = u * w * SS
            ang = u * math.pi * 3.5 + phase
            pts_a.append((px, cy + amp * env * math.sin(ang)))
            pts_b.append((px, cy + amp * env * math.sin(ang + math.pi)))

        a1 = int(125 * w_in)
        a2 = int(105 * w_in)
        d.line(pts_a, fill=(255, 176, 208, a1), width=3)
        d.line(pts_b, fill=(192, 206, 255, a2), width=2)

        # 双螺旋交汇节点星芒
        for k in range(4, n_pts - 3, 9):
            u = k / n_pts
            px, py = pts_a[k]
            rr = 2.6 * SS
            d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(255, 245, 252, int(175 * w_in)))

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, x0, line.y + line.font.size * 0.68 - h * 0.5, 1.0)

    def _draw_prism_refraction(self, canvas: Image.Image, line, prism_map, t: float, fo: float):
        """69.45s ~ 72.55s (对应原片咲斜向玻璃棱镜彩虹色散): 掠过虹彩折射光晕与十字晶芒!"""
        if t < 69.45:
            return
        w_pr = math.sin(math.pi * clamp01((t - 69.45) / 3.05)) * fo
        if w_pr <= 0.02:
            return

        n_ch = max(1, len(line.chars))
        sweep = ((t - 69.45) / 2.65) * (n_ch + 4) - 1.5

        for i, (s_core, _, _, px_c, py_c, cx, cy, is_sp) in enumerate(line.chars):
            if is_sp or i not in prism_map:
                continue
            dx, dy, a_ch, _ = line.char_state(i, t)
            if a_ch <= 0.04:
                continue
            # 斜向棱镜光谱波包扫过每字
            band = math.exp(-0.5 * ((i - sweep) / 2.3) ** 2)
            ha = a_ch * w_pr * (0.28 + 0.62 * band)
            if ha > 0.02:
                hp, hx, hy, col = prism_map[i]
                composite_alpha(canvas, hp, hx + dx, hy + dy, ha)
                composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

                # 波峰处点缀棱镜十字折光星芒
                if band > 0.72:
                    gl_a = int(215 * w_pr * (band - 0.72) / 0.28)
                    if gl_a > 12:
                        gx, gy = cx + dx + 8, cy + dy - 12
                        st = Image.new("RGBA", (28, 28), (*col, 0))
                        sd = ImageDraw.Draw(st)
                        sd.line([(14, 2), (14, 26)], fill=(255, 255, 255, gl_a), width=2)
                        sd.line([(2, 14), (26, 14)], fill=(*col, gl_a), width=2)
                        sd.ellipse([11, 11, 17, 17], fill=(255, 255, 255, gl_a))
                        composite_alpha(canvas, st, gx - 14, gy - 14, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 1) 63.52s ~ 65.15s 白银蔷薇强光帧叠轻柔暗蔷薇护盾 (置于字形正后方 z=22)
        if t < 65.15:
            v_in = clamp01((t - 63.52) / 0.22)
            v_out = 1.0 - ease_in_out(clamp01((t - 64.72) / 0.42))
            va = v_in * v_out * fo
            if va > 0.02:
                composite_alpha(canvas, self.jp_veil, self.jp.bbox_x0 - 64, self.jp.bbox_y0 - 56, va)
                composite_alpha(canvas, self.cn_veil, self.cn.bbox_x0 - 64, self.cn.bbox_y0 - 56, va)

        # 2) 双螺旋丝带衬景 (自然穿梭于字形背后)
        self._draw_double_helix(canvas, self.jp, t, fo)
        self._draw_double_helix(canvas, self.cn, t, fo)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 3) 69.45s ~ 72.55s 咲棱镜彩虹色散折射 (前景虹彩光晕 + 棱镜十字星芒)
        if self.jp.exit_progress(t) < 0.25:
            self._draw_prism_refraction(canvas, self.jp, self.jp_prism, t, fo)
            self._draw_prism_refraction(canvas, self.cn, self.cn_prism, t, fo)


# =====================================================================
#  [L07] 古铜金怀表滴答刻度 + 彩窗暖金光斑与翠绿凤蝶微尘 (72.76s ~ 81.77s)
# =====================================================================
class PocketwatchMiracleMotes(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end

        # 预缓存『奇跡求め / 微茫的奇迹』暖金与翠玉双色神圣光晕
        self.jp_gold = self._prep_halos(jp_line, font_jp, (255, 214, 112), 0)
        self.cn_gold = self._prep_halos(cn_line, font_cn, (255, 214, 112), C.CN_SYNTH_BOLD)

        # 生成 76.7s~81.6s 彩窗金尘与翠绿凤蝶微粒 (呼应 78s 彩窗光柱 & 81.2s 翠绿凤蝶!)
        rng = random.Random(7276)
        self.motes = []
        for k in range(28):
            target_jp = (k % 2 == 0)
            ln = jp_line if target_jp else cn_line
            tb = rng.uniform(76.65, 80.55)
            life = rng.uniform(1.15, 1.95)
            # 聚焦在『奇跡求め / 微茫的奇迹』后半句区域
            x_min = ln.bbox_x0 + (ln.bbox_x1 - ln.bbox_x0) * 0.35
            x_max = ln.bbox_x1 - 24
            x0 = rng.uniform(x_min, x_max)
            y0 = ln.y + rng.uniform(8.0, 42.0)
            vx = rng.uniform(-14.0, 18.0)
            vy = rng.uniform(-34.0, -16.0)
            is_bfly = (k % 3 == 0)
            is_emerald = (k % 2 == 1) or (tb > 79.4)
            sz = rng.uniform(5.2, 7.8) if is_bfly else rng.uniform(2.2, 4.2)
            ph = rng.uniform(0.0, math.tau)
            self.motes.append((tb, life, x0, y0, vx, vy, is_bfly, is_emerald, sz, ph))

    @staticmethod
    def _prep_halos(line, font, col, sb):
        out = {}
        for i, (_, _, _, _, _, cx, cy, is_sp) in enumerate(line.chars):
            if not is_sp:
                h = char_halo(line.text[i], font, halo_col=col, blur_r=8.5, synth_bold=sb)
                out[i] = (h, cx - h.width * 0.5, cy - h.height * 0.5)
        return out

    def _draw_pocketwatch_dial(self, canvas: Image.Image, cx: float, cy: float,
                               radius: float, t: float, alpha_mul: float):
        """2x 超采样绘制古铜金西洋怀表星盘刻度弧与擒纵跳秒指针 (72.80s~75.70s)。"""
        SS = 2
        sz = int((radius + 16) * 2)
        im = Image.new("RGBA", (sz * SS, sz * SS), (242, 198, 106, 0))
        d = ImageDraw.Draw(im)
        mc = (sz * 0.5) * SS
        r_out = radius * SS
        r_in = radius * 0.80 * SS

        a_ring = int(135 * alpha_mul)
        a_tick = int(175 * alpha_mul)
        a_hand = int(215 * alpha_mul)

        # 双层古铜金纤细表圈
        d.ellipse([mc - r_out, mc - r_out, mc + r_out, mc + r_out], outline=(245, 202, 108, a_ring), width=2)
        d.ellipse([mc - r_in, mc - r_in, mc + r_in, mc + r_in], outline=(228, 178, 86, int(a_ring * 0.72)), width=2)

        # 12 枚古典刻度与四方菱钻
        for k in range(12):
            ang = k * (math.tau / 12.0) - math.pi * 0.5
            ca, sa = math.cos(ang), math.sin(ang)
            if k % 3 == 0:
                rr = 3.2 * SS
                px, py = mc + ca * (r_out - 4 * SS), mc + sa * (r_out - 4 * SS)
                d.polygon([(px, py - rr), (px + rr, py), (px, py + rr), (px - rr, py)],
                          fill=(255, 232, 162, a_tick))
            else:
                p0 = (mc + ca * (r_in + 2 * SS), mc + sa * (r_in + 2 * SS))
                p1 = (mc + ca * (r_out - 2 * SS), mc + sa * (r_out - 2 * SS))
                d.line([p0, p1], fill=(242, 198, 108, int(a_tick * 0.78)), width=2)

        # 擒纵机构跳秒指针 (每秒 4 拍微顿挫, 呼应 73.3s 摆动怀表!)
        dt = t - 72.76
        beats = dt * 4.0
        b_int = math.floor(beats)
        b_frac = beats - b_int
        step_beats = b_int + ease_out(clamp01(b_frac * 2.8))
        h_ang = -math.pi * 0.65 + step_beats * (math.tau / 24.0)
        h_ca, h_sa = math.cos(h_ang), math.sin(h_ang)
        d.line([(mc - h_ca * 7 * SS, mc - h_sa * 7 * SS),
                (mc + h_ca * (r_out - 3 * SS), mc + h_sa * (r_out - 3 * SS))],
               fill=(255, 238, 176, a_hand), width=3)
        # 分针慢走
        m_ang = -math.pi * 0.22 + dt * 0.12
        d.line([(mc, mc), (mc + math.cos(m_ang) * r_in * 0.72, mc + math.sin(m_ang) * r_in * 0.72)],
               fill=(242, 196, 106, int(a_hand * 0.80)), width=3)
        cr = 3.2 * SS
        d.ellipse([mc - cr, mc - cr, mc + cr, mc + cr], fill=(255, 246, 205, a_hand))

        out = im.resize((sz, sz), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, cx - sz * 0.5, cy - sz * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 1) 72.78s ~ 75.85s: 『祈る / 虔诚祈祷』古铜金怀表星盘衬底 (z=22)
        if t <= 75.85:
            w_in = ease_out(clamp01((t - 72.78) / 0.45))
            w_out = 1.0 - ease_in_out(clamp01((t - 74.95) / 0.90))
            wa = w_in * w_out * fo
            if wa > 0.02:
                jp_cx = 0.5 * (self.jp.chars[0][5] + self.jp.chars[1][5])
                jp_cy = self.jp.y + self.jp.font.size * 0.50
                cn_cx = 0.5 * (self.cn.chars[0][5] + self.cn.chars[3][5])
                cn_cy = self.cn.y + self.cn.font.size * 0.50
                self._draw_pocketwatch_dial(canvas, jp_cx, jp_cy, 40.0, t, wa)
                self._draw_pocketwatch_dial(canvas, cn_cx, cn_cy, 40.0, t, wa * 0.92)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 2) 76.75s ~ 81.65s: 『奇跡求め / 追寻那一丝微茫的奇迹』彩窗暖金圣光晕 + 翠绿凤蝶微尘
        if t >= 76.65 and self.jp.exit_progress(t) < 0.30:
            w_mir = ease_out(clamp01((t - 76.75) / 0.75)) * fo * 0.56
            if w_mir > 0.02:
                for line, g_map, idx_from in (
                    (self.jp, self.jp_gold, 6),   # JP『奇跡求め』
                    (self.cn, self.cn_gold, 7),   # CN『一丝微茫的奇迹』
                ):
                    for i in range(idx_from, len(line.chars)):
                        s_core, _, _, px_c, py_c, _, _, is_sp = line.chars[i]
                        if is_sp or i not in g_map:
                            continue
                        dx, dy, a_ch, _ = line.char_state(i, t)
                        if a_ch > 0.04:
                            gh, gx, gy = g_map[i]
                            composite_alpha(canvas, gh, gx + dx, gy + dy, a_ch * w_mir)
                            composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

            # 浮升的彩窗暖金光斑与翠绿凤蝶
            m_layer = Image.new("RGBA", (canvas.width, canvas.height), (120, 240, 190, 0))
            md = ImageDraw.Draw(m_layer)
            has_m = False
            for tb, life, x0, y0, vx, vy, is_bfly, is_em, sz, ph in self.motes:
                age = t - tb
                if 0.0 <= age <= life:
                    u = age / life
                    ma = math.sin(math.pi * u) * fo
                    if ma <= 0.03:
                        continue
                    has_m = True
                    px = x0 + vx * age + 6.5 * math.sin(age * 4.5 + ph)
                    py = y0 + vy * age
                    rgb = (78, 244, 188) if is_em else (255, 224, 132)
                    if is_bfly:
                        flap = math.sin(t * 16.5 + ph)
                        _draw_micro_butterfly(md, px, py, sz, flap, -0.25 + 0.2 * math.sin(age * 3.0),
                                              (*rgb, int(218 * ma)))
                    else:
                        r_out = sz * 1.8
                        md.ellipse([px - r_out, py - r_out, px + r_out, py + r_out],
                                   fill=(*rgb, int(85 * ma)))
                        md.ellipse([px - sz * 0.7, py - sz * 0.7, px + sz * 0.7, py + sz * 0.7],
                                   fill=(255, 252, 236, int(225 * ma)))
            if has_m:
                canvas.alpha_composite(m_layer)


# =====================================================================
#  [L08 + L09] 82.83s 白蔷薇碎裂绯红花瓣 -> 86.46s 粉紫梦境与沧蓝幻蝶 (81.77s ~ 90.54s)
# =====================================================================
class WhiteRoseToBlueDream(Layer):
    z = 35

    def __init__(self, jp8, cn8, jp9, cn9, font_jp, font_cn):
        self.jp8, self.cn8 = jp8, cn8
        self.jp9, self.cn9 = jp9, cn9
        self.start = jp8.start
        self.end = jp9.end
        self.t_burst = 82.83     # 原片纯白蔷薇轰然炸裂为漫天深红花瓣的精确帧!
        self.t_dream = 86.46     # 原片闪白切入粉紫梦境 + 有栖脸颊蓝蝶特写!

        # 81.80s~83.35s 纯白蔷薇高光背景轻柔氛围护航
        self.veil8_jp = _soft_cushion(jp8.bbox_x1 - jp8.bbox_x0 + 44, jp8.bbox_y1 - jp8.bbox_y0 + 28,
                                      rgb=(112, 34, 62), alpha=44, blur_r=26.0)
        self.veil8_cn = _soft_cushion(cn8.bbox_x1 - cn8.bbox_x0 + 44, cn8.bbox_y1 - cn8.bbox_y0 + 28,
                                      rgb=(112, 34, 62), alpha=44, blur_r=26.0)

        # 82.83s 花瓣爆裂瞬间的字形轻震钩子
        def _shock_hook(i: int, t: float):
            dt = t - self.t_burst
            if 0.0 <= dt <= 0.34:
                env = math.exp(-dt * 9.5)
                return (
                    3.2 * env * math.sin(dt * 48.0 + i * 1.3),
                    2.4 * env * math.cos(dt * 42.0 + i * 0.9),
                    1.0,
                )
            return 0.0, 0.0, 1.0

        jp8.motion_hook = _shock_hook
        cn8.motion_hook = _shock_hook

        # 预缓存 L09 粉紫梦境与沧蓝幻蝶双色光晕
        self.jp9_blue = PocketwatchMiracleMotes._prep_halos(jp9, font_jp, (82, 168, 255), 0)
        self.cn9_blue = PocketwatchMiracleMotes._prep_halos(cn9, font_cn, (82, 168, 255), C.CN_SYNTH_BOLD)

        # 1) 82.83s 白蔷薇碎裂深红花瓣粒子池
        rng = random.Random(8283)
        self.burst_petals = []
        for k in range(38):
            ln = jp8 if (k % 2 == 0) else cn8
            t0 = self.t_burst + rng.uniform(0.0, 0.24)
            life = rng.uniform(1.10, 2.05)
            x0 = rng.uniform(ln.bbox_x0 + 36, ln.bbox_x1 - 36)
            y0 = ln.y + rng.uniform(6.0, 40.0)
            ang_v = rng.uniform(-math.pi * 0.85, math.pi * 0.85)
            spd = rng.uniform(28.0, 88.0)
            vx = math.cos(ang_v) * spd
            vy = math.sin(ang_v) * spd * 0.55 + rng.uniform(12.0, 32.0)
            rad = rng.uniform(4.2, 8.2)
            rot0 = rng.uniform(0.0, math.tau)
            vrot = rng.uniform(-4.8, 4.8)
            col = (196, 16, 44) if (k % 3 != 0) else (238, 42, 76)
            self.burst_petals.append((t0, life, x0, y0, vx, vy, rad, rot0, vrot, col))

        # 2) 87.11s ~ 90.45s L09 沧蓝幻蝶粒子 + 89.60s 坠入暗夜的深红残瓣
        self.dream_bflies = []
        for k in range(18):
            ln = jp9 if (k % 2 == 0) else cn9
            tb = rng.uniform(87.05, 89.20)
            life = rng.uniform(1.25, 2.10)
            x0 = rng.uniform(ln.bbox_x0 + 28, ln.bbox_x1 - 28)
            y0 = ln.y + rng.uniform(4.0, 42.0)
            vx = rng.uniform(-16.0, 20.0)
            vy = rng.uniform(-26.0, -10.0)
            sz = rng.uniform(5.6, 8.6)
            ph = rng.uniform(0.0, math.tau)
            col = (72, 166, 255) if (k % 3 != 0) else (188, 126, 255)
            self.dream_bflies.append((tb, life, x0, y0, vx, vy, sz, ph, col))

        self.night_petals = []
        for k in range(20):
            ln = jp9 if (k % 2 == 0) else cn9
            tb = rng.uniform(89.45, 89.95)
            life = rng.uniform(0.75, 1.15)
            x0 = rng.uniform(ln.bbox_x0 + 30, ln.bbox_x1 - 30)
            y0 = ln.y + rng.uniform(8.0, 38.0)
            vx = rng.uniform(-24.0, 24.0)
            vy = rng.uniform(28.0, 62.0)
            rad = rng.uniform(4.5, 7.8)
            rot0 = rng.uniform(0.0, math.tau)
            self.night_petals.append((tb, life, x0, y0, vx, vy, rad, rot0))

    @staticmethod
    def _draw_petal_poly(d: ImageDraw.ImageDraw, x: float, y: float, rad: float, ang: float, rgba):
        ca, sa = math.cos(ang), math.sin(ang)
        rx, ry = rad * 1.38, rad * 0.74
        d.polygon([
            (x + ca * rx, y + sa * rx),
            (x - sa * ry, y + ca * ry),
            (x - ca * rx * 0.82, y - sa * rx * 0.82),
            (x + sa * ry, y - ca * ry),
        ], fill=rgba)

    def draw_under(self, canvas: Image.Image, t: float):
        if not self.jp8.is_active(t):
            return
        fo8 = 1.0 - ease_in_out(self.jp8.exit_progress(t))
        w_white = 0.0
        if t < 83.55:
            w_white = clamp01((t - 81.80) / 0.18) * (1.0 - ease_in_out(clamp01((t - 82.95) / 0.60)))
        elif t > 86.40:
            w_white = clamp01((t - 86.40) / 0.15) * 0.65
        if w_white * fo8 > 0.02:
            composite_alpha(canvas, self.veil8_jp, self.jp8.bbox_x0 - 62, self.jp8.bbox_y0 - 54, w_white * fo8)
            composite_alpha(canvas, self.veil8_cn, self.cn8.bbox_x0 - 62, self.cn8.bbox_y0 - 54, w_white * fo8)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return

        # ---- L08 区间 (81.77s ~ 87.11s): 82.83s 深红蔷薇花瓣炸裂! ----
        if self.jp8.is_active(t):
            fo8 = 1.0 - ease_in_out(self.jp8.exit_progress(t))
            if t >= self.t_burst:
                p_im = Image.new("RGBA", (canvas.width, canvas.height), (200, 20, 48, 0))
                pd = ImageDraw.Draw(p_im)
                has_p = False
                for t0, life, x0, y0, vx, vy, rad, rot0, vrot, col in self.burst_petals:
                    age = t - t0
                    if 0.0 <= age <= life:
                        u = age / life
                        pa = math.sin(math.pi * (u ** 0.72)) * fo8
                        if pa > 0.03:
                            has_p = True
                            # 空气阻力减速 + 飘摇下落
                            drag = (1.0 - 0.42 * u)
                            px = x0 + vx * age * drag + 7.5 * math.sin(age * 4.8 + rot0)
                            py = y0 + vy * age + 18.0 * (age ** 1.5)
                            self._draw_petal_poly(pd, px, py, rad, rot0 + vrot * age, (*col, int(232 * pa)))
                if has_p:
                    canvas.alpha_composite(p_im)

        # ---- L09 区间 (87.11s ~ 90.54s): 有栖沧蓝幻蝶 + 粉紫梦境呼吸 + 89.6s 深红落瓣 ----
        if self.jp9.is_active(t):
            fo9 = 1.0 - ease_in_out(self.jp9.exit_progress(t))
            if fo9 > 0.02 and self.jp9.exit_progress(t) < 0.25:
                w_bl = (0.45 + 0.18 * math.sin((t - 87.11) * 3.6)) * fo9
                for line, b_map in ((self.jp9, self.jp9_blue), (self.cn9, self.cn9_blue)):
                    for i, (s_core, _, _, px_c, py_c, _, _, is_sp) in enumerate(line.chars):
                        if is_sp or i not in b_map:
                            continue
                        dx, dy, a_ch, _ = line.char_state(i, t)
                        if a_ch > 0.04:
                            bh, bx, by = b_map[i]
                            composite_alpha(canvas, bh, bx + dx, by + dy, a_ch * w_bl)
                            composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

            d_im = Image.new("RGBA", (canvas.width, canvas.height), (82, 166, 255, 0))
            dd = ImageDraw.Draw(d_im)
            has_d = False
            for tb, life, x0, y0, vx, vy, sz, ph, col in self.dream_bflies:
                age = t - tb
                if 0.0 <= age <= life:
                    u = age / life
                    ba = math.sin(math.pi * u) * fo9
                    if ba > 0.03:
                        has_d = True
                        px = x0 + vx * age + 6.0 * math.sin(age * 4.2 + ph)
                        py = y0 + vy * age
                        _draw_micro_butterfly(dd, px, py, sz, math.sin(t * 15.5 + ph),
                                              -0.2 + 0.2 * math.cos(age * 2.8), (*col, int(224 * ba)))

            for tb, life, x0, y0, vx, vy, rad, rot0 in self.night_petals:
                age = t - tb
                if 0.0 <= age <= life:
                    u = age / life
                    pa = math.sin(math.pi * u)
                    if pa > 0.03:
                        has_d = True
                        px = x0 + vx * age + 5.5 * math.sin(age * 5.2 + rot0)
                        py = y0 + vy * age
                        self._draw_petal_poly(dd, px, py, rad, rot0 + age * 3.8, (186, 12, 38, int(230 * pa)))
            if has_d:
                canvas.alpha_composite(d_im)


# =====================================================================
#  [L10] 暗棋盘舞台追光 + 『取り戻す/重新夺回』红线牵引 + 双人剪影花瓣爆散 (90.54s ~ 99.43s)
# =====================================================================
class ChiaroscuroBondReach(Layer):
    z = 34

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_shatter1 = 93.23   # 咲 & 弥生剪影碎为深红花瓣!
        self.t_shatter2 = 97.94   # 有栖 & 樱子剪影碎为深红花瓣!

        # 『取り戻す』(idx 3..6) 与『重新夺回』(idx 5..8) 从两侧轻微张开再紧紧相扣聚拢!
        def _make_reach_hook(i_start: int, i_end: int, t_pull: float):
            mid = 0.5 * (i_start + i_end)

            def _hook(i: int, t: float):
                if i_start <= i <= i_end:
                    u = ease_out(clamp01((t - t_pull) / 1.15))
                    # 初态向外微张 +-9px, 随歌声紧紧牵引归位并轻柔相依
                    sep = (i - mid) * 5.8 * (1.0 - u)
                    return sep, -1.8 * math.sin(math.pi * u), 1.0
                return 0.0, 0.0, 1.0

            return _hook

        jp_line.motion_hook = _make_reach_hook(3, 6, 93.05)
        cn_line.motion_hook = _make_reach_hook(5, 8, 91.60)

        # 预烘舞台柔白追光光束衬底
        self.spot_jp = _soft_cushion(jp_line.bbox_x1 - jp_line.bbox_x0 + 48, 92,
                                     rgb=(255, 232, 238), alpha=34, blur_r=22.0)
        self.spot_cn = _soft_cushion(cn_line.bbox_x1 - cn_line.bbox_x0 + 48, 92,
                                     rgb=(255, 232, 238), alpha=34, blur_r=22.0)

        # 93.23s & 97.94s 两次双人剪影爆散的丝绒红花瓣池
        rng = random.Random(9054)
        self.petals = []
        for t_sh in (self.t_shatter1, self.t_shatter2):
            for k in range(26):
                ln = jp_line if (k % 2 == 0) else cn_line
                tb = t_sh + rng.uniform(0.0, 0.18)
                life = rng.uniform(0.95, 1.65)
                x0 = rng.uniform(ln.bbox_x0 + 36, ln.bbox_x1 - 36)
                y0 = ln.y + rng.uniform(8.0, 38.0)
                vx = rng.uniform(-54.0, 54.0)
                vy = rng.uniform(-22.0, 46.0)
                rad = rng.uniform(4.2, 7.6)
                rot0 = rng.uniform(0.0, math.tau)
                vrot = rng.uniform(-4.5, 4.5)
                self.petals.append((tb, life, x0, y0, vx, vy, rad, rot0, vrot))

    def _draw_red_thread(self, canvas: Image.Image, line, idx_a: int, idx_b: int, t: float, fo: float):
        """在『君 <-> 取り戻す』与『你 <-> 重新夺回』之间牵起一缕温润绯金命运红线!"""
        if t < self.start + 0.85:
            return
        w_th = ease_out(clamp01((t - (self.start + 0.85)) / 0.90)) * fo
        if w_th <= 0.03 or idx_b >= len(line.chars):
            return

        _, _, _, _, _, cx_a, _, _ = line.chars[idx_a]
        _, _, _, _, _, cx_b, _, _ = line.chars[idx_b]
        dxa, _, aa, _ = line.char_state(idx_a, t)
        dxb, _, ab, _ = line.char_state(idx_b, t)
        w_th *= min(aa, ab)
        if w_th <= 0.03:
            return

        xa, xb = cx_a + dxa, cx_b + dxb
        if xa > xb:
            xa, xb = xb, xa
        span = max(24.0, xb - xa)
        y_base = line.y + line.font.size + 4

        SS = 2
        w = int(span + 32)
        h = 28
        im = Image.new("RGBA", (w * SS, h * SS), (242, 68, 102, 0))
        d = ImageDraw.Draw(im)
        pts = []
        sag = (5.5 + 1.5 * math.sin(t * 2.8)) * SS
        for k in range(37):
            u = k / 36.0
            px = (16 + span * u) * SS
            py = 6 * SS + sag * math.sin(math.pi * u)
            pts.append((px, py))
        d.line(pts, fill=(246, 68, 102, int(172 * w_th)), width=3)
        d.line(pts, fill=(255, 210, 222, int(96 * w_th)), width=1)
        for end_pt in (pts[0], pts[-1]):
            rr = 2.8 * SS
            d.ellipse([end_pt[0] - rr, end_pt[1] - rr, end_pt[0] + rr, end_pt[1] + rr],
                      fill=(255, 226, 232, int(205 * w_th)))
        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, xa - 16, y_base - 4, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 1) 暗黑棋盘舞台柔光追光晕 (z=22)
        a_sp = ease_out(clamp01((t - self.start) / 0.55)) * fo
        composite_alpha(canvas, self.spot_jp, self.jp.bbox_x0 - 68, self.jp.y - 64, a_sp)
        composite_alpha(canvas, self.spot_cn, self.cn.bbox_x0 - 68, self.cn.y - 64, a_sp)

        # 2) 命运红线牵引 (『君(0) -> 戻(5)』与『你(3) -> 夺(7)』)
        if self.jp.exit_progress(t) < 0.25:
            self._draw_red_thread(canvas, self.jp, 0, 5, t, fo)
            self._draw_red_thread(canvas, self.cn, 3, 7, t, fo)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 3) 93.23s & 97.94s 双人剪影碎裂深红花瓣爆散!
        p_im = Image.new("RGBA", (canvas.width, canvas.height), (210, 18, 48, 0))
        pd = ImageDraw.Draw(p_im)
        has_p = False
        for tb, life, x0, y0, vx, vy, rad, rot0, vrot in self.petals:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                pa = math.sin(math.pi * (u ** 0.75)) * fo
                if pa > 0.03:
                    has_p = True
                    px = x0 + vx * age * (1.0 - 0.35 * u) + 6.0 * math.sin(age * 4.6 + rot0)
                    py = y0 + vy * age + 14.0 * (age ** 1.4)
                    WhiteRoseToBlueDream._draw_petal_poly(
                        pd, px, py, rad, rot0 + vrot * age, (206, 18, 48, int(228 * pa))
                    )
        if has_p:
            canvas.alpha_composite(p_im)


# =====================================================================
#  [L11] 情感终章走马灯微闪 + 106.95s~109.08s 分形猩红血墨斑块吞噬!
# =====================================================================
class CrimsonInkBlotFinale(Layer):
    z = 36

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_blot = 106.92     # 原片猩红血墨斑块开始在有栖身上浮现 (106.95s) 直至 109.10s 全屏纯红!

        # 106.92s 之后接管默认水波退场, 改用分形猩红血墨侵蚀吞噬!
        jp_line.suppress_spans.append((self.t_blot, jp_line.end + 0.25))
        cn_line.suppress_spans.append((self.t_blot, cn_line.end + 0.25))

        # 走马灯三次黑闪切镜 (102.67s / 103.21s / 103.79s) 共振光晕
        self.jp_mem = PocketwatchMiracleMotes._prep_halos(jp_line, font_jp, (176, 118, 255), 0)
        self.cn_mem = PocketwatchMiracleMotes._prep_halos(cn_line, font_cn, (176, 118, 255), C.CN_SYNTH_BOLD)

        # 为日/中两行预生成多尺度有机阿米巴分形血墨噪声场 [0..1]
        self.jp_rect, self.jp_field = self._build_blot_field(jp_line, seed=10695)
        self.cn_rect, self.cn_field = self._build_blot_field(cn_line, seed=10810)

    @staticmethod
    def _build_blot_field(line, seed: int):
        bx0 = max(0, line.bbox_x0 - 16)
        by0 = max(0, line.bbox_y0 - 14)
        bx1 = min(C.W, line.bbox_x1 + 16)
        by1 = min(C.H, line.bbox_y1 + 14)
        bw, bh = max(16, bx1 - bx0), max(16, by1 - by0)

        rng = np.random.RandomState(seed)
        # 三尺度高斯有机斑块叠加 (复刻原片 Rorschach 血墨晕开轮廓!)
        f_acc = np.zeros((bh, bw), dtype=np.float32)
        for sigma, weight in ((20.0, 0.52), (9.0, 0.32), (3.8, 0.16)):
            raw = (rng.rand(bh, bw) * 255.0).astype(np.uint8)
            sm = np.array(Image.fromarray(raw, mode="L").filter(ImageFilter.GaussianBlur(sigma)),
                          dtype=np.float32)
            sm = (sm - sm.min()) / max(1e-5, sm.max() - sm.min())
            f_acc += sm * weight

        # 从外缘向中心略微偏置, 让血墨从四周边角向笔芯包抄吞噬
        yy = np.linspace(-1.0, 1.0, bh, dtype=np.float32)[:, None]
        xx = np.linspace(-1.0, 1.0, bw, dtype=np.float32)[None, :]
        edge_bias = 0.14 * (xx * xx * 0.65 + yy * yy * 0.35)
        f_acc = f_acc - edge_bias
        f_acc = (f_acc - f_acc.min()) / max(1e-5, f_acc.max() - f_acc.min())
        return (bx0, by0, bw, bh), f_acc

    def _blot_threshold(self, t: float) -> float:
        """精确拟合原片 106.92s -> 109.08s 血墨扩张曲线 (含 107.50s 猩红骤闪脉冲!)。"""
        u = clamp01((t - self.t_blot) / (self.end - self.t_blot))
        base = ease_in_out(u) * 1.12
        # 107.50s 原片全屏红闪瞬间血墨猛然漫溢一拍随后微退继续吞噬
        flash_pulse = 0.24 * math.exp(-((t - 107.50) / 0.11) ** 2)
        return min(1.14, base + flash_pulse)

    def _render_ink_eroded_line(self, canvas: Image.Image, line, rect, field: np.ndarray, tau: float):
        bx0, by0, bw, bh = rect
        strip = Image.new("RGBA", (bw, bh), (120, 4, 12, 0))
        # 取 106.90s 稳定完整态字形作为被血墨吞噬的底片
        line.render_to_buffer(strip, self.t_blot - 0.02, bx0, by0)
        arr = np.array(strip, dtype=np.float32)
        alpha_orig = arr[..., 3]
        if alpha_orig.max() <= 1.0:
            return

        # field < tau - 0.14: 已被猩红血墨彻底吞没 (alpha -> 0, 融入原片纯红底幕!)
        # tau - 0.14 <= field < tau + 0.08: 正在渗血染红的湿润墨缘 (白字化作鲜红血墨 RGB(212, 6, 16)!)
        survive = np.clip((field - (tau - 0.14)) / 0.14, 0.0, 1.0)
        bleed = np.clip(1.0 - np.abs(field - (tau - 0.01)) / 0.13, 0.0, 1.0)
        # 已侵入内侧更深染红
        wet = np.clip((tau + 0.09 - field) / 0.18, 0.0, 1.0)
        crimson_mix = np.maximum(bleed, wet * 0.88)[..., None]

        blood_rgb = np.array([208.0, 4.0, 14.0], dtype=np.float32)[None, None, :]
        arr[..., :3] = arr[..., :3] * (1.0 - crimson_mix) + blood_rgb * crimson_mix
        arr[..., 3] = alpha_orig * (survive ** 1.25)

        composite_alpha(canvas, Image.fromarray(np.clip(arr, 0.0, 255.0).astype(np.uint8)), bx0, by0, 1.0)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end + 0.05:
            return

        # 1) 106.92s ~ 109.08s: 分形猩红血墨吞噬终幕!
        if t >= self.t_blot:
            tau = self._blot_threshold(t)
            if tau < 1.135:
                self._render_ink_eroded_line(canvas, self.jp, self.jp_rect, self.jp_field, tau)
                self._render_ink_eroded_line(canvas, self.cn, self.cn_rect, self.cn_field, tau)
            return

        # 2) 102.67s / 103.21s / 103.79s 三次走马灯闪回瞬间的紫蓝幽光脉动
        pulse_m = 0.0
        for tm in (102.67, 103.21, 103.79):
            pulse_m = max(pulse_m, math.exp(-((t - tm) / 0.16) ** 2))
        w_mem = 0.22 + 0.55 * pulse_m
        for line, m_map in ((self.jp, self.jp_mem), (self.cn, self.cn_mem)):
            for i, (s_core, _, _, px_c, py_c, _, _, is_sp) in enumerate(line.chars):
                if is_sp or i not in m_map:
                    continue
                dx, dy, a_ch, _ = line.char_state(i, t)
                if a_ch > 0.04:
                    mh, mx, my = m_map[i]
                    composite_alpha(canvas, mh, mx + dx, my + dy, a_ch * w_mem)
                    composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)


# =====================================================================
#  [尾奏 2:00 猩红题记] 原生级内嵌『这是一个甜蜜而又幸福的恶梦故事』
#    对应原片 119.50s ~ 124.88s 中央『これは甘くて幸せな悪い夢のお話』:
#    - 同族华康金文体修长哥特纵横比 (scale_y=1.24), 无黑边纯红粉发光笔触
#    - 『梦』字单独放大 1.38x, 并在 122.00s~122.80s 帧同步渗血点亮鲜红辉光!
#    - 123.62s~124.88s 自上而下逐行卷烟扭曲 + 横向水波蒸发消散!
# =====================================================================
class OutroTagline(Layer):
    z = 42

    def __init__(self):
        self.t_in = 119.50
        self.t_steady = 121.65
        self.t_bleed0 = 120.85   # 与原片『夢』一致: 从暗血红逐步燃起纯正鲜红光华!
        self.t_bleed1 = 122.20
        self.t_smoke = 123.62    # 原片自上而下开始卷起水波青烟蒸发的精确时刻!
        self.t_end = 124.88

        self.text = "这是一个甜蜜而又幸福的恶梦故事"
        self.meng_idx = self.text.index("梦")  # idx = 12
        self.y_center = 688                    # 稳居原生『夢』(底端 y=618) 正下方黄金呼吸位!

        self.strip_base, self.strip_hot, self.sx0, self.sy0 = self._prebake_strips()

    def _prebake_strips(self):
        """3x 超采样预烘焙无黑边修长金文体题记条带 (base 暗血红『梦』+ hot 纯正猩红『梦』)。"""
        SS = 3
        scale_y = 1.34           # 复刻原片『これは甘くて...』标志性的高挑修长哥特童话比例!
        sz_norm = 45
        sz_meng = 65             # 『梦』字放大一号 (约 1.44x), 呼应原片醒目的大号『夢』!
        spacing = 12

        f_norm = ImageFont.truetype(C.FONT_PATH_CN, sz_norm * SS)
        f_meng = ImageFont.truetype(C.FONT_PATH_CN, sz_meng * SS)

        # 测量每字宽度
        advs = []
        for idx, ch in enumerate(self.text):
            f = f_meng if idx == self.meng_idx else f_norm
            advs.append(f.getlength(ch) / SS)

        total_w = sum(advs) + spacing * (len(self.text) - 1)
        pad_x = 58
        pad_y = 62
        W1 = int(math.ceil(total_w + pad_x * 2))
        H1_raw = int(math.ceil(sz_meng + pad_y * 2))
        W3 = W1 * SS
        H3_raw = H1_raw * SS

        # 精确对齐原片色值: 普通字灰粉珊红 (246, 130, 136), 『梦』纯正高饱和鲜血红 (绝不泛粉白!)
        norm_col = (246, 130, 136)
        norm_glow = (192, 42, 52)
        meng_base_col = (206, 10, 14)
        meng_base_glow = (156, 6, 10)
        meng_hot_col = (255, 14, 18)
        meng_hot_glow = (232, 8, 12)

        # 1) 普通 14 字层
        norm_im = Image.new("RGBA", (W3, H3_raw), (*norm_col, 0))
        norm_gl = Image.new("RGBA", (W3, H3_raw), (*norm_glow, 0))
        dn = ImageDraw.Draw(norm_im)
        dng = ImageDraw.Draw(norm_gl)

        # 2) 『梦』初态深血红层 & 燃血高光层
        mb_im = Image.new("RGBA", (W3, H3_raw), (*meng_base_col, 0))
        mb_gl = Image.new("RGBA", (W3, H3_raw), (*meng_base_glow, 0))
        mh_im = Image.new("RGBA", (W3, H3_raw), (*meng_hot_col, 0))
        mh_gl = Image.new("RGBA", (W3, H3_raw), (*meng_hot_glow, 0))
        dmb = ImageDraw.Draw(mb_im)
        dmbg = ImageDraw.Draw(mb_gl)
        dmh = ImageDraw.Draw(mh_im)
        dmhg = ImageDraw.Draw(mh_gl)

        cur_x = pad_x * SS
        cy3 = (H3_raw * 0.5)
        for idx, ch in enumerate(self.text):
            w3 = advs[idx] * SS
            if idx == self.meng_idx:
                bb = f_meng.getbbox(ch)
                bh = (bb[3] - bb[1]) if bb else sz_meng * SS
                ox = cur_x + w3 * 0.5 - ((bb[0] + bb[2]) * 0.5 if bb else w3 * 0.5)
                # 与原片『夢』一致: 顶端略高于普通字顶、底端长撇潇洒探出基线下方!
                oy = cy3 - bh * 0.48 - (bb[1] if bb else 0)
                dmbg.text((ox, oy), ch, font=f_meng, fill=(*meng_base_glow, 220),
                          stroke_width=3, stroke_fill=(*meng_base_glow, 200))
                dmb.text((ox, oy), ch, font=f_meng, fill=(*meng_base_col, 255),
                         stroke_width=1, stroke_fill=(*meng_base_col, 240))

                dmhg.text((ox, oy), ch, font=f_meng, fill=(*meng_hot_glow, 255),
                          stroke_width=5, stroke_fill=(*meng_hot_glow, 235))
                dmh.text((ox, oy), ch, font=f_meng, fill=(*meng_hot_col, 255),
                         stroke_width=1, stroke_fill=(*meng_hot_col, 255))
            else:
                bb = f_norm.getbbox(ch)
                bh = (bb[3] - bb[1]) if bb else sz_norm * SS
                ox = cur_x + w3 * 0.5 - ((bb[0] + bb[2]) * 0.5 if bb else w3 * 0.5)
                oy = cy3 - bh * 0.50 - (bb[1] if bb else 0)
                dng.text((ox, oy), ch, font=f_norm, fill=(*norm_glow, 185),
                         stroke_width=2, stroke_fill=(*norm_glow, 165))
                dn.text((ox, oy), ch, font=f_norm, fill=(*norm_col, 250),
                        stroke_width=1, stroke_fill=(*norm_col, 225))
            cur_x += w3 + spacing * SS

        norm_gl = norm_gl.filter(ImageFilter.GaussianBlur(4.2 * SS))
        mb_gl = mb_gl.filter(ImageFilter.GaussianBlur(5.0 * SS))
        mh_gl = mh_gl.filter(ImageFilter.GaussianBlur(8.5 * SS))

        base_3x = Image.new("RGBA", (W3, H3_raw), (*norm_col, 0))
        base_3x.alpha_composite(norm_gl)
        base_3x.alpha_composite(mb_gl)
        base_3x.alpha_composite(norm_im)
        base_3x.alpha_composite(mb_im)

        hot_3x = Image.new("RGBA", (W3, H3_raw), (*meng_hot_glow, 0))
        hot_3x.alpha_composite(mh_gl)
        hot_3x.alpha_composite(mh_im)

        # 缩回 1x 并施加修长哥特纵向比例 scale_y = 1.24
        H1 = int(round(H1_raw * scale_y))
        strip_base = base_3x.resize((W1, H1), Image.Resampling.LANCZOS)
        strip_hot = hot_3x.resize((W1, H1), Image.Resampling.LANCZOS)

        sx0 = int(round(C.W * 0.5 - W1 * 0.5))
        sy0 = int(round(self.y_center - H1 * 0.5))
        return strip_base, strip_hot, sx0, sy0

    @staticmethod
    def _apply_topdown_curl_smoke(strip_im: Image.Image, u_global: float) -> Image.Image:
        """复刻原片 123.62s~124.88s 标志性的『自上而下逐行卷烟上浮 + 横向水波蒸发』滤镜!"""
        arr = np.array(strip_im, dtype=np.float32)
        h, w, _ = arr.shape
        ys = np.arange(h, dtype=np.float32)[:, None]
        xs = np.arange(w, dtype=np.float32)[None, :]

        # 顶端行比底端行提前约 0.28 进度开始卷烟扭曲 (与 orig_outro_tagline.jpg t=123.75s 完全一致!)
        y_norm = ys / max(1.0, h - 1.0)
        u_row = np.clip((u_global * 1.32) - y_norm * 0.32, 0.0, 1.0)

        # 2D 卷烟涡流位移: 横向正弦水波 + 纵向青烟上卷拉伸
        dx = (
            13.5 * (u_row ** 1.35) * np.sin(ys * 0.14 + xs * 0.028 - u_global * 8.2)
            + 5.8 * (u_row ** 1.65) * np.cos(ys * 0.31 - xs * 0.052 + u_global * 11.4)
        )
        dy = (
            -16.0 * (u_row ** 1.45) * (0.65 + 0.35 * np.sin(xs * 0.045 + u_global * 5.0))
            + 4.2 * (u_row ** 1.5) * np.cos(xs * 0.085 - ys * 0.12)
        )

        src_x = np.clip(xs - dx, 0.0, w - 1.001)
        src_y = np.clip(ys - dy, 0.0, h - 1.001)
        x0 = np.floor(src_x).astype(np.int32)
        y0 = np.floor(src_y).astype(np.int32)
        fx = (src_x - x0)[..., None]
        fy = (src_y - y0)[..., None]

        p00 = arr[y0, x0]
        p10 = arr[y0, x0 + 1]
        p01 = arr[y0 + 1, x0]
        p11 = arr[y0 + 1, x0 + 1]
        warped = (
            p00 * (1.0 - fx) * (1.0 - fy)
            + p10 * fx * (1.0 - fy)
            + p01 * (1.0 - fx) * fy
            + p11 * fx * fy
        )

        # 顶部先行烟化消散, 底部『梦』的长撇最后隐入暗红帷幕
        fade_row = (1.0 - (3.0 * u_row * u_row - 2.0 * u_row * u_row * u_row)) ** 1.22
        warped[..., 3] *= fade_row

        out = Image.fromarray(np.clip(warped, 0.0, 255.0).astype(np.uint8))
        if u_global > 0.12:
            out = out.filter(ImageFilter.GaussianBlur(3.4 * ((u_global - 0.12) / 0.88)))
        return out

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_in or t > self.t_end:
            return

        # 合成当前时刻 strip (叠加 122.00s~122.80s 『梦』字渗血燃红辉光!)
        cur = self.strip_base.copy()
        if t > self.t_bleed0:
            u_hot = ease_in_out(clamp01((t - self.t_bleed0) / (self.t_bleed1 - self.t_bleed0)))
            # 微微心跳搏动
            pulse = 1.0 + 0.08 * math.sin((t - self.t_bleed0) * 4.2) if t > self.t_bleed1 else 1.0
            composite_alpha(cur, self.strip_hot, 0, 0, clamp01(u_hot * 0.90 * pulse))

        # 1) 119.50s ~ 121.65s: 从猩红迷雾中凝结显影 (帧同步原片高斯雾化淡入曲线!)
        if t < self.t_steady:
            u_in = clamp01((t - self.t_in) / (self.t_steady - self.t_in))
            alpha_in = ease_in_out(u_in) ** 1.15
            blur_r = 6.8 * ((1.0 - ease_out(u_in)) ** 1.35)
            if blur_r > 0.35:
                cur = cur.filter(ImageFilter.GaussianBlur(blur_r))
            composite_alpha(canvas, cur, self.sx0, self.sy0, alpha_in)
            return

        # 2) 123.62s ~ 124.88s: 自上而下卷烟扭曲 + 水波蒸发退场!
        if t >= self.t_smoke:
            u_sm = clamp01((t - self.t_smoke) / (self.t_end - self.t_smoke))
            warped = self._apply_topdown_curl_smoke(cur, u_sm)
            composite_alpha(canvas, warped, self.sx0, self.sy0, 1.0)
            return

        # 3) 121.65s ~ 123.62s: 清晰静谧凝视
        composite_alpha(canvas, cur, self.sx0, self.sy0, 1.0)


def with_underlay(stage_layer):
    """同时返回 [背景衬底适配器(z=22), 前景演出层(z=34+)]。"""
    return [_UnderlayAdapter(stage_layer), stage_layer]

