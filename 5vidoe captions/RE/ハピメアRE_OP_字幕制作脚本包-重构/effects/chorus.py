# -*- coding: utf-8 -*-
"""副歌高潮 (L10 ~ L17, 53.19s ~ 76.93s) 与片尾涂抹彩蛋 (94.83s ~ 96.50s) 专属演出图层。

全部时间点均与 ../opre.mkv 24fps 实测帧严格对齐:
  - ChorusBurstTear       : L10 53.33s 巨型红玫瑰爆裂绯红光波 + 54.67s 落泪特写冰晶水波微光
  - MoonRibbonTrail       : L11 弯月微弧托『夢』+ 56.0s 流光紫粉丝带在字下蜿蜒穿行
  - ButterflyDreamFarewell: L12 59.833s 紫粉蝶海爆发霓虹柔光接管 + 双『夢』振翅荧光蝶飞升道别
  - CageBarsOpen          : L13『檻』落下古典暗金笼栏 -> L14『見える景色の先を』笼栏向两侧敞开化光
  - WishStarlightAura     : L15 66.7s 强白光抗过曝深海蓝底衬 + 67.40s『願う』暖金十字祈愿星涟漪
  - KeyRepairSweep        : L16 回收 B 段伏笔!『壊』『鍵』初始保持斜裂错位 -> 69.85s 金钥匙特写暖金扫光将其无缝焊合修复!
  - RubyRingReach         : L17 73.85s 红宝石金戒六芒十字星闪 + 75.22s『手を伸ばして』字距向光舒展延伸
  - OutroRedactedCards    : 94.833s~96.500s 片尾双定格卡 (『于是今天 ███ 依然做着梦。』+ 11帧闪白卡『关于 ███ 的事，无人知晓』) 原生级红笔涂抹对位
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .base import Layer, clamp01, ease_out, ease_in_out, char_sprites, char_halo, composite_alpha
import config as C


class ChorusBurstTear(Layer):
    """L10 見忘れている / 我一直都忘记了:
      - 53.333s 红玫瑰炸裂瞬间迸发绯红柔光冲击环;
      - 54.67s 切入落泪特写时, 在『忘れている』下方漾开一圈晶莹泪滴折射光纹。
    """
    z = 46

    def __init__(self, jp_line, cn_line, t_burst=53.458, t_tear=54.833):
        self.jp = jp_line
        self.cn = cn_line
        self.t_burst = t_burst
        self.t_tear = t_tear
        self.jp_center = self._line_center(jp_line)
        self.cn_center = self._line_center(cn_line)

    @staticmethod
    def _line_center(line):
        xs = [x + s.width * 0.5 for s, _, x, _ in line.chars]
        ys = [y + s.height * 0.5 for _, s, _, y in line.chars]
        return (sum(xs) / max(1, len(xs)), sum(ys) / max(1, len(ys)))

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return

        # 1) 53.333s 副歌引爆绯红冲击柔光波
        dt_b = t - self.t_burst
        if 0.0 <= dt_b <= 0.55:
            u = dt_b / 0.55
            e = ease_out(u)
            fa = (1.0 - u) ** 1.65 * 0.72
            for cx, cy in (self.jp_center, self.cn_center):
                pw, ph = 380, 130
                sp = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
                d = ImageDraw.Draw(sp)
                rx = 55 + 125 * e
                ry = 18 + 38 * e
                d.ellipse([pw * 0.5 - rx, ph * 0.5 - ry, pw * 0.5 + rx, ph * 0.5 + ry],
                          outline=(255, 88, 118, int(215 * fa)), width=3)
                d.ellipse([pw * 0.5 - rx * 0.65, ph * 0.5 - ry * 0.65,
                           pw * 0.5 + rx * 0.65, ph * 0.5 + ry * 0.65],
                          fill=(235, 38, 72, int(90 * fa)))
                sp = sp.filter(ImageFilter.GaussianBlur(4.0))
                composite_alpha(canvas, sp, cx - pw * 0.5, cy - ph * 0.5, 1.0)

        # 2) 54.67s 晶莹泪光涟漪 (呼应有栖眼角滑落的泪珠)
        dt_t = t - self.t_tear
        if 0.0 <= dt_t <= 0.85:
            ut = dt_t / 0.85
            et = ease_out(ut)
            ta = math.sin(math.pi * ut) * 0.78
            cx, cy = self.jp_center[0] + 18, self.jp_center[1] + 22
            pw, ph = 220, 84
            SS = 2
            sp = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(sp)
            ox, oy = pw * 0.5 * SS, ph * 0.5 * SS
            rx, ry = (24 + 66 * et) * SS, (7 + 16 * et) * SS
            d.ellipse([ox - rx, oy - ry, ox + rx, oy + ry],
                      outline=(210, 242, 255, int(205 * ta)), width=max(1, int(1.6 * SS)))
            # 中央微小泪珠星光
            if ut < 0.55:
                sa = (1.0 - ut / 0.55) * ta
                d.ellipse([ox - 3 * SS, oy - 5 * SS - ut * 8 * SS,
                           ox + 3 * SS, oy + 3 * SS - ut * 8 * SS],
                          fill=(235, 250, 255, int(235 * sa)))
            sp = sp.resize((pw, ph), Image.Resampling.LANCZOS)
            composite_alpha(canvas, sp, cx - pw * 0.5, cy - ph * 0.5, 1.0)


class MoonRibbonTrail(Layer):
    """L11 夢はそこにあるはず / 梦本就该存在这里 (55.60s ~ 57.90s):
    呼应原片新月夜空下舞亚身畔盘旋的紫粉流光丝带——
    句首『夢/梦』左上方浮现纤细银白新月牙, 一条流光紫粉丝带沿字底轻盈穿行。
    """
    z = 38

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.jp_box = self._box(jp_line)
        self.cn_box = self._box(cn_line)

    @staticmethod
    def _box(line):
        xs = [x for _, _, x, _ in line.chars]
        rights = [x + s.width for s, _, x, _ in line.chars]
        y0 = line.chars[0][3]
        h0 = line.chars[0][0].height
        return (min(xs), max(rights), y0, y0 + h0)

    def _draw_ribbon_and_moon(self, canvas, line, box, t, fo, exit_dy, is_jp=True):
        x0, x1, y0, y1 = box
        prog = ease_out(clamp01((t - line.start) / (line.end - line.start - 0.25)))
        if prog <= 0.02:
            return

        # 1) 『夢 / 梦』(首字) 左上角纤巧银白新月弧
        s0, _, cx0, cy0 = line.chars[0]
        moon_a = ease_out(clamp01((t - line.start) / 0.38)) * fo
        if moon_a > 0.02:
            SS = 3
            mdim = 56
            mp = Image.new("RGBA", (mdim * SS, mdim * SS), (0, 0, 0, 0))
            md = ImageDraw.Draw(mp)
            mc = mdim * 0.5 * SS
            mr = 15.5 * SS
            md.ellipse([mc - mr, mc - mr, mc + mr, mc + mr], fill=(248, 244, 255, int(225 * moon_a)))
            # 挖出新月内弧
            md.ellipse([mc - mr + 5.2 * SS, mc - mr - 3.2 * SS,
                        mc + mr + 5.2 * SS, mc + mr - 3.2 * SS], fill=(0, 0, 0, 0))
            mp_glow = mp.resize((mdim, mdim), Image.Resampling.LANCZOS)
            mp_blur = mp_glow.filter(ImageFilter.GaussianBlur(3.2))
            composite_alpha(canvas, mp_blur, cx0 - 6, cy0 - 4 + exit_dy, 0.75)
            composite_alpha(canvas, mp_glow, cx0 - 6, cy0 - 4 + exit_dy, 0.92)

        # 2) 字下流光紫粉丝带
        rx0 = max(0, int(x0 - 28))
        rx1 = min(1920, int(x1 + 28))
        ry0 = max(0, int(y0 + 18 + exit_dy))
        ry1 = min(1080, int(y1 + 26 + exit_dy))
        rw, rh = rx1 - rx0, ry1 - ry0
        if rw <= 8 or rh <= 8:
            return

        SS = 2
        reg = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(reg)
        N = 80
        n_cur = max(3, int(N * prog))
        span = (x1 - x0 + 24) * SS
        sx0 = (x0 - 12 - rx0) * SS
        ym = (y1 - 12 + exit_dy - ry0) * SS

        pts = []
        for k in range(n_cur + 1):
            u = k / N
            px = sx0 + span * u
            wave = math.sin(u * math.pi * 2.4 - t * 2.6 + (0 if is_jp else 1.5)) * 6.5 * SS
            pts.append((px, ym + wave, u))

        for k in range(len(pts) - 1):
            xa, ya, u1 = pts[k]
            xb, yb, _ = pts[k + 1]
            taper = math.sin(math.pi * min(1.0, u1 / max(0.05, prog))) ** 0.6
            w_glow = max(2, int(5.5 * SS * taper))
            w_core = max(1, int(1.8 * SS * taper))
            d.line([xa, ya, xb, yb], fill=(196, 62, 245, int(135 * fo * taper)), width=w_glow)
            d.line([xa, ya, xb, yb], fill=(252, 215, 255, int(220 * fo * taper)), width=w_core)

        reg_1x = reg.resize((rw, rh), Image.Resampling.LANCZOS)
        composite_alpha(canvas, reg_1x, rx0, ry0, 1.0)

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        self._draw_ribbon_and_moon(canvas, self.jp, self.jp_box, t, fo, exit_dy, True)
        self._draw_ribbon_and_moon(canvas, self.cn, self.cn_box, t, fo, exit_dy, False)


class ButterflyDreamFarewell(Layer):
    """L12 夢とお別れする夢を / 一场与梦离别的梦 (57.90s ~ 60.81s):
      - 59.833s 原片漫天紫粉荧光蝶爆发瞬间 (恰逢第二个『夢』59.86s 唱响!):
        双语字幕叠入梦幻霓虹紫粉柔光 + 深紫黑抗过曝轮廓 (扛住 60.58s~60.81s 纯白闪光转场!);
      - 句中四个『夢/梦』字周围化生出振翅闪烁的紫粉发光小蝶向上翩跹飞离, 演绎「与梦离别的梦」。
    """
    z = 57

    def __init__(self, jp_line, cn_line, font_jp, font_cn,
                 t_swarm=59.958, jp_dream_idx=(0, 7), cn_dream_idx=(3, 7)):
        self.jp = jp_line
        self.cn = cn_line
        self.t_swarm = t_swarm

        # 预生成抗过曝深紫描边 + 霓虹紫粉发光字形 (保证 60.58s luma=252 白场依然醒目!)
        self.jp_bloom = self._prep_bloom(jp_line, font_jp, synth_bold=0)
        self.cn_bloom = self._prep_bloom(cn_line, font_cn, synth_bold=C.CN_SYNTH_BOLD)

        # 生成从『夢 / 梦』字飞出的发光蝴蝶粒子
        rng = random.Random(1212)
        self.butterflies = []
        sources = []
        for idx in jp_dream_idx:
            if idx < len(jp_line.chars):
                s, _, x, y = jp_line.chars[idx]
                t_st = max(jp_line.t_char[idx] + 0.15, t_swarm - 0.10 if idx == 7 else jp_line.t_char[idx] + 0.25)
                sources.append((x + s.width * 0.5, y + s.height * 0.5, t_st))
        for idx in cn_dream_idx:
            if idx < len(cn_line.chars):
                s, _, x, y = cn_line.chars[idx]
                sources.append((x + s.width * 0.5, y + s.height * 0.5, t_swarm + 0.02))

        for si, (sx, sy, tst) in enumerate(sources):
            for k in range(3):
                st = tst + k * 0.14 + rng.uniform(0.0, 0.08)
                life = rng.uniform(0.95, 1.35)
                vx = rng.uniform(-28.0, 26.0)
                vy = rng.uniform(-52.0, -28.0)
                scale = rng.uniform(0.78, 1.18)
                phase = rng.uniform(0.0, math.pi * 2)
                hue_alt = (si + k) % 2 == 0
                self.butterflies.append((st, life, sx + rng.uniform(-10, 10), sy, vx, vy, scale, phase, hue_alt))

    @staticmethod
    def _prep_bloom(line, font, synth_bold=0):
        out = []
        for i, (s_orig, _, x, y) in enumerate(line.chars):
            ch = line.text[i]
            if ch.isspace():
                continue
            bs, bg = char_sprites(
                ch, font, fill=(255, 244, 255), glow_col=(236, 68, 224),
                glow_r=12, outline=2.8, outline_col=(48, 10, 56),
                shadow_col=(24, 4, 30), shadow_alpha=0.75, synth_bold=synth_bold
            )
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            out.append((i, bs, bg, cx - bs.width * 0.5, cy - bs.height * 0.5))
        return out

    @staticmethod
    def _draw_butterfly(canvas, px, py, scale, flap, alpha, hue_alt):
        """绘制一只 3x 超采样振翅发光小蝴蝶 (flap: 0.25~1.0 模拟双翼开合)。"""
        SS = 3
        dim = 36
        im = Image.new("RGBA", (dim * SS, dim * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = dim * 0.5 * SS
        w_wing = 10.5 * scale * flap * SS
        h_up = 9.0 * scale * SS
        h_dn = 6.2 * scale * SS

        wing_col = (248, 92, 238, int(205 * alpha)) if hue_alt else (165, 115, 255, int(205 * alpha))
        core_col = (255, 232, 255, int(245 * alpha))

        for side in (-1.0, 1.0):
            # 上翼
            d.polygon([
                (c, c),
                (c + side * w_wing, c - h_up),
                (c + side * w_wing * 0.88, c - h_up * 0.12),
            ], fill=wing_col)
            # 下翼
            d.polygon([
                (c, c + 1 * SS),
                (c + side * w_wing * 0.78, c + h_dn * 0.2),
                (c + side * w_wing * 0.58, c + h_dn),
            ], fill=wing_col)
            # 翼心亮斑
            d.polygon([
                (c, c),
                (c + side * w_wing * 0.62, c - h_up * 0.62),
                (c + side * w_wing * 0.52, c - h_up * 0.12),
            ], fill=core_col)

        out = im.resize((dim, dim), Image.Resampling.LANCZOS)
        glow = out.filter(ImageFilter.GaussianBlur(2.2))
        composite_alpha(canvas, glow, px - dim * 0.5, py - dim * 0.5, 0.85)
        composite_alpha(canvas, out, px - dim * 0.5, py - dim * 0.5, 1.0)

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT + 0.25:
            return

        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -6.0 * (u_out ** 1.5)

        # 1) 59.833s 紫粉蝶海霓虹光晕平滑叠加
        if t >= self.t_swarm and fo > 0.005:
            sw_a = ease_out(clamp01((t - self.t_swarm) / 0.22)) * fo
            for line, packs in ((self.jp, self.jp_bloom), (self.cn, self.cn_bloom)):
                for i, bs, bg, rx, ry in packs:
                    a_in = clamp01((t - line.t_char[i]) / line.fade_in)
                    if a_in <= 0.0:
                        continue
                    e_in = ease_out(a_in)
                    dy = (-C.RISE * (1.0 - e_in) if line.mode in ("karaoke", "chars") else 0.0) + exit_dy
                    dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in) if line.mode == "cn_slide" else 0.0
                    composite_alpha(canvas, bg, rx + dx, ry + dy, sw_a * e_in)
                    composite_alpha(canvas, bs, rx + dx, ry + dy, sw_a * e_in * 0.94)

        # 2) 振翅飞离的发光蝴蝶
        for st, life, sx, sy, vx, vy, scale, phase, hue_alt in self.butterflies:
            dt = t - st
            if 0.0 < dt < life:
                u = dt / life
                ba = math.sin(math.pi * u) ** 0.72 * 0.92
                px = sx + vx * dt + math.sin(dt * 6.5 + phase) * 7.5
                py = sy + vy * dt
                flap = 0.28 + 0.72 * abs(math.cos(dt * 17.0 + phase))
                self._draw_butterfly(canvas, px, py, scale * (1.0 - 0.2 * u), flap, ba, hue_alt)


class CageBarsOpen(Layer):
    """L13 貴方の檻から -> L14 見える景色の先を (60.81s ~ 65.34s 双句联动演出!):
      - L13 61.43s 唱响『檻(牢笼)』时, 7 根纤细古典暗金笼栏从上方落下将文字囚于笼中;
      - 延续至 L14 唱响『景色の先を』(64.15s~65.25s 切向远方晨光地平线) 时,
        暗金笼栏向左右两侧缓缓拉开并化作柔和金青光芒消融, 象征视线越出牢笼!
    """
    z = 54

    def __init__(self, jp13, cn13, jp14, cn14, t_bars_in=61.40, t_bars_open=64.10):
        self.t0 = t_bars_in
        self.t_open = t_bars_open
        self.t_end = jp14.end + 0.15
        self.jp_zone = self._union_box(jp13, jp14)
        self.cn_zone = self._union_box(cn13, cn14)

    @staticmethod
    def _union_box(l1, l2):
        xs, x2s, ys, y2s = [], [], [], []
        for ln in (l1, l2):
            for s, _, x, y in ln.chars:
                arr = np.array(s)[..., 3]
                ynz, xnz = np.where(arr > 30)
                if len(xnz) > 0:
                    xs.append(x + xnz.min())
                    x2s.append(x + xnz.max())
                    ys.append(y + ynz.min())
                    y2s.append(y + ynz.max())
        return (min(xs) - 10, max(x2s) + 10, min(ys) - 8, max(y2s) + 8)

    def _draw_cage(self, canvas, box, t, n_bars=7):
        x0, x1, y0, y1 = box
        drop_u = ease_out(clamp01((t - self.t0) / 0.38))
        open_u = ease_in_out(clamp01((t - self.t_open) / 0.95)) if t >= self.t_open else 0.0
        fade_end = 1.0 - clamp01((t - (self.t_end - 0.35)) / 0.35)
        a = drop_u * (1.0 - 0.88 * open_u) * fade_end
        if a <= 0.01:
            return

        cx = (x0 + x1) * 0.5
        w_span = x1 - x0
        h_full = (y1 - y0) * drop_u

        rx0 = max(0, int(x0 - 45))
        rx1 = min(1920, int(x1 + 45))
        ry0 = max(0, int(y0 - 14))
        ry1 = min(1080, int(y1 + 14))
        rw, rh = rx1 - rx0, ry1 - ry0
        if rw <= 8 or rh <= 8:
            return

        SS = 2
        reg = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(reg)

        # 横向顶梁 (开门时向两侧断开退去)
        ty = (y0 + 2 - ry0) * SS
        by = (y0 + 2 + h_full - ry0) * SS
        gap_mid = open_u * w_span * 0.58 * SS
        lx_edge = (x0 - open_u * 26 - rx0) * SS
        rx_edge = (x1 + open_u * 26 - rx0) * SS
        mcx = (cx - rx0) * SS

        col_gold = (212, 174, 98, int(165 * a))
        col_hi = (245, 232, 185, int(195 * a))
        col_sh = (16, 10, 14, int(130 * a))

        if mcx - gap_mid > lx_edge:
            d.line([lx_edge, ty, mcx - gap_mid, ty], fill=col_gold, width=2 * SS)
        if rx_edge > mcx + gap_mid:
            d.line([mcx + gap_mid, ty, rx_edge, ty], fill=col_gold, width=2 * SS)

        # 竖向笼栏: 随 open_u 从中心向左右两侧推开消融!
        for k in range(n_bars):
            frac = k / max(1, n_bars - 1) - 0.5  # -0.5 .. +0.5
            side = -1.0 if frac < 0 else (1.0 if frac > 0 else 0.0)
            spread = side * open_u * (36.0 + abs(frac) * 28.0)
            bx = (cx + frac * w_span + spread - rx0) * SS
            # 正中央那根在敞开时最先化光消失
            bar_a = a * (1.0 - open_u if abs(frac) < 0.05 else 1.0)
            if bar_a <= 0.01:
                continue
            d.line([bx + 2, ty, bx + 2, by], fill=(16, 10, 14, int(120 * bar_a)), width=2 * SS)
            d.line([bx, ty, bx, by], fill=(212, 174, 98, int(155 * bar_a)), width=max(1, int(1.5 * SS)))
            # 栏尖菱形微饰
            d.polygon([(bx, by + 4 * SS), (bx - 2.2 * SS, by), (bx + 2.2 * SS, by)],
                      fill=(245, 228, 175, int(185 * bar_a)))

        reg_1x = reg.resize((rw, rh), Image.Resampling.LANCZOS)
        composite_alpha(canvas, reg_1x, rx0, ry0, 1.0)

    def draw(self, canvas, t):
        if t < self.t0 or t > self.t_end:
            return
        self._draw_cage(canvas, self.jp_zone, t, n_bars=8)
        self._draw_cage(canvas, self.cn_zone, t, n_bars=6)


class WishStarlightAura(Layer):
    """L15 見てほしいのと願うだけ / 望见的景色的后续 (65.34s ~ 68.63s):
      - 66.67s~68.30s 原片右上与中央出现极强星空纯白逆光 (luma=220),
        自动叠入深海夜蓝柔光护盾背板保证字字清晰;
      - 67.40s 唱响『願う(祈愿)』时, 在『願』(idx=7) 与中文『望』(idx=0) 绽开暖金星蓝十字祈愿星芒。
    """
    z = 49

    def __init__(self, jp_line, cn_line, font_jp, jp_wish_idx=7, cn_wish_idx=0, t_wish=67.40):
        self.jp = jp_line
        self.cn = cn_line
        self.t_wish = t_wish

        # 深海星蓝护盾背板精灵 (垫在 z=49, 即主字 z=50 之下, 抵御 67.9s 刺眼纯白光!)
        self.jp_shields = []
        for i, (s_orig, _, x, y) in enumerate(jp_line.chars):
            ch = jp_line.text[i]
            _, g_blue = char_sprites(
                ch, font_jp, fill=(255, 255, 255), glow_col=(28, 86, 178),
                glow_r=13, outline=3.0, outline_col=(18, 32, 68),
                shadow_col=(8, 14, 34), shadow_alpha=0.82
            )
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            self.jp_shields.append((i, g_blue, cx - g_blue.width * 0.5, cy - g_blue.height * 0.5))

        s_jw, _, jx, jy = jp_line.chars[min(jp_wish_idx, len(jp_line.chars) - 1)]
        s_cw, _, cx, cy = cn_line.chars[min(cn_wish_idx, len(cn_line.chars) - 1)]
        self.star_pts = [
            (jx + s_jw.width * 0.5, jy + s_jw.height * 0.5),
            (cx + s_cw.width * 0.5, cy + s_cw.height * 0.5),
        ]

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)

        # 1) 66.60s 起渐入深海星蓝背板护盾
        if t >= 66.708:
            sh_a = ease_out(clamp01((t - 66.708) / 0.30)) * fo
            for i, g_blue, rx, ry in self.jp_shields:
                a_in = ease_out(clamp01((t - self.jp.t_char[i]) / self.jp.fade_in))
                if a_in > 0.01:
                    dy = -C.RISE * (1.0 - a_in) + exit_dy
                    composite_alpha(canvas, g_blue, rx, ry + dy, sh_a * a_in)

        # 2) 67.40s 『願 / 望』十字祈愿星芒 (z=49 衬在字正后方, 光芒四射又不糊笔画!)
        dt = t - self.t_wish
        if 0.0 <= dt <= 0.95:
            u = dt / 0.95
            sa = math.sin(math.pi * u) ** 0.7 * fo
            reach = 0.45 + 0.55 * ease_out(min(1.0, u / 0.35))
            SS = 3
            dim = 116
            sp = Image.new("RGBA", (dim * SS, dim * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(sp)
            c = dim * 0.5 * SS
            r_long = 48.0 * SS * reach
            r_short = 22.0 * SS * reach
            # 柔和光环
            rr = 24.0 * SS * ease_out(u)
            d.ellipse([c - rr, c - rr, c + rr, c + rr],
                      outline=(145, 220, 255, int(165 * sa)), width=2 * SS)
            # 十字长星针 + 斜向短星针
            for ang, r_len, w_l in ((0, r_long, 2.6), (90, r_long * 0.85, 2.6),
                                    (45, r_short, 1.6), (135, r_short, 1.6)):
                rad = math.radians(ang)
                ux, uy = math.cos(rad) * r_len, math.sin(rad) * r_len
                d.line([c - ux, c - uy, c + ux, c + uy],
                       fill=(255, 232, 165, int(215 * sa)), width=max(1, int(w_l * SS)))
            sp_1x = sp.resize((dim, dim), Image.Resampling.LANCZOS)
            for px, py in self.star_pts:
                composite_alpha(canvas, sp_1x, px - dim * 0.5, py - dim * 0.5 + exit_dy, 1.0)


class KeyRepairSweep(Layer):
    """L16 壊れた鍵は直してあるからね / 坏掉的钥匙 已经完整修复 (68.63s ~ 73.39s):
    全片最具叙事闭环的伏笔回收演出!
      1) 句初 68.63s~69.85s: 日文『壊(0)』『鍵(3)』与右下角中文『坏(0)』『钥(3)』『匙(4)』
         以与 B 段 L07 完全一致的斜对角错位断裂状态入场!
      2) 69.85s~71.25s (原片圆桌聚光灯照亮古典金钥匙特写, 且正好唱到『鍵は直して』!):
         一道璀璨暖金金属高光带伴随金星火花从左向右扫过整行双语字幕——
         金光掠过之处, 断裂错位的『壊』『鍵』与『坏…钥匙』两半严丝合缝重新焊合归位,
         并镀上一层温润的鎏金光泽直至句尾!
    """
    z = 56

    def __init__(self, jp_line, cn_line, font_jp, font_cn,
                 jp_break=(0, 3), cn_break=(0, 3, 4),
                 t_sweep_start=69.958, sweep_dur=1.35):
        self.jp = jp_line
        self.cn = cn_line
        self.t_sweep = t_sweep_start
        self.sweep_dur = sweep_dur
        self.jp_break = set(jp_break)
        self.cn_break = set(cn_break)

        # 预切分断裂字两半 + 预生成鎏金修复字形
        self.jp_broken = self._slice_chars(jp_line, self.jp_break)
        self.cn_broken = self._slice_chars(cn_line, self.cn_break)
        self.jp_gold = self._prep_gold(jp_line, font_jp, synth_bold=0)
        self.cn_gold = self._prep_gold(cn_line, font_cn, synth_bold=C.CN_SYNTH_BOLD)

        # 算出每个断裂字被金光扫到的精确时刻, 在焊合完成前隐藏底层原字
        self.jp_heal_t = self._calc_heal_times(jp_line, t_sweep_start, sweep_dur)
        self.cn_heal_t = self._calc_heal_times(cn_line, t_sweep_start + 0.08, sweep_dur)

        def _make_hook(break_set, heal_map):
            def _hook(i, t):
                if i in break_set:
                    th = heal_map[i]
                    if t < th + 0.24:
                        return (0.0, 0.0, 0.0)  # 焊合完成前由本层绘制两半拼合动画
                return (0.0, 0.0, 1.0)
            return _hook

        jp_line.motion_hook = _make_hook(self.jp_break, self.jp_heal_t)
        cn_line.motion_hook = _make_hook(self.cn_break, self.cn_heal_t)

    @staticmethod
    def _calc_heal_times(line, t_sw0, sw_dur):
        xs = [x + s.width * 0.5 for s, _, x, _ in line.chars]
        xmin, xmax = min(xs), max(xs)
        span = max(1.0, xmax - xmin)
        return {i: t_sw0 + ((xs[i] - xmin) / span) * sw_dur * 0.78 for i in range(len(xs))}

    @staticmethod
    def _slice_chars(line, idx_set):
        out = {}
        for i in sorted(idx_set):
            if i >= len(line.chars):
                continue
            s, g, x, y = line.chars[i]
            h, w = s.height, s.width
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            diag = (xx - w * 0.5) * 0.84 + (yy - h * 0.5) * 0.54
            jag = 1.6 * np.sin(yy * 0.45 + i)
            ma = (diag + jag <= 0).astype(np.float32)
            mb = 1.0 - ma
            sa, sb = np.array(s), np.array(s)
            ga, gb = np.array(g), np.array(g)
            sa[..., 3] = (sa[..., 3] * ma).astype(np.uint8)
            sb[..., 3] = (sb[..., 3] * mb).astype(np.uint8)
            ga[..., 3] = (ga[..., 3] * ma).astype(np.uint8)
            gb[..., 3] = (gb[..., 3] * mb).astype(np.uint8)
            out[i] = (Image.fromarray(sa), Image.fromarray(sb),
                      Image.fromarray(ga), Image.fromarray(gb), x, y)
        return out

    @staticmethod
    def _prep_gold(line, font, synth_bold=0):
        packs = []
        for i, (s_orig, _, x, y) in enumerate(line.chars):
            ch = line.text[i]
            if ch.isspace():
                packs.append(None)
                continue
            gs, gg = char_sprites(
                ch, font, fill=(255, 244, 206), glow_col=(236, 172, 48),
                glow_r=11, outline=2.6, outline_col=(48, 28, 10),
                shadow_col=(18, 10, 4), shadow_alpha=0.65, synth_bold=synth_bold
            )
            gh = char_halo(ch, font, halo_col=(255, 224, 128), blur_r=8.0, synth_bold=synth_bold)
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            packs.append((gs, gg, gh, cx - gs.width * 0.5, cy - gs.height * 0.5))
        return packs

    def _draw_line_repair(self, canvas, line, broken_map, gold_packs, heal_map, t, fo, exit_dy):
        for i, (s_orig, _, x, y) in enumerate(line.chars):
            if line.text[i].isspace():
                continue
            a_in = clamp01((t - line.t_char[i]) / line.fade_in)
            if a_in <= 0.0:
                continue
            e_in = ease_out(a_in)
            dy = (-C.RISE * (1.0 - e_in) if line.mode in ("karaoke", "chars") else 0.0) + exit_dy
            dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in) if line.mode == "cn_slide" else 0.0

            th = heal_map[i]
            u_heal = ease_in_out(clamp01((t - th) / 0.24))

            # 1) 断裂字在焊合完成前绘制两半闭合过程 (off 从 2.6px 平滑归零!)
            if i in broken_map and t < th + 0.24:
                sa, sb, ga, gb, bx, by = broken_map[i]
                off = 2.6 * (1.0 - u_heal)
                px, py = bx + dx, by + dy
                composite_alpha(canvas, ga, px - off * 0.9, py - off * 0.7, e_in * fo)
                composite_alpha(canvas, gb, px + off * 1.0, py + off * 1.1, e_in * fo)
                composite_alpha(canvas, sa, px - off * 0.9, py - off * 0.7, e_in * fo)
                composite_alpha(canvas, sb, px + off * 1.0, py + off * 1.1, e_in * fo)

            # 2) 金光扫过当前字时的金属高光脉冲 + 焊合后的温润鎏金覆层
            gp = gold_packs[i]
            if gp is not None and t >= th - 0.06:
                gs, gg, gh, gx, gy = gp
                dt_h = t - th
                # 扫过瞬间闪亮脉冲
                shimmer = math.sin(math.pi * clamp01((dt_h + 0.06) / 0.36))
                # 重点字(壊/鍵/直して 及 残损/钥匙/修好)保留更高鎏金色泽, 其余字保留淡雅暖金余韵
                hi_idx = (5, 6, 7) if (line is self.jp) else (10, 11)
                keep = 0.86 if (i in broken_map or i in hi_idx) else 0.48
                gold_a = max(shimmer * 0.95, u_heal * keep) * e_in * fo
                composite_alpha(canvas, gg, gx + dx, gy + dy, gold_a)
                if shimmer > 0.05:
                    composite_alpha(canvas, gh, gx + dx, gy + dy, shimmer * e_in * fo * 0.92)
                composite_alpha(canvas, gs, gx + dx, gy + dy, gold_a)

                # 断裂字焊合瞬间的金色星火闪烁
                if i in broken_map and 0.0 <= dt_h <= 0.32:
                    sp_a = math.sin(math.pi * (dt_h / 0.32)) * fo
                    dim = 56
                    sp = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
                    d = ImageDraw.Draw(sp)
                    c = dim // 2
                    r = 20 * shimmer
                    d.line([c - r, c, c + r, c], fill=(255, 240, 175, int(235 * sp_a)), width=2)
                    d.line([c, c - r * 0.8, c, c + r * 0.8], fill=(255, 240, 175, int(235 * sp_a)), width=2)
                    sp = sp.filter(ImageFilter.GaussianBlur(0.6))
                    composite_alpha(canvas, sp, x + s_orig.width * 0.5 - c + dx,
                                    y + s_orig.height * 0.5 - c + dy, 1.0)

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        self._draw_line_repair(canvas, self.jp, self.jp_broken, self.jp_gold, self.jp_heal_t, t, fo, exit_dy)
        self._draw_line_repair(canvas, self.cn, self.cn_broken, self.cn_gold, self.cn_heal_t, t, fo, exit_dy)


class RubyRingReach(Layer):
    """L17 ドアノブに手を伸ばして / 所以才会将手伸向把手 (73.39s ~ 76.93s):
      1) 73.80s~74.60s 呼应黑底特写中闪耀六芒红光的红宝石金戒:
         在句首『ドアノブ』点亮一枚精致的暖金指环微弧与红宝石六芒星闪;
      2) 75.22s~76.93s 唱到『手を伸ばして』(少女向空中金戒伸出手、大门开启涌入暖白金光):
         『手を伸ばして』与『将手伸向把手』字距柔和舒展延伸, 并泛起温暖的晨曦金光收束全曲。
    """
    z = 56

    def __init__(self, jp_line, cn_line, font_jp, font_cn, t_glint=73.958, t_reach=75.18):
        self.jp = jp_line
        self.cn = cn_line
        self.t_glint = t_glint
        self.t_reach = t_reach

        # 『手を伸ばして』(idx=5..10) 与中文『伸出手吧』(idx=7..10) 柔和向外舒展延伸
        def _jp_reach(i, t):
            if i >= 5 and t >= t_reach:
                u = ease_out(clamp01((t - t_reach) / 1.45))
                # 右对齐行向左微展或按字序舒展, 同时轻盈上托呼应向上伸出的手!
                stretch = (i - 7.5) * 2.2 * u
                lift = -3.8 * u * ((i - 4) / 6.0)
                return (stretch, lift, 1.0)
            return (0.0, 0.0, 1.0)

        def _cn_reach(i, t):
            if i >= 7 and t >= t_reach:
                u = ease_out(clamp01((t - t_reach) / 1.45))
                stretch = (i - 6) * 2.4 * u
                lift = -3.0 * u * ((i - 6) / 4.0)
                return (stretch, lift, 1.0)
            return (0.0, 0.0, 1.0)

        jp_line.motion_hook = _jp_reach
        cn_line.motion_hook = _cn_reach

        s0, _, x0, y0 = jp_line.chars[1]  # 『ア』附近点缀指环红宝石星芒
        self.gem_pos = (x0 + s0.width * 0.5, y0 + 18)

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        if t > self.jp.end - C.FADE_OUT:
            fo = 1.0 - ease_out(clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT))

        # 73.80s ~ 74.68s 红宝石金戒六芒星闪 (复刻原片 73.85s 戒指特写!)
        dt = t - self.t_glint
        if 0.0 <= dt <= 0.88:
            u = dt / 0.88
            a = math.sin(math.pi * u) ** 0.65 * fo
            rot = u * 18.0
            SS = 3
            dim = 96
            sp = Image.new("RGBA", (dim * SS, dim * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(sp)
            c = dim * 0.5 * SS

            # 纤巧斜置金戒椭圆环
            d.ellipse([c - 18 * SS, c - 6 * SS, c + 14 * SS, c + 8 * SS],
                      outline=(245, 198, 96, int(185 * a)), width=max(1, int(1.6 * SS)))
            # 戒面红宝石六芒星针
            gx, gy = c + 4 * SS, c - 5 * SS
            for k, ang_base in enumerate((0, 60, 120)):
                rad = math.radians(ang_base + rot)
                r_len = (34.0 if k == 0 else 24.0) * SS * (0.5 + 0.5 * math.sin(math.pi * u))
                ux, uy = math.cos(rad) * r_len, math.sin(rad) * r_len
                d.line([gx - ux, gy - uy, gx + ux, gy + uy],
                       fill=(255, 48, 86, int(210 * a)), width=2 * SS)
                d.line([gx - ux * 0.6, gy - uy * 0.6, gx + ux * 0.6, gy + uy * 0.6],
                       fill=(255, 232, 240, int(245 * a)), width=max(1, SS))

            sp_1x = sp.resize((dim, dim), Image.Resampling.LANCZOS)
            composite_alpha(canvas, sp_1x, self.gem_pos[0] - dim * 0.5, self.gem_pos[1] - dim * 0.5, 1.0)


class OutroRedactedCards(Layer):
    """片尾全 7 处画面内嵌文字原生级视觉同化翻译演出 (88.167s ~ 98.854s):
      1) 88.167s ~ 89.729s (1:28): 『これは[甘]くて幸せな[悪]い夢のお話』
         -> 『这是一个[甜]蜜而又幸福的[恶]梦故事』
         复刻原片 12fps 液态水银凝珠化字入场 + 『甜/恶』深绯红点睛 + 89.46s 双帧黑闪同步熄灭 + 89.54s 金画框暖色内嵌!
      2) 92.000s ~ 92.605s (1:32 白底 Quote 卡 #1): 『わたしたちには、[███] しか無いものね』
         -> 『毕竟我们除了 [███] 就什么也没有了呢』(豆沙暗红柔印 + 镜头追焦模糊入场 + 定格红涂抹)
      3) 93.625s ~ 94.062s (1:33.6 白底 Quote 卡 #2): 『きっとわたしは、ずっと [███]』
         -> 『我一定，会一直 [███]』(豆沙暗红柔印 + 追焦模糊 + 浓红涂抹切换细钢笔斜刮痕)
      4) 94.833s ~ 96.040s (1:35 飞书卡): 『そして今日も [███] は夢をみる。』
         -> 『于是今天 [███] 依然做着梦。』(字距同步舒展 + 8fps 定格红油彩涂抹)
      5) 96.042s ~ 96.498s (1:36 白底 Quote 卡 #3): 『[███]のことは誰も知らない』
         -> 『关于 [███] 的事，无人知晓』(豆沙暗红柔印 + 追焦模糊 + 柔化红涂抹)
      6) 97.333s ~ 97.812s (1:37 霓虹故障框卡): 『[酷]く、幸せな[夢]の始まり。』
         -> 『[残酷]、幸福的[梦]之开端。』(青红双色散故障镶边 + 框内居中随镜头右移 + 『残酷/梦』由白渗血染红!)
      7) 98.208s ~ 98.854s (1:38 红玫瑰终幕卡): 『■■■ ─── 「おやすみ」』
         -> 『「晚安」』(绯红柔光象牙白 + 追焦推近 + 98.54s 双帧黑闪同步熄灭 + 98.62s 64% 画框拉远同缩!)
    """
    z = 70

    def __init__(self, font_cn_path):
        self.font_path = font_cn_path
        self.f_128 = ImageFont.truetype(font_cn_path, 35)
        self.f_quote = ImageFont.truetype(font_cn_path, 29)
        self.f_book = ImageFont.truetype(font_cn_path, 38)
        self.f_glitch = ImageFont.truetype(font_cn_path, 34)
        self.f_oya_big = ImageFont.truetype(font_cn_path, 36)
        self.f_oya_sm = ImageFont.truetype(font_cn_path, 23)

        # ---- 1) 1:28 『这是一个甜蜜而又幸福的恶梦故事』预缓存 ----
        self.c128_text = "这是一个甜蜜而又幸福的恶梦故事"
        self.c128_red_idx = {4, 11}  # 『甜』『恶』对应原片『甘』『悪』
        self.c128_chars = []
        self.c128_strip_clean, self.c128_strip_gold = self._build_128_strips()

        # ---- 2, 3, 5) 三张白底豆沙红 Quote 卡底图与涂抹缓存 ----
        # Card 2 (92.00s): 毕竟我们除了 [███] 就什么也没有了呢
        self.q92_base, self.q92_gap = self._build_white_quote_base(
            left_txt="毕竟我们除了", right_txt="就什么也没有了呢", gap_w=138, target_gap_center=1112
        )
        # Card 3 (93.62s): 我一定，会一直 [███]
        self.q93_base, self.q93_gap = self._build_white_quote_base(
            left_txt="我一定，会一直", right_txt="", gap_w=138, target_gap_center=1278
        )
        # Card 5 (96.04s): 关于 [███] 的事，无人知晓
        self.q96_base, self.q96_gap = self._build_white_quote_base(
            left_txt="关于", right_txt="的事，无人知晓", gap_w=104, target_gap_center=962
        )

        # ---- 4) 1:35 飞书卡左右文字精灵缓存 ----
        self.c1_left = [self._book_char(c) for c in "于是今天"]
        self.c1_right = [self._book_char(c) for c in "依然做着梦。"]

        # ---- 6) 1:37 霓虹故障框卡预缓存 (白态与渗血红态双图层, 支持逐帧平滑渗红!) ----
        self.glitch_white, self.glitch_red = self._build_glitch_card_layers()

        # ---- 7) 1:38 『「晚安」』近景与远景双尺度精灵缓存 ----
        self.oya_big = self._build_oyasumi_sprite(self.f_oya_big, w=220, h=76, glow_r=7.0)
        self.oya_sm = self._build_oyasumi_sprite(self.f_oya_sm, w=150, h=54, glow_r=4.8)

    # ------------------------------------------------------------------
    #  预构建辅助方法
    # ------------------------------------------------------------------
    def _build_128_strips(self):
        """构建 1:28 整行高清条带 (常规冷白版 + 89.54s 金画框暖金辉光版) 以及液态变形底图。"""
        txt = self.c128_text
        spacing = 5.5
        advs = [self.f_128.getlength(c) for c in txt]
        tot_w = sum(advs) + spacing * (len(txt) - 1)
        W_box, H_box = int(tot_w + 80), 86
        x0 = (W_box - tot_w) * 0.5
        y0 = 18

        strip_clean = Image.new("RGBA", (W_box, H_box), (0, 0, 0, 0))
        strip_gold = Image.new("RGBA", (W_box, H_box), (0, 0, 0, 0))
        # 液态水银凝珠入场专用的纯色高对比无发光底图 (2x)
        SS = 2
        raw_2x = Image.new("RGBA", (W_box * SS, H_box * SS), (0, 0, 0, 0))
        d_raw = ImageDraw.Draw(raw_2x)
        f_2x = ImageFont.truetype(self.font_path, self.f_128.size * SS)

        cur_x = x0
        for idx, ch in enumerate(txt):
            is_red = idx in self.c128_red_idx
            fill_c = (212, 16, 34) if is_red else (252, 252, 255)
            glow_c = (150, 12, 26) if is_red else (24, 30, 48)
            s, g = char_sprites(
                ch, self.f_128, fill=fill_c, glow_col=glow_c,
                glow_r=6, outline=2.0, outline_col=(18, 12, 18),
                shadow_col=(8, 6, 10), shadow_alpha=0.72, synth_bold=C.CN_SYNTH_BOLD
            )
            # 金画框阶段暖色辉光版本
            glow_gold = (195, 32, 24) if is_red else (218, 132, 46)
            s_gd, g_gd = char_sprites(
                ch, self.f_128, fill=(224, 24, 36) if is_red else (255, 248, 236),
                glow_col=glow_gold, glow_r=7, outline=2.0, outline_col=(36, 16, 10),
                shadow_col=(18, 8, 4), shadow_alpha=0.72, synth_bold=C.CN_SYNTH_BOLD
            )
            w_ch = advs[idx]
            px = cur_x + w_ch * 0.5 - s.width * 0.5
            py = y0
            composite_alpha(strip_clean, g, px, py, 1.0)
            composite_alpha(strip_clean, s, px, py, 1.0)
            composite_alpha(strip_gold, g_gd, px, py, 1.0)
            composite_alpha(strip_gold, s_gd, px, py, 1.0)

            d_raw.text(
                (int(cur_x * SS), int((py + 8) * SS)), ch, font=f_2x,
                fill=(216, 14, 32, 255) if is_red else (255, 255, 255, 255),
                stroke_width=2, stroke_fill=(216, 14, 32, 255) if is_red else (255, 255, 255, 255)
            )
            cur_x += w_ch + spacing

        self.c128_raw_1x = raw_2x.resize((W_box, H_box), Image.Resampling.LANCZOS)
        return strip_clean, strip_gold

    def _build_white_quote_base(self, left_txt, right_txt, gap_w, target_gap_center):
        """构建白底 Quote 卡的豆沙暗红文字层, 并让涂抹区精确对齐原片日文涂抹区的 X 中心!"""
        SS = 2
        f2 = ImageFont.truetype(self.font_path, self.f_quote.size * SS)
        step = 3 * SS
        col = (164, 82, 88, 236)

        w_left = sum(int(f2.getlength(c)) + step for c in left_txt) if left_txt else 0
        w_right = sum(int(f2.getlength(c)) + step for c in right_txt) if right_txt else 0
        pad_x = 24 * SS
        gap_2x = gap_w * SS
        tot_2x = pad_x * 2 + w_left + gap_2x + w_right
        W_box = tot_2x // SS + 8
        H_box = 68

        # 透明底采用与豆沙红同色相的 RGB (避免 PIL 非预乘高斯模糊在白底上渗出暗灰边!)
        im = Image.new("RGBA", (W_box * SS, H_box * SS), (172, 78, 86, 0))
        d = ImageDraw.Draw(im)
        y_txt = 16 * SS

        x_cur = pad_x
        for ch in left_txt:
            d.text((x_cur, y_txt), ch, font=f2, fill=col, stroke_width=1, stroke_fill=col)
            x_cur += int(f2.getlength(ch)) + step

        gap_x0_local = x_cur // SS
        gap_x1_local = (x_cur + gap_2x) // SS

        x_cur += gap_2x
        for ch in right_txt:
            d.text((x_cur, y_txt), ch, font=f2, fill=col, stroke_width=1, stroke_fill=col)
            x_cur += int(f2.getlength(ch)) + step

        out = im.resize((W_box, H_box), Image.Resampling.LANCZOS)
        out = out.filter(ImageFilter.GaussianBlur(0.32))

        local_gap_mid = 0.5 * (gap_x0_local + gap_x1_local)
        canvas_x = int(round(target_gap_center - local_gap_mid))
        return (out, canvas_x), (gap_x0_local, gap_x1_local, W_box, H_box)

    @staticmethod
    def _make_quote_scribble(w_box, h_box, gx0, gx1, seed, heavy=True):
        """生成白底 Quote 卡上的鲜红涂抹块 (透明底用纯鲜红 RGB 防灰边, 斜向右上至左下 '/' 贴合原画手癖)。"""
        SS = 2
        im = Image.new("RGBA", (w_box * SS, h_box * SS), (218, 22, 36, 0))
        sd = ImageDraw.Draw(im)
        rng = random.Random(seed)
        ox0 = (gx0 + 10) * SS
        ox1 = (gx1 - 10) * SS
        y_top = 19 * SS
        y_bot = 47 * SS

        # 底层细密红钢笔往返斜刮线 ('\' 主斜向 + 轻微交叉回锋, 复刻 k=2256 原画柔和红铅笔质感)
        n_fine = 26
        pts = []
        for k in range(n_fine):
            ux = ox0 + (ox1 - ox0) * (k / max(1, n_fine - 1))
            jt1 = rng.uniform(-4.5, 4.5) * SS
            jt2 = rng.uniform(-4.5, 4.5) * SS
            p_top = (ux - 8 * SS + rng.uniform(-2.5, 2.5) * SS, y_top + jt1)
            p_bot = (ux + 8 * SS + rng.uniform(-2.5, 2.5) * SS, y_bot + jt2)
            sd.line([p_top, p_bot], fill=(214, 42, 54, 118 if not heavy else 205), width=max(2, int(1.1 * SS)))
            pts.append(p_top if k % 2 == 0 else p_bot)
        if len(pts) > 2:
            sd.line(pts, fill=(214, 46, 58, 78 if not heavy else 145), width=max(1, int(0.9 * SS)))

        if heavy:
            # 浓烈鲜红马克笔连续往返涂抹块
            zig = []
            for k in range(22):
                ux = ox0 + (ox1 - ox0) * (k / 21.0)
                jt1 = rng.uniform(-4.5, 4.5) * SS
                jt2 = rng.uniform(-4.5, 4.5) * SS
                pa = (ux + 7 * SS, y_top + 1 * SS + jt1)
                pb = (ux - 7 * SS, y_bot - 1 * SS + jt2)
                sd.line([pa, pb], fill=(222, 20, 34, 232), width=int(rng.uniform(5.2, 7.4) * SS))
                zig.extend([pa, pb])
            sd.line(zig, fill=(212, 16, 30, 185), width=int(4.2 * SS))
            im = im.filter(ImageFilter.GaussianBlur(1.5 * SS))
        else:
            im = im.filter(ImageFilter.GaussianBlur(0.85 * SS))

        return im.resize((w_box, h_box), Image.Resampling.LANCZOS)

    def _book_char(self, ch):
        return char_sprites(
            ch, self.f_book, fill=(252, 250, 250), glow_col=(40, 20, 24),
            glow_r=6, outline=1.8, outline_col=(28, 16, 18),
            shadow_col=(10, 6, 8), shadow_alpha=0.68, synth_bold=C.CN_SYNTH_BOLD
        )

    def _build_glitch_card_layers(self):
        """构建 1:37 『残酷、幸福的梦之开端。』青红双色散故障层 (全白初态 + 『残酷/梦』渗血红终态)。"""
        txt = "残酷、幸福的梦之开端。"
        red_idx = {0, 1, 6}  # 『残(0)』『酷(1)』『梦(6)』精确对应原片『酷』『夢』!
        SS = 2
        f2 = ImageFont.truetype(self.font_path, self.f_glitch.size * SS)
        spacing = 6.5 * SS
        advs = [f2.getlength(c) for c in txt]
        tot_w = sum(advs) + spacing * (len(txt) - 1)
        W_box = int(tot_w // SS + 64)
        H_box = 78

        def _render_variant(crimson_keywords):
            im = Image.new("RGBA", (W_box * SS, H_box * SS), (0, 0, 0, 0))
            # 分别绘制青色左偏层、品红右偏层、主字芯层以复刻原片 RGB 故障色散!
            lyr_cyan = Image.new("RGBA", (W_box * SS, H_box * SS), (0, 0, 0, 0))
            lyr_mag = Image.new("RGBA", (W_box * SS, H_box * SS), (0, 0, 0, 0))
            lyr_main = Image.new("RGBA", (W_box * SS, H_box * SS), (0, 0, 0, 0))
            dc = ImageDraw.Draw(lyr_cyan)
            dm = ImageDraw.Draw(lyr_mag)
            d0 = ImageDraw.Draw(lyr_main)

            x_cur = (W_box * SS - tot_w) * 0.5
            y_txt = 18 * SS
            dx_ab = int(2.6 * SS)
            dy_ab = int(0.8 * SS)

            for idx, ch in enumerate(txt):
                is_kw = crimson_keywords and (idx in red_idx)
                c_cyan = (36, 232, 255, 165 if is_kw else 205)
                c_mag = (242, 22, 68, 225 if is_kw else 205)
                c_core = (196, 16, 46, 252) if is_kw else (244, 246, 252, 255)

                dc.text((x_cur - dx_ab, y_txt - dy_ab), ch, font=f2, fill=c_cyan, stroke_width=1, stroke_fill=c_cyan)
                dm.text((x_cur + dx_ab, y_txt + dy_ab), ch, font=f2, fill=c_mag, stroke_width=1, stroke_fill=c_mag)
                d0.text((x_cur, y_txt), ch, font=f2, fill=c_core, stroke_width=1, stroke_fill=c_core)
                x_cur += advs[idx] + spacing

            # 柔和霓虹辉光底衬
            glow = lyr_mag.filter(ImageFilter.GaussianBlur(4.5 * SS))
            im.alpha_composite(glow)
            im.alpha_composite(lyr_cyan.filter(ImageFilter.GaussianBlur(0.45 * SS)))
            im.alpha_composite(lyr_mag.filter(ImageFilter.GaussianBlur(0.45 * SS)))
            im.alpha_composite(lyr_main)
            return im.resize((W_box, H_box), Image.Resampling.LANCZOS)

        return _render_variant(False), _render_variant(True)

    @staticmethod
    def _build_oyasumi_sprite(font, w, h, glow_r=6.5):
        """构建 1:38 『「晚安」』温润象牙白 + 绯红玫瑰柔光精灵。"""
        txt = "「晚安」"
        spacing = max(2.0, font.size * 0.10)
        advs = [font.getlength(c) for c in txt]
        tot_w = sum(advs) + spacing * (len(txt) - 1)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        cur_x = (w - tot_w) * 0.5
        py = (h - font.size) * 0.5 - 4
        for idx, ch in enumerate(txt):
            s, g = char_sprites(
                ch, font, fill=(255, 248, 248), glow_col=(212, 38, 58),
                glow_r=glow_r, outline=max(1.2, font.size * 0.045),
                outline_col=(52, 10, 16), shadow_col=(24, 4, 8),
                shadow_alpha=0.65, synth_bold=C.CN_SYNTH_BOLD
            )
            px = cur_x + advs[idx] * 0.5 - s.width * 0.5
            composite_alpha(im, g, px, py, 0.95)
            composite_alpha(im, s, px, py, 1.0)
            cur_x += advs[idx] + spacing
        return im

    # ------------------------------------------------------------------
    #  各卡片逐帧渲染
    # ------------------------------------------------------------------
    def _draw_card_128(self, canvas, t):
        # 修正时间轴：89.583s ~ 89.667s 对应旧版双帧纯黑频闪切镜。
        if 89.583 <= t < 89.667:
            return

        if t >= 89.667:
            sp = self.c128_strip_gold
            composite_alpha(canvas, sp, 942.0 - sp.width * 0.5, 578.0, 0.96)
            return

        dt = max(0.0, t - 88.292)
        if dt < 0.48:
            # 12fps 阶梯时间 (与原片一拍二完全同频!)
            u_step = clamp01((int(dt * 12.0) / 6.0))
            u_smooth = clamp01(dt / 0.48)
            sx = 0.44 + 0.56 * ease_out(u_step)
            sy = 0.34 + 0.66 * ease_out(u_step)
            W0, H0 = self.c128_raw_1x.size
            nw = max(16, int(round(W0 * sx)))
            nh = max(12, int(round(H0 * sy)))
            scaled = self.c128_raw_1x.resize((nw, nh), Image.Resampling.BILINEAR)

            tmp = Image.new("RGBA", (W0, H0), (255, 255, 255, 0))
            ox_s = (W0 - nw) // 2
            oy_s = (H0 - nh) // 2
            tmp.paste(scaled, (ox_s, oy_s))

            # 前两拍 (k=2116..2119) 叠加液态水银横脊线, 复刻原片从一整条白红水银带断裂成珠的质感!
            if u_step < 0.40:
                td = ImageDraw.Draw(tmp)
                bar_a = int(255 * (1.0 - u_step / 0.40))
                cy_bar = H0 // 2 + 2
                bx0 = ox_s + int(nw * 0.04)
                bx1 = ox_s + int(nw * 0.96)
                if u_step < 0.10:
                    # 第 1 拍: 完整连贯白红液态水银带
                    td.line([(bx0, cy_bar), (bx1, cy_bar)], fill=(252, 252, 255, bar_a), width=9)
                    # 『甜』『恶』两处染上绯红液芯
                    for r_frac in (0.30, 0.77):
                        rx = bx0 + int((bx1 - bx0) * r_frac)
                        td.line([(rx - 22, cy_bar), (rx + 22, cy_bar)], fill=(216, 16, 34, bar_a), width=10)
                else:
                    # 第 2 拍: 断裂为 4 段白红水银长滴 (复刻 k=2118!)
                    segs = [(0.04, 0.18, False), (0.24, 0.36, True), (0.58, 0.79, True), (0.83, 0.96, False)]
                    for f0, f1, is_r in segs:
                        sx0 = bx0 + int((bx1 - bx0) * f0)
                        sx1 = bx0 + int((bx1 - bx0) * f1)
                        col_s = (216, 16, 34, bar_a) if is_r else (252, 252, 255, bar_a)
                        td.line([(sx0, cy_bar), (sx1, cy_bar)], fill=col_s, width=8)

            blur_r = max(0.6, 5.8 * (1.0 - u_step * 0.85))
            blurred = tmp.filter(ImageFilter.GaussianBlur(blur_r))

            # Metaball 液态阈值切割 + 暗色描边包裹水银珠边缘
            arr = np.array(blurred, dtype=np.float32)
            a_boost = 1.85 - 0.85 * u_step
            a_raw = np.clip((arr[..., 3] / 255.0) * a_boost, 0.0, 1.0)
            thresh = 0.34 - 0.14 * u_step
            a_core = np.clip((a_raw - thresh) / 0.12, 0.0, 1.0)
            a_rim = np.clip((a_raw - (thresh - 0.09)) / 0.09, 0.0, 1.0)

            out = np.zeros_like(arr)
            rim_only = np.clip(a_rim - a_core, 0.0, 1.0)
            scale_rgb = np.maximum(arr[..., 3:4] / 255.0, 1e-3)
            core_rgb = np.clip(arr[..., :3] / scale_rgb, 0.0, 255.0)
            out[..., :3] = core_rgb * a_core[..., None] + np.array([18.0, 14.0, 22.0]) * rim_only[..., None]
            out[..., 3] = np.clip(a_rim * 255.0, 0.0, 255.0)
            goo_im = Image.fromarray(out.astype(np.uint8))

            # 尾段 (u_smooth > 0.68) 平滑过渡至超采样清晰成字
            cross = clamp01((u_smooth - 0.68) / 0.32)
            px = 960.0 - W0 * 0.5
            py = 578.0
            if cross < 1.0:
                composite_alpha(canvas, goo_im, px, py, 1.0 - cross * 0.85)
            if cross > 0.0:
                composite_alpha(canvas, self.c128_strip_clean, px, py, cross)
        else:
            sp = self.c128_strip_clean
            composite_alpha(canvas, sp, 960.0 - sp.width * 0.5, 578.0, 1.0)

    def _draw_white_quote(self, canvas, t, t0, base_pack, gap_pack, heavy_fn, y_pos=584):
        base_im, cx = base_pack
        gx0, gx1, wb, hb = gap_pack
        step_f = int((t - t0) * 8.0)
        is_heavy = heavy_fn(t)
        scrib = self._make_quote_scribble(wb, hb, gx0, gx1, seed=int(t0 * 10) + step_f, heavy=is_heavy)

        merged = base_im.copy()
        merged.alpha_composite(scrib)

        # 复刻原片前 3~4 帧光学追焦模糊入场 (GaussianBlur 7.5px -> 0px)
        dt = t - t0
        if dt < 0.145:
            u = clamp01(dt / 0.145)
            r_blur = 7.2 * ((1.0 - u) ** 1.55)
            if r_blur > 0.25:
                merged = merged.filter(ImageFilter.GaussianBlur(r_blur))

        composite_alpha(canvas, merged, cx, y_pos, 0.96)

    def _draw_card_book(self, canvas, t):
        # 94.833s 切入, 字距在 94.83s ~ 95.30s 由紧凑缓缓舒展 (与原片日文动画完全同步!)
        u_open = ease_out(clamp01((t - 94.958) / 0.46))
        a = ease_out(clamp01((t - 94.958) / 0.14))
        spacing = 2.0 + 9.5 * u_open
        gap_w = 108.0 + 28.0 * u_open

        adv_l = [self.f_book.getlength(c) for c in "于是今天"]
        adv_r = [self.f_book.getlength(c) for c in "依然做着梦。"]
        tot_l = sum(adv_l) + spacing * (len(adv_l) - 1)
        tot_r = sum(adv_r) + spacing * (len(adv_r) - 1)
        total_w = tot_l + gap_w + tot_r

        x_start = 960.0 - total_w * 0.5
        y_line = 588.0

        cur_x = x_start
        for idx, (s, g) in enumerate(self.c1_left):
            w_ch = adv_l[idx]
            px = cur_x + w_ch * 0.5 - s.width * 0.5
            composite_alpha(canvas, g, px, y_line, a)
            composite_alpha(canvas, s, px, y_line, a)
            cur_x += w_ch + spacing

        gap_x0 = cur_x + 4.0
        cur_x += gap_w
        for idx, (s, g) in enumerate(self.c1_right):
            w_ch = adv_r[idx]
            px = cur_x + w_ch * 0.5 - s.width * 0.5
            composite_alpha(canvas, g, px, y_line, a)
            composite_alpha(canvas, s, px, y_line, a)
            cur_x += w_ch + spacing

        SS = 3
        pw = int(gap_w + 16)
        ph = 76
        patch = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
        pd = ImageDraw.Draw(patch)
        step_frame = int((t - 94.958) * 8)
        rng = random.Random(955 + step_frame)
        ox0 = 18 * SS
        ox1 = (pw - 18) * SS
        oy_top = 19 * SS
        oy_bot = 53 * SS

        n_fine = 18
        for k in range(n_fine):
            fx = ox0 + (ox1 - ox0) * (k / max(1, n_fine - 1))
            jt1 = rng.uniform(-3.8, 3.8) * SS
            jt2 = rng.uniform(-3.8, 3.8) * SS
            pd.line([fx - 7 * SS, oy_top + jt1, fx + 7 * SS, oy_bot + jt2],
                    fill=(198, 18, 30, int(205 * a)), width=max(2, int(1.3 * SS)))

        is_heavy = (step_frame % 3 != 1) or (t >= 95.792)
        heavy_alpha = 246 if is_heavy else 95
        rng2 = random.Random(980 + step_frame)
        for k in range(20):
            hx = ox0 + (ox1 - ox0) * (k / 19.0)
            jt1 = rng2.uniform(-4.8, 4.8) * SS
            jt2 = rng2.uniform(-4.8, 4.8) * SS
            w_stroke = int(rng2.uniform(4.8, 7.4) * SS)
            col_r = (214, 14, 28, int(heavy_alpha * a)) if k % 3 != 0 else (178, 8, 20, int(heavy_alpha * a))
            pd.line([hx - 7.5 * SS, oy_top + 2 * SS + jt1,
                     hx + 7.5 * SS, oy_bot - 2 * SS + jt2],
                    fill=col_r, width=w_stroke)

        p1 = patch.resize((pw, ph), Image.Resampling.LANCZOS)
        composite_alpha(canvas, p1, gap_x0 - 6, y_line + 2, 1.0)

    def _draw_card_glitch(self, canvas, t):
        # 修正时间轴：97.458s ~ 97.958s 对应旧版霓虹故障框卡。
        u = clamp01((t - 97.458) / 0.458)
        bleed = ease_out(clamp01((t - 97.500) / 0.38))
        # 轻微水平故障微抖 (±1px)
        step_g = int((t - 97.458) * 24)
        jx = (-1.0 if step_g in (2, 7) else (1.2 if step_g in (4, 9) else 0.0))
        cx = 918.0 + 20.0 * u + jx
        px = cx - self.glitch_white.width * 0.5
        py = 562.0  # 稳稳嵌在霓虹底框 (y=636) 上方的净空区内!

        if bleed < 0.999:
            composite_alpha(canvas, self.glitch_white, px, py, 1.0 - bleed)
        if bleed > 0.001:
            composite_alpha(canvas, self.glitch_red, px, py, bleed)

    def _draw_card_oyasumi(self, canvas, t):
        # 修正时间轴：98.667s ~ 98.750s 对应旧版双帧纯黑频闪切镜。
        if 98.667 <= t < 98.750:
            return

        if t >= 98.750:
            sp = self.oya_sm
            composite_alpha(canvas, sp, 1105.0 - sp.width * 0.5, 566.0, 0.96)
            return

        dt = t - 98.333
        sp = self.oya_big
        u_focus = clamp01(dt / 0.084)
        cx = 1184.0 + 34.0 * ease_out(u_focus)
        if u_focus < 0.99:
            r_blur = 8.2 * ((1.0 - u_focus) ** 1.35)
            sp = sp.filter(ImageFilter.GaussianBlur(max(0.3, r_blur)))
        composite_alpha(canvas, sp, cx - sp.width * 0.5, 580.0, 0.98)

    def draw(self, canvas, t):
        if 88.292 <= t < 89.875:
            self._draw_card_128(canvas, t)
        elif 92.125 <= t < 92.750:
            self._draw_white_quote(
                canvas, t, 92.125, self.q92_base, self.q92_gap,
                heavy_fn=lambda ts: ts >= 92.250, y_pos=582
            )
        elif 93.750 <= t < 94.208:
            self._draw_white_quote(
                canvas, t, 93.750, self.q93_base, self.q93_gap,
                heavy_fn=lambda ts: 93.917 <= ts < 94.083, y_pos=582
            )
        elif 94.958 <= t < 96.167:
            self._draw_card_book(canvas, t)
        elif 96.167 <= t < 96.625:
            self._draw_white_quote(
                canvas, t, 96.167, self.q96_base, self.q96_gap,
                heavy_fn=lambda ts: True, y_pos=584
            )
        elif 97.458 <= t < 97.958:
            self._draw_card_glitch(canvas, t)
        elif 98.333 <= t < 99.000:
            self._draw_card_oyasumi(canvas, t)
