# -*- coding: utf-8 -*-
"""FD OP 序幕演出 (L00~L02, 0:00.68~0:17.37) + 间奏 0:25 纯白走廊双行题记原生级内嵌:
  - L00 SpotlightPiercingDarkness : 幽暗中斜向刺入的暖金体积追光束 + 浮金微尘 + 『光』字星芒
  - L01 GrimoirePageTurn          : 黄金魔导书柔棕护航 + 『振り返る/蓦然回首』翻页微风金箔残影
  - L02 SapphireDreamTrace        : 『夢の跡/梦之残痕』电光沧蓝紫幻影 + 16.36s 标题白幕无黑边过曝消融
  - CorridorEpigraph (24.65s~30.22s): 原生级双行内嵌『没有不会醒来的梦。/ 然而，人也绝不会不再做梦。』
                                      (炭黑金文 + 双『梦』放大染血红 + 左起显影 + 29.32s 3D 走廊纵深推进失焦消散!)
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out, composite_alpha,
    char_sprites, char_halo, soft_cloud,
)


# =====================================================================
#  [L00] 幽暗暖金体积光束刺入 + 浮金微尘 (0:00.68 ~ 0:06.29)
# =====================================================================
class SpotlightPiercingDarkness(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_ray = 1.85       # 『差し込んだ』起唱, 暖金光束刺破黑暗!
        self.t_hikari = 4.26    # 『光』长音点亮时刻!

        self.jp_gold = self._prep_halos(jp_line, font_jp, (255, 222, 128), 0)
        self.cn_gold = self._prep_halos(cn_line, font_cn, (255, 222, 128), C.CN_SYNTH_BOLD)

        rng = random.Random(68)
        self.motes = []
        for k in range(24):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(2.05, 5.10)
            life = rng.uniform(1.05, 1.75)
            x0 = rng.uniform(ln.bbox_x0 + (ln.bbox_x1 - ln.bbox_x0) * 0.32, ln.bbox_x1 - 18)
            y0 = ln.y + rng.uniform(6.0, 40.0)
            vx = rng.uniform(6.0, 22.0)
            vy = rng.uniform(-22.0, -8.0)
            rad = rng.uniform(1.8, 3.6)
            ph = rng.uniform(0.0, math.tau)
            self.motes.append((tb, life, x0, y0, vx, vy, rad, ph))

    @staticmethod
    def _prep_halos(line, font, col, sb):
        out = {}
        for i, (_, _, _, _, _, cx, cy, is_sp) in enumerate(line.chars):
            if not is_sp:
                h = char_halo(line.text[i], font, halo_col=col, blur_r=9.0, synth_bold=sb)
                out[i] = (h, cx - h.width * 0.5, cy - h.height * 0.5)
        return out

    @staticmethod
    def _draw_beam_cone(canvas: Image.Image, target_x: float, target_y: float,
                        from_top: bool, progress: float, alpha_mul: float):
        """绘制边界柔和归零的斜向暖金体积追光束。"""
        w, h = 420, 150
        im = Image.new("RGBA", (w, h), (255, 218, 126, 0))
        d = ImageDraw.Draw(im)
        reach = ease_out(progress)
        a_core = int(78 * alpha_mul * reach)
        if a_core <= 2:
            return
        if from_top:
            pts = [(36, 0), (128, 0), (int(128 + 260 * reach), h), (int(36 + 110 * reach), h)]
        else:
            pts = [(int(w - 130 - 220 * reach), 0), (int(w - 40 - 90 * reach), 0), (w - 30, h), (w - 120, h)]
        d.polygon(pts, fill=(255, 220, 128, a_core))
        im = im.filter(ImageFilter.GaussianBlur(22.0))
        composite_alpha(canvas, im, target_x - w * 0.5, target_y - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.t_ray or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        u_ray = clamp01((t - self.t_ray) / 1.45)
        if fo * u_ray <= 0.02:
            return
        # 斜向金光刺入『ひとすじの光』与『一缕微光』
        self._draw_beam_cone(canvas, self.jp.bbox_x1 - 150, self.jp.y + 18, True, u_ray, fo)
        self._draw_beam_cone(canvas, self.cn.bbox_x1 - 140, self.cn.y + 22, False, u_ray, fo * 0.90)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_ray or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.01:
            return

        # 1) 『ひとすじの光 (idx>=10) / 一缕微光 (idx>=11)』暖金圣辉点亮 + 『光』十字星芒
        if self.jp.exit_progress(t) < 0.28:
            w_g = ease_out(clamp01((t - 3.10) / 0.85)) * fo * 0.72
            if w_g > 0.02:
                for line, g_map, idx0 in ((self.jp, self.jp_gold, 10), (self.cn, self.cn_gold, 11)):
                    for i in range(idx0, len(line.chars)):
                        s_core, _, _, px_c, py_c, cx, cy, is_sp = line.chars[i]
                        if is_sp or i not in g_map:
                            continue
                        dx, dy, a_ch, _ = line.char_state(i, t)
                        if a_ch > 0.04:
                            gh, gx, gy = g_map[i]
                            boost = 1.28 if (i == len(line.chars) - 1 and t >= self.t_hikari) else 0.85
                            composite_alpha(canvas, gh, gx + dx, gy + dy, clamp01(a_ch * w_g * boost))
                            composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

                            # 句末『光』字绽放纤细暖金十字星芒
                            if i == len(line.chars) - 1 and t >= self.t_hikari:
                                u_st = math.sin(math.pi * clamp01((t - self.t_hikari) / 1.75)) * fo
                                if u_st > 0.06:
                                    st = Image.new("RGBA", (44, 44), (255, 236, 168, 0))
                                    sd = ImageDraw.Draw(st)
                                    al = int(220 * u_st)
                                    sd.line([(22, 2), (22, 42)], fill=(255, 248, 210, al), width=2)
                                    sd.line([(2, 22), (42, 22)], fill=(255, 232, 152, al), width=2)
                                    sd.ellipse([18, 18, 26, 26], fill=(255, 255, 240, al))
                                    composite_alpha(canvas, st, cx + dx + 10 - 22, cy + dy - 14 - 22, 1.0)

        # 2) 光束中漂浮的暖金尘埃粒子
        m_im = Image.new("RGBA", (canvas.width, canvas.height), (255, 228, 148, 0))
        md = ImageDraw.Draw(m_im)
        has_m = False
        for tb, life, x0, y0, vx, vy, rad, ph in self.motes:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                ma = math.sin(math.pi * u) * fo
                if ma > 0.03:
                    has_m = True
                    px = x0 + vx * age + 4.5 * math.sin(age * 4.0 + ph)
                    py = y0 + vy * age
                    r2 = rad * 2.1
                    md.ellipse([px - r2, py - r2, px + r2, py + r2], fill=(255, 216, 118, int(82 * ma)))
                    md.ellipse([px - rad * 0.7, py - rad * 0.7, px + rad * 0.7, py + rad * 0.7],
                               fill=(255, 252, 230, int(228 * ma)))
        if has_m:
            canvas.alpha_composite(m_im)


# =====================================================================
#  [L01] 黄金魔导书翻页微风 + 金箔余晖 (0:08.62 ~ 0:12.90)
# =====================================================================
class GrimoirePageTurn(Layer):
    z = 34

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_turn = 10.05     # 『振り返る / 蓦然回首』翻页轻拂时刻

        # 8.8s~12.45s 黄金古书高亮底的温润深棕衬云 (零截断边缘)
        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(62, 28, 12), alpha=78)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(62, 28, 12), alpha=78)

        # 『振り返る』(idx 5..8) 与『蓦然回首』(idx 6..9) 书页轻翻水平回旋韵律
        def _make_turn_hook(i0: int, i1: int):
            def _hook(i: int, t: float):
                if i0 <= i <= i1:
                    dt = t - (self.t_turn + (i - i0) * 0.055)
                    if 0.0 <= dt <= 0.56:
                        u = dt / 0.56
                        dx = -8.5 * math.sin(math.pi * u)
                        dy = -2.8 * math.sin(math.pi * u)
                        return dx, dy, 1.0
                return 0.0, 0.0, 1.0
            return _hook

        jp_line.motion_hook = _make_turn_hook(5, 8)
        cn_line.motion_hook = _make_turn_hook(6, 9)

        rng = random.Random(862)
        self.leafs = []
        for k in range(18):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(9.10, 11.75)
            life = rng.uniform(0.85, 1.40)
            x0 = rng.uniform(ln.bbox_x0 + 30, ln.bbox_x1 - 30)
            y0 = ln.y + rng.uniform(8.0, 38.0)
            vx = rng.uniform(-38.0, -14.0)
            vy = rng.uniform(-14.0, 12.0)
            sz = rng.uniform(2.8, 5.2)
            rot0 = rng.uniform(0.0, math.tau)
            self.leafs.append((tb, life, x0, y0, vx, vy, sz, rot0))

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        # 12.40s 原片古书暗化为黑底 Purple Logo, 衬云同步柔和收起
        w_gold = ease_out(clamp01((t - self.start) / 0.35)) * (1.0 - ease_in_out(clamp01((t - 13.083) / 0.35))) * fo
        if w_gold > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_gold)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_gold)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        im = Image.new("RGBA", (canvas.width, canvas.height), (255, 224, 132, 0))
        d = ImageDraw.Draw(im)
        has_l = False
        for tb, life, x0, y0, vx, vy, sz, rot0 in self.leafs:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                la = math.sin(math.pi * u) * fo
                if la > 0.03:
                    has_l = True
                    px = x0 + vx * age
                    py = y0 + vy * age + 4.5 * math.sin(age * 5.2 + rot0)
                    ang = rot0 + age * 4.5
                    ca, sa = math.cos(ang), math.sin(ang)
                    rx, ry = sz * 1.3, sz * 0.55
                    d.polygon([
                        (px + ca * rx, py + sa * rx),
                        (px - sa * ry, py + ca * ry),
                        (px - ca * rx, py - sa * rx),
                        (px + sa * ry, py - ca * ry),
                    ], fill=(255, 232, 152, int(210 * la)))
        if has_l:
            canvas.alpha_composite(im)


# =====================================================================
#  [L02] 电光沧蓝紫『夢の跡』幻影 + 16.36s 纯白标题卡无黑边过曝消融!
# =====================================================================
class SapphireDreamTrace(Layer):
    z = 36

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.t_white = 17.167    # 修正时间轴：对应旧版 16.32s 的同一视频帧
        self.white_end = 17.667  # 赶在标题笔画铺开前化作纯白圣光无痕消融!

        jp_line.suppress_spans.append((self.t_white, jp_line.end + 0.1))
        cn_line.suppress_spans.append((self.t_white, cn_line.end + 0.1))

        self.jp_blue = SpotlightPiercingDarkness._prep_halos(jp_line, font_jp, (92, 156, 255), 0)
        self.cn_blue = SpotlightPiercingDarkness._prep_halos(cn_line, font_cn, (156, 118, 255), C.CN_SYNTH_BOLD)

        self.jp_white = self._prep_pure_white(jp_line, font_jp, 0)
        self.cn_white = self._prep_pure_white(cn_line, font_cn, C.CN_SYNTH_BOLD)

    @staticmethod
    def _prep_pure_white(line, font, sb):
        out = []
        for i, (_, _, _, _, _, cx, cy, is_sp) in enumerate(line.chars):
            if is_sp:
                out.append(None)
                continue
            sw, gw = char_sprites(
                line.text[i], font,
                fill_top=(255, 255, 255), fill_bot=(255, 246, 252),
                glow_col=(255, 210, 232), glow_r=11.0,
                outline=1.2, outline_col=(255, 242, 248),
                shadow_col=(255, 255, 255), shadow_alpha=0.0,
                synth_bold=sb,
            )
            out.append((sw, gw, cx - sw.width * 0.5, cy - sw.height * 0.5))
        return out

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.white_end:
            return

        # 1) 16.32s ~ 16.82s: 无黑边纯白标题光晕消融!
        if t >= self.t_white:
            u = clamp01((t - self.t_white) / (self.white_end - self.t_white))
            cross = clamp01(u / 0.26)
            fade_w = 1.0 - ease_in_out(clamp01((u - 0.12) / 0.88))
            if cross < 0.99:
                self.jp.render_to_buffer(canvas, self.t_white - 0.01, 0, 0)
                self.cn.render_to_buffer(canvas, self.t_white - 0.01, 0, 0)

            for line, packs in ((self.jp, self.jp_white), (self.cn, self.cn_white)):
                bx0 = max(0, line.bbox_x0 - 28)
                by0 = max(0, line.bbox_y0 - 20)
                bx1 = min(canvas.width, line.bbox_x1 + 28)
                by1 = min(canvas.height, line.bbox_y1 + 20)
                w_buf = Image.new("RGBA", (bx1 - bx0, by1 - by0), (255, 255, 255, 0))
                for p in packs:
                    if p is not None:
                        sw, gw, px, py = p
                        composite_alpha(w_buf, gw, px - bx0, py - by0, fade_w)
                        composite_alpha(w_buf, sw, px - bx0, py - by0, fade_w)
                if u > 0.15:
                    w_buf = w_buf.filter(ImageFilter.GaussianBlur(5.8 * ((u - 0.15) / 0.85)))
                composite_alpha(canvas, w_buf, bx0, by0, clamp01(cross * 1.15))
            return

        # 2) 13.90s ~ 16.30s: 『夢の跡 (idx>=5) / 梦之残痕 (idx>=6)』沧蓝紫电光幻影残像!
        if t >= 13.88:
            w_tr = ease_out(clamp01((t - 13.88) / 0.45)) * 0.72
            drift = 7.5 + 3.5 * math.sin((t - 13.88) * 5.2)
            for line, b_map, idx0 in ((self.jp, self.jp_blue, 5), (self.cn, self.cn_blue, 6)):
                for i in range(idx0, len(line.chars)):
                    s_core, _, _, px_c, py_c, _, _, is_sp = line.chars[i]
                    if is_sp or i not in b_map:
                        continue
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        bh, bx, by = b_map[i]
                        # 偏移幽蓝梦影 + 本体光晕
                        composite_alpha(canvas, s_core, px_c + dx + drift, py_c + dy - 3.5, a_ch * w_tr * 0.36)
                        composite_alpha(canvas, bh, bx + dx, by + dy, a_ch * w_tr * 0.85)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)


# =====================================================================
#  [间奏 0:25 纯白走廊题记] 原生级内嵌:
#    『没有不会醒来的梦。』
#    『　然而，人也绝不会不再做梦。』
#    精准对齐原片『覚めない夢は無い。/ けれど、夢を見なくなる事もない。』:
#      - 炭黑浓墨金文体 (44, 40, 39) + 两个『梦』字放大染鲜血红 (198, 6, 12)
#      - 阶梯左缩进 (x=206 -> x=332) 严丝合缝镜像原片双行缩进
#      - 左起逐字柔焦显影 (24.68s~26.22s & 26.58s~28.45s)
#      - 29.32s~30.22s 随走廊镜头冲向木门执行 (960, 540) 3D 透视推进放大 + 景深失焦消隐!
# =====================================================================
class CorridorEpigraph(Layer):
    z = 40

    def __init__(self):
        # 以下锚点已按修正后的视频时间轴逐帧迁移（旧值 24.65/29.32/30.24）。
        self.t_start = 25.500
        self.t_zoom = 30.167
        self.t_end = 31.083

        self.line1_spec = ("没有不会醒来的梦。", 206, 718, 25.542, 27.083)
        self.line2_spec = ("然而，人也绝不会不再做梦。", 332, 804, 27.417, 29.292)

        self.chars1 = self._prebake_line(self.line1_spec[0], self.line1_spec[1], self.line1_spec[2])
        self.chars2 = self._prebake_line(self.line2_spec[0], self.line2_spec[1], self.line2_spec[2])

    @staticmethod
    def _prebake_line(text: str, x_start: float, y_center: float):
        """3x 超采样预烘每个字符的清晰精灵与柔焦雾化精灵, 零黑边纯正炭墨与血红墨色。"""
        SS = 3
        scale_y = 1.15
        sz_norm = 45
        sz_meng = 59
        spacing = 11

        f_norm = ImageFont.truetype(C.FONT_PATH_CN, sz_norm * SS)
        f_meng = ImageFont.truetype(C.FONT_PATH_CN, sz_meng * SS)

        ink_norm = (44, 40, 39)
        ink_meng = (198, 6, 12)
        glow_meng = (224, 26, 36)

        cur_x = float(x_start)
        items = []
        for ch in text:
            is_meng = (ch == "梦")
            f = f_meng if is_meng else f_norm
            adv = f.getlength(ch) / SS
            bb = f.getbbox(ch)
            bw3 = max(6, (bb[2] - bb[0]) if bb else int(adv * SS))
            bh3 = max(6, (bb[3] - bb[1]) if bb else f.size)
            pad3 = 22 * SS
            W3, H3 = bw3 + pad3 * 2, bh3 + pad3 * 2
            ox = pad3 - (bb[0] if bb else 0)
            oy = pad3 - (bb[1] if bb else 0)

            col = ink_meng if is_meng else ink_norm
            im3 = Image.new("RGBA", (W3, H3), (*col, 0))
            d3 = ImageDraw.Draw(im3)
            if is_meng:
                gl3 = Image.new("RGBA", (W3, H3), (*glow_meng, 0))
                dg3 = ImageDraw.Draw(gl3)
                dg3.text((ox, oy), ch, font=f, fill=(*glow_meng, 125), stroke_width=4, stroke_fill=(*glow_meng, 105))
                gl3 = gl3.filter(ImageFilter.GaussianBlur(3.6 * SS))
                im3.alpha_composite(gl3)
                d3.text((ox, oy), ch, font=f, fill=(*col, 255), stroke_width=2, stroke_fill=(*col, 245))
            else:
                d3.text((ox, oy), ch, font=f, fill=(*col, 248), stroke_width=2, stroke_fill=(*col, 220))

            W1 = max(4, int(round(W3 / SS)))
            H1 = max(4, int(round((H3 / SS) * scale_y)))
            sp_sharp = im3.resize((W1, H1), Image.Resampling.LANCZOS)
            sp_soft = sp_sharp.filter(ImageFilter.GaussianBlur(3.8))

            cx = cur_x + adv * 0.5
            cy = y_center - (3.0 if is_meng else 0.0)
            items.append((sp_sharp, sp_soft, cx, cy))
            cur_x += adv + spacing
        return items

    def _draw_reveal_into(self, dst: Image.Image, ox: int, oy: int, chars, t: float, t0: float, t1: float):
        if t < t0:
            return
        n = max(1, len(chars))
        span = max(0.2, (t1 - t0) - 0.34)
        for i, (sp_sharp, sp_soft, cx, cy) in enumerate(chars):
            tc = t0 + (i / max(1, n - 1)) * span
            u = clamp01((t - tc) / 0.36)
            if u <= 0.005:
                continue
            a = ease_out(u)
            dx = 6.0 * (1.0 - a)
            if u < 0.72:
                w_soft = 1.0 - (u / 0.72)
                composite_alpha(dst, sp_soft, cx - sp_soft.width * 0.5 + dx - ox, cy - sp_soft.height * 0.5 - oy, a * w_soft)
                composite_alpha(dst, sp_sharp, cx - sp_sharp.width * 0.5 + dx - ox, cy - sp_sharp.height * 0.5 - oy, a * (1.0 - w_soft * 0.75))
            else:
                composite_alpha(dst, sp_sharp, cx - sp_sharp.width * 0.5 - ox, cy - sp_sharp.height * 0.5 - oy, a)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_start or t > self.t_end:
            return

        # 常态显影区间 (24.65s ~ 29.32s): 直接高清合成至主画布
        if t < self.t_zoom:
            self._draw_reveal_into(canvas, 0, 0, self.chars1, t, self.line1_spec[3], self.line1_spec[4])
            self._draw_reveal_into(canvas, 0, 0, self.chars2, t, self.line2_spec[3], self.line2_spec[4])
            return

        # 29.32s ~ 30.24s: 走廊镜头冲向双扇木门! 以消失点 (960, 540) 为锚执行 3D 透视推进放大 + 景深失焦模糊!
        u_z = clamp01((t - self.t_zoom) / (self.t_end - self.t_zoom))
        scale = 1.0 + 0.52 * (u_z ** 1.55)
        fade = (1.0 - ease_in_out(u_z)) ** 1.15
        if fade <= 0.008:
            return

        bx0, by0, bx1, by1 = 150, 660, 1780, 868
        bw, bh = bx1 - bx0, by1 - by0
        sub = Image.new("RGBA", (bw, bh), (44, 40, 39, 0))
        self._draw_reveal_into(sub, bx0, by0, self.chars1, self.t_zoom, self.line1_spec[3], self.line1_spec[4])
        self._draw_reveal_into(sub, bx0, by0, self.chars2, self.t_zoom, self.line2_spec[3], self.line2_spec[4])

        nw = max(16, int(round(bw * scale)))
        nh = max(16, int(round(bh * scale)))
        zoomed = sub.resize((nw, nh), Image.Resampling.BILINEAR)
        blur_r = 12.5 * (u_z ** 1.25)
        if blur_r > 0.35:
            zoomed = zoomed.filter(ImageFilter.GaussianBlur(blur_r))

        # 围绕全屏走廊消失点 (960, 540) 放射状向外推进偏移!
        vx, vy = 960.0, 540.0
        dest_x = vx + (bx0 - vx) * scale
        dest_y = vy + (by0 - vy) * scale
        composite_alpha(canvas, zoomed, dest_x, dest_y, fade)
