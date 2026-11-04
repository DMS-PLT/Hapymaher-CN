# -*- coding: utf-8 -*-
"""FD OP 副歌高潮演出层 (L11~L19, 1:06.68 ~ 1:42.80):
  - L11 ThornsAndBloodTrail   : 『いばらみち かき分けて』荆棘向两侧拨开 + 『流した血の色』字底凝结晶莹血珠垂落!
  - L12 BurningChestRose      : 『薔薇』背后层叠哥特红蔷薇绽放 + 『紅く熱く』赤金灼热火种升腾!
  - L13 SlashScarsMelt        : 『傷つけて/傷ついて』银红交叉剑刃寒光斩痕 + 『溶け合ってゆくの』绯红与暖金双色光晕交融!
  - L14 EcstasyStarlightRipples: 契合有子沧蓝星海涟漪 — 『悦楽/欢愉』透视同心星水波纹扩散 + 十字星芒闪烁!
  - L15 YandereLoveKillFlash  : 『愛してる×2』双重心跳绯红冲击波 + 85.75s 红底白影帧同步『殺したいほどに』病娇猩红斩裂闪光!
  - L16 HeartLockboxCage      : 契合 3D 红白棋盘箱庭 — 四向哥特金红花丝锁匣合拢扣死『閉じ込めたい/锁进心底的匣中』!
  - L17 ClosedRoomWarmWorld   : 暖阳窗棂斜射光束 + 虹彩柔焦光斑笼罩『世界の全てに/便是世界的全部』!
  - L18 EternalGoldenStream   : 暖金流沙星尘横贯长河 + 『永久へ/迈向永恒』香槟圣辉!
  - L19 EncoreVelvetCurtain   : 避让左下角原画署名 + 『開かれる 舞台』歌剧金红天鹅绒帷幕向两侧优雅拉开与舞台脚光谢幕!
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out, composite_alpha,
    char_sprites, char_halo, soft_cloud,
)


def _prep_idx_halos(line, font, idx_range, col, blur_r=9.0, sb=0):
    out = {}
    for i in idx_range:
        if 0 <= i < len(line.chars) and not line.chars[i][7]:
            _, _, _, _, _, cx, cy, _ = line.chars[i]
            h = char_halo(line.text[i], font, halo_col=col, blur_r=blur_r, synth_bold=sb)
            out[i] = (h, cx - h.width * 0.5, cy - h.height * 0.5)
    return out


def _draw_star4(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, col_rgba):
    r_in = r * 0.24
    pts = [
        (cx, cy - r), (cx + r_in, cy - r_in),
        (cx + r, cy), (cx + r_in, cy + r_in),
        (cx, cy + r), (cx - r_in, cy + r_in),
        (cx - r, cy), (cx - r_in, cy - r_in),
    ]
    d.polygon(pts, fill=col_rgba)


# =====================================================================
#  [L11] 拨开荆棘之路 + 垂落晶莹血珠 (66.68s ~ 71.06s)
# =====================================================================
class ThornsAndBloodTrail(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_part = 67.92    # 『かき分けて』拨开荆棘
        self.t_blood = 69.25   # 『流した血の色』鲜血凝珠垂落

        # 68.70s 起画面切入白底蔷薇雾与舞亚特写, 启用无框解析酒红柔云护航可读性
        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(76, 14, 34), alpha=72)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(76, 14, 34), alpha=72)

        # 『流した血の色 (12..17) / 流淌出的血色 (7..12)』深绯血色辉光与猩红字芯覆写
        self.jp_blood = self._prep_blood_chars(jp_line, font_jp, range(12, 18), 0)
        self.cn_blood = self._prep_blood_chars(cn_line, font_cn, range(7, 13), C.CN_SYNTH_BOLD)

        # 从『流した血の色 / 流淌出的血色』笔画底端凝结垂落的血珠池
        rng = random.Random(6668)
        self.blood_drops = []
        for line, idxs in ((jp_line, range(12, 18)), (cn_line, range(7, 13))):
            for i in idxs:
                if i < len(line.chars) and not line.chars[i][7]:
                    _, _, _, _, _, cx, cy, _ = line.chars[i]
                    for k in range(2):
                        tb = 69.32 + (i - min(idxs)) * 0.14 + k * 0.42 + rng.uniform(-0.04, 0.06)
                        life = rng.uniform(0.75, 1.15)
                        x0 = cx + rng.uniform(-10.0, 10.0)
                        y0 = cy + line.font.size * 0.34
                        rad = rng.uniform(2.6, 4.2)
                        self.blood_drops.append((tb, life, x0, y0, rad))

    @staticmethod
    def _prep_blood_chars(line, font, idx_range, sb):
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, _, _, _, _, cx, cy, _ = line.chars[i]
                sb_sp, gb_sp = char_sprites(
                    line.text[i], font,
                    fill_top=(255, 226, 232), fill_bot=(232, 34, 62),
                    glow_col=(228, 12, 38), glow_r=9.6,
                    outline=2.4, outline_col=(36, 6, 14),
                    shadow_col=(18, 2, 8), shadow_alpha=0.72,
                    synth_bold=sb,
                )
                out[i] = (sb_sp, gb_sp, cx - sb_sp.width * 0.5, cy - sb_sp.height * 0.5)
        return out

    @staticmethod
    def _draw_parting_thorns(canvas: Image.Image, line, t: float, fo: float):
        """绘制从字行中央向上下两侧拨开退散的哥特黑红荆棘枝条 (66.75s ~ 69.65s)。"""
        if t > 69.75:
            return
        u_in = ease_out(clamp01((t - (line.start + 0.05)) / 0.55))
        u_part = ease_in_out(clamp01((t - 67.92) / 1.15))
        al_mul = u_in * (1.0 - 0.85 * u_part) * fo
        if al_mul <= 0.02:
            return

        x0 = line.bbox_x0 + 16
        w = max(60, int((line.bbox_x1 - line.bbox_x0) * 0.68))
        h = 78
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (44, 8, 18, 0))
        d = ImageDraw.Draw(im)
        cy = (h * 0.5) * SS
        spread = (4.0 + 17.5 * u_part) * SS

        for sgn in (-1.0, 1.0):
            pts = []
            for px in range(6 * SS, w * SS - 6 * SS, 6 * SS):
                u = px / max(1.0, w * SS)
                py = cy + sgn * (spread * math.sin(math.pi * u) + 3.5 * SS * math.sin(u * 13.0))
                pts.append((px, py))
            if len(pts) >= 2:
                d.line(pts, fill=(38, 6, 14, int(195 * al_mul)), width=4)
                d.line(pts, fill=(186, 18, 46, int(165 * al_mul)), width=2)
                for k in range(1, len(pts) - 1, 2):
                    tx, ty = pts[k]
                    d.polygon([(tx - 4, ty), (tx + 5, ty + sgn * 12), (tx + 4, ty)],
                              fill=(204, 20, 48, int(190 * al_mul)))

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, x0, line.y + line.font.size * 0.52 - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        w_cloud = ease_in_out(clamp01((t - 69.417) / 0.28)) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)
        self._draw_parting_thorns(canvas, self.jp, t, fo)
        self._draw_parting_thorns(canvas, self.cn, t, fo)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_blood or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        # 1) 『流した血の色 / 流淌出的血色』浸染绯红血泽
        if self.jp.exit_progress(t) < 0.25:
            w_b = ease_out(clamp01((t - self.t_blood) / 0.45)) * fo
            for line, b_map in ((self.jp, self.jp_blood), (self.cn, self.cn_blood)):
                for i, (sb_sp, gb_sp, bx, by) in b_map.items():
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, gb_sp, bx + dx, by + dy, a_ch * w_b * 0.90)
                        composite_alpha(canvas, sb_sp, bx + dx, by + dy, a_ch * w_b * 0.92)

        # 2) 凝结并缓缓拉丝垂落的晶莹血珠
        im = Image.new("RGBA", (canvas.width, canvas.height), (206, 8, 32, 0))
        d = ImageDraw.Draw(im)
        has_d = False
        for tb, life, x0, y0, rad in self.blood_drops:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                al = math.sin(math.pi * (u ** 0.68)) * fo
                if al <= 0.03:
                    continue
                has_d = True
                # 前 25% 凝珠蓄力, 随后重力加速垂落并拉出纤细血丝尾迹
                fall = 0.0 if u < 0.22 else 44.0 * (((u - 0.22) / 0.78) ** 1.85)
                py = y0 + fall
                if fall > 3.0:
                    d.line([(x0, y0), (x0, py)], fill=(186, 8, 30, int(135 * al * (1.0 - u))), width=2)
                # 水滴形血珠 (上尖下圆)
                d.polygon([(x0, py - rad * 1.65), (x0 - rad * 0.92, py - rad * 0.1), (x0 + rad * 0.92, py - rad * 0.1)],
                          fill=(208, 8, 32, int(232 * al)))
                d.ellipse([x0 - rad, py - rad * 0.85, x0 + rad, py + rad * 1.15],
                          fill=(208, 8, 32, int(238 * al)))
                hr = rad * 0.32
                d.ellipse([x0 - rad * 0.32 - hr, py - rad * 0.1 - hr, x0 - rad * 0.32 + hr, py - rad * 0.1 + hr],
                          fill=(255, 220, 228, int(215 * al)))
        if has_d:
            canvas.alpha_composite(im)


# =====================================================================
#  [L12] 胸口哥特红蔷薇绽放 + 『紅く熱く』赤金灼热星火 (71.45s ~ 74.60s)
# =====================================================================
class BurningChestRose(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_hot = 72.88     # 『紅く熱く / 炽热绯红』灼热绽放

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(76, 14, 34), alpha=70)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(76, 14, 34), alpha=70)

        # 计算『薔薇』(JP 2..3) 与『蔷薇』(CN 4..5) 几何中心
        self.rose_jp = self._span_center(jp_line, 2, 3)
        self.rose_cn = self._span_center(cn_line, 4, 5)

        self.jp_fire = self._prep_fire_chars(jp_line, font_jp, range(6, 10), 0)
        self.cn_fire = self._prep_fire_chars(cn_line, font_cn, range(7, 11), C.CN_SYNTH_BOLD)

        rng = random.Random(7145)
        self.embers = []
        for k in range(26):
            ln = jp_line if (k % 2 == 0) else cn_line
            x_min = ln.bbox_x0 + (ln.bbox_x1 - ln.bbox_x0) * 0.48
            tb = rng.uniform(72.85, 74.10)
            life = rng.uniform(0.65, 1.10)
            x0 = rng.uniform(x_min, ln.bbox_x1 - 18)
            y0 = ln.y + rng.uniform(14.0, 42.0)
            vx = rng.uniform(-14.0, 18.0)
            vy = rng.uniform(-38.0, -16.0)
            rad = rng.uniform(2.0, 3.8)
            self.embers.append((tb, life, x0, y0, vx, vy, rad))

    @staticmethod
    def _span_center(line, i0, i1):
        xs = [line.chars[i][5] for i in range(i0, min(len(line.chars), i1 + 1)) if not line.chars[i][7]]
        ys = [line.chars[i][6] for i in range(i0, min(len(line.chars), i1 + 1)) if not line.chars[i][7]]
        return (sum(xs) / max(1, len(xs)), sum(ys) / max(1, len(ys)))

    @staticmethod
    def _prep_fire_chars(line, font, idx_range, sb):
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, _, _, _, _, cx, cy, _ = line.chars[i]
                sf, gf = char_sprites(
                    line.text[i], font,
                    fill_top=(255, 246, 214), fill_bot=(244, 52, 68),
                    glow_col=(248, 38, 52), glow_r=10.2,
                    outline=2.4, outline_col=(42, 8, 14),
                    shadow_col=(20, 4, 8), shadow_alpha=0.72,
                    synth_bold=sb,
                )
                out[i] = (sf, gf, cx - sf.width * 0.5, cy - sf.height * 0.5)
        return out

    @staticmethod
    def _draw_rose_rosette(canvas: Image.Image, cx: float, cy: float, bloom: float, alpha_mul: float):
        """2x 超采样绘制优雅的哥特层叠红蔷薇花冠衬纹 (z=22)。"""
        if bloom <= 0.03 or alpha_mul <= 0.03:
            return
        sz = 92
        SS = 2
        im = Image.new("RGBA", (sz * SS, sz * SS), (196, 18, 46, 0))
        d = ImageDraw.Draw(im)
        mc = (sz * 0.5) * SS
        rot_base = (1.0 - bloom) * 0.55

        for ring_idx, (n_pet, r_out, col_rgb, al_k) in enumerate((
            (7, 36.0 * bloom, (148, 12, 34), 125),
            (6, 25.0 * bloom, (206, 20, 48), 155),
            (5, 14.5 * bloom, (246, 56, 82), 175),
        )):
            al = int(al_k * alpha_mul)
            for k in range(n_pet):
                ang = rot_base * (1 if ring_idx % 2 == 0 else -1) + k * (math.tau / n_pet) + ring_idx * 0.4
                px = mc + math.cos(ang) * r_out * 0.55 * SS
                py = mc + math.sin(ang) * r_out * 0.55 * SS
                rr = r_out * 0.52 * SS
                d.ellipse([px - rr, py - rr * 0.78, px + rr, py + rr * 0.78], fill=(*col_rgb, al))

        out = im.resize((sz, sz), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, cx - sz * 0.5, cy - sz * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        # 71.45~72.80s 白底舞亚 + 73.58~74.35s 暖白逆光闪切柔云护航
        w_c1 = 1.0 - ease_in_out(clamp01((t - 73.542) / 0.25))
        w_c2 = ease_out(clamp01((t - 74.417) / 0.16)) * (1.0 - ease_in_out(clamp01((t - 75.042) / 0.28)))
        w_cloud = max(w_c1, w_c2) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)

        bloom = ease_out(clamp01((t - 71.88) / 0.65))
        self._draw_rose_rosette(canvas, self.rose_jp[0], self.rose_jp[1], bloom, fo * 0.85)
        self._draw_rose_rosette(canvas, self.rose_cn[0], self.rose_cn[1], bloom, fo * 0.85)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_hot or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        if self.jp.exit_progress(t) < 0.25:
            w_f = ease_out(clamp01((t - self.t_hot) / 0.42)) * fo
            pulse = 0.86 + 0.14 * math.sin((t - self.t_hot) * 9.0)
            for line, f_map in ((self.jp, self.jp_fire), (self.cn, self.cn_fire)):
                for i, (sf, gf, fx, fy) in f_map.items():
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, gf, fx + dx, fy + dy, clamp01(a_ch * w_f * pulse))
                        composite_alpha(canvas, sf, fx + dx, fy + dy, a_ch * w_f)

        # 升腾的赤金灼热火种微粒
        im = Image.new("RGBA", (canvas.width, canvas.height), (255, 118, 68, 0))
        d = ImageDraw.Draw(im)
        has_e = False
        for tb, life, x0, y0, vx, vy, rad in self.embers:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                al = math.sin(math.pi * u) * fo
                if al > 0.03:
                    has_e = True
                    px = x0 + vx * age + 4.0 * math.sin(age * 6.5)
                    py = y0 + vy * age
                    r2 = rad * 2.0
                    d.ellipse([px - r2, py - r2, px + r2, py + r2], fill=(244, 48, 58, int(96 * al)))
                    d.ellipse([px - rad * 0.7, py - rad * 0.7, px + rad * 0.7, py + rad * 0.7],
                              fill=(255, 236, 172, int(235 * al)))
        if has_e:
            canvas.alpha_composite(im)


# =====================================================================
#  [L13] 『傷つけて / 傷ついて』交叉银红剑光斩痕 + 『溶け合ってゆくの』双色交融 (74.60s ~ 78.80s)
# =====================================================================
class SlashScarsMelt(Layer):
    z = 35

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_slash1 = 74.72   # 『傷つけて / 彼此伤害』第一道斜斩!
        self.t_slash2 = 76.02   # 『傷ついて / 遍体鳞伤』第二道逆向斜斩!
        self.t_melt = 77.05     # 『溶け合ってゆくの / 渐渐交融一体』双色交融!

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(72, 16, 36), alpha=68)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(72, 16, 36), alpha=68)

        self.c_jp1 = BurningChestRose._span_center(jp_line, 0, 3)
        self.c_jp2 = BurningChestRose._span_center(jp_line, 5, 8)
        self.c_cn1 = BurningChestRose._span_center(cn_line, 0, 3)
        self.c_cn2 = BurningChestRose._span_center(cn_line, 5, 8)

        # 受斩瞬间的锋利微震钩子
        def _make_slash_hook():
            def _hook(i: int, t: float):
                if 0 <= i <= 3:
                    dt = t - self.t_slash1
                    if 0.0 <= dt <= 0.26:
                        s = math.exp(-dt * 12.0) * math.sin(dt * 52.0)
                        return 4.5 * s, -2.2 * s, 1.0
                elif 5 <= i <= 8:
                    dt = t - self.t_slash2
                    if 0.0 <= dt <= 0.26:
                        s = math.exp(-dt * 12.0) * math.sin(dt * 52.0)
                        return -4.5 * s, 2.2 * s, 1.0
                return 0.0, 0.0, 1.0
            return _hook

        jp_line.motion_hook = _make_slash_hook()
        cn_line.motion_hook = _make_slash_hook()

        # 『溶け合ってゆくの (10..17) / 渐渐交融一体 (10..15)』玫瑰绯红与香槟暖金双色交融光晕
        self.jp_rose = _prep_idx_halos(jp_line, font_jp, range(10, 18), (255, 58, 98), 9.5, 0)
        self.jp_gold = _prep_idx_halos(jp_line, font_jp, range(10, 18), (255, 224, 146), 9.5, 0)
        self.cn_rose = _prep_idx_halos(cn_line, font_cn, range(10, 16), (255, 58, 98), 9.5, C.CN_SYNTH_BOLD)
        self.cn_gold = _prep_idx_halos(cn_line, font_cn, range(10, 16), (255, 224, 146), 9.5, C.CN_SYNTH_BOLD)

    @staticmethod
    def _draw_blade_slash(canvas: Image.Image, cx: float, cy: float, dt: float, angle_deg: float):
        """绘制凌厉划破空气的银白芯绯红刃光斩痕!"""
        if dt < 0.0 or dt > 0.62:
            return
        u = dt / 0.62
        reach = ease_out(clamp01(dt / 0.16))
        fade = (1.0 - ease_in_out(clamp01((u - 0.18) / 0.82)))
        if fade <= 0.02:
            return

        w, h = 230, 96
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (236, 28, 62, 0))
        d = ImageDraw.Draw(im)
        mcx, mcy = (w * 0.5) * SS, (h * 0.5) * SS
        rad = math.radians(angle_deg)
        ca, sa = math.cos(rad), math.sin(rad)
        half_len = 96.0 * SS * reach
        x0, y0 = mcx - ca * half_len, mcy - sa * half_len
        x1, y1 = mcx + ca * half_len, mcy + sa * half_len
        nx, ny = -sa, ca

        # 绯红刃气外晕 + 纯白锋刃细芯
        w_outer = 5.2 * SS * (1.0 - 0.55 * u)
        d.polygon([
            (x0, y0),
            (mcx + nx * w_outer, mcy + ny * w_outer),
            (x1, y1),
            (mcx - nx * w_outer, mcy - ny * w_outer),
        ], fill=(232, 22, 56, int(205 * fade)))

        w_core = 2.0 * SS * (1.0 - 0.45 * u)
        d.polygon([
            (x0, y0),
            (mcx + nx * w_core, mcy + ny * w_core),
            (x1, y1),
            (mcx - nx * w_core, mcy - ny * w_core),
        ], fill=(255, 250, 252, int(250 * fade)))

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, cx - w * 0.5, cy - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        w_cloud = ease_out(clamp01((t - self.start) / 0.25)) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))

        # 1) 两道交叉银红刀光斩痕
        self._draw_blade_slash(canvas, self.c_jp1[0], self.c_jp1[1], t - self.t_slash1, -21.0)
        self._draw_blade_slash(canvas, self.c_cn1[0], self.c_cn1[1], t - self.t_slash1, -21.0)
        self._draw_blade_slash(canvas, self.c_jp2[0], self.c_jp2[1], t - self.t_slash2, 21.0)
        self._draw_blade_slash(canvas, self.c_cn2[0], self.c_cn2[1], t - self.t_slash2, 21.0)

        # 2) 『溶け合ってゆくの / 渐渐交融一体』双色光晕从两侧相拥合一!
        if t >= self.t_melt and self.jp.exit_progress(t) < 0.28:
            u_m = ease_in_out(clamp01((t - self.t_melt) / 0.95))
            sep = 6.5 * (1.0 - u_m)
            al_m = ease_out(clamp01((t - self.t_melt) / 0.45)) * fo * 0.72
            for line, r_map, g_map in ((self.jp, self.jp_rose, self.jp_gold),
                                       (self.cn, self.cn_rose, self.cn_gold)):
                for i in r_map:
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        rh, rx, ry = r_map[i]
                        gh, gx, gy = g_map[i]
                        composite_alpha(canvas, rh, rx + dx - sep, ry + dy - sep * 0.3, a_ch * al_m)
                        composite_alpha(canvas, gh, gx + dx + sep, gy + dy + sep * 0.3, a_ch * al_m)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)


# =====================================================================
#  [L14] 『この　悦楽』有子星海同心水波纹 + 星芒闪烁 (78.94s ~ 82.65s)
# =====================================================================
class EcstasyStarlightRipples(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_etsu = 80.38    # 0.74s 休止拍后『悦楽 / 欢愉』破寂绽放!

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0 + 36, 74, rgb=(64, 24, 48), alpha=72)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0 + 36, 74, rgb=(64, 24, 48), alpha=72)

        self.c_jp = BurningChestRose._span_center(jp_line, 3, 4)
        self.c_cn = BurningChestRose._span_center(cn_line, 3, 4)

        self.jp_azure = _prep_idx_halos(jp_line, font_jp, [3, 4], (96, 208, 255), 10.0, 0)
        self.cn_azure = _prep_idx_halos(cn_line, font_cn, [3, 4], (126, 198, 255), 10.0, C.CN_SYNTH_BOLD)

        rng = random.Random(7894)
        self.stars = []
        for k in range(16):
            cx, cy = self.c_jp if (k % 2 == 0) else self.c_cn
            tb = rng.uniform(80.42, 81.85)
            life = rng.uniform(0.55, 0.95)
            ox = rng.uniform(-76.0, 76.0)
            oy = rng.uniform(-28.0, 28.0)
            rad = rng.uniform(5.5, 9.5)
            self.stars.append((tb, life, cx + ox, cy + oy, rad))

    @staticmethod
    def _draw_water_ripples(canvas: Image.Image, cx: float, cy: float, dt: float, fo: float):
        """绘制呼应 1:21 有子星海镜面的透视同心星光水波纹椭圆环 (z=22)。"""
        if dt < 0.0:
            return
        w, h = 280, 110
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (92, 198, 255, 0))
        d = ImageDraw.Draw(im)
        mcx, mcy = (w * 0.5) * SS, (h * 0.54) * SS
        has_r = False

        for k in range(3):
            age = dt - k * 0.34
            if 0.0 <= age <= 1.45:
                u = age / 1.45
                al = (1.0 - ease_in_out(u)) * ease_out(clamp01(u / 0.18)) * fo
                if al > 0.03:
                    has_r = True
                    rx = (22.0 + 102.0 * ease_out(u)) * SS
                    ry = (8.0 + 36.0 * ease_out(u)) * SS
                    col = (98, 214, 255) if (k % 2 == 0) else (228, 136, 255)
                    d.ellipse([mcx - rx, mcy - ry, mcx + rx, mcy + ry],
                              outline=(*col, int(195 * al)), width=3)
        if has_r:
            out = im.resize((w, h), Image.Resampling.LANCZOS)
            composite_alpha(canvas, out, cx - w * 0.5, cy - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        # 78.94s~80.45s 纯白逆光手部特写柔云护航, 切入深蓝星海后柔和收起
        w_cloud = (1.0 - ease_in_out(clamp01((t - 81.167) / 0.45))) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 62, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 62, self.cn.y - 52, w_cloud)

        if t >= self.t_etsu:
            self._draw_water_ripples(canvas, self.c_jp[0], self.c_jp[1], t - self.t_etsu, fo)
            self._draw_water_ripples(canvas, self.c_cn[0], self.c_cn[1], t - self.t_etsu, fo)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_etsu or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        if self.jp.exit_progress(t) < 0.25:
            w_a = ease_out(clamp01((t - self.t_etsu) / 0.40)) * fo * 0.85
            for line, a_map in ((self.jp, self.jp_azure), (self.cn, self.cn_azure)):
                for i, (ah, ax, ay) in a_map.items():
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, ah, ax + dx, ay + dy, a_ch * w_a)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

        im = Image.new("RGBA", (canvas.width, canvas.height), (218, 245, 255, 0))
        d = ImageDraw.Draw(im)
        has_s = False
        for tb, life, sx, sy, rad in self.stars:
            age = t - tb
            if 0.0 <= age <= life:
                al = math.sin(math.pi * (age / life)) * fo
                if al > 0.04:
                    has_s = True
                    _draw_star4(d, sx, sy, rad * (0.65 + 0.35 * al), (235, 250, 255, int(230 * al)))
        if has_s:
            canvas.alpha_composite(im)


# =====================================================================
#  [L15] 『愛してる×2』双重心跳脉冲 + 85.75s『殺したいほどに』病娇猩红斩裂闪光! (82.65s ~ 87.15s)
# =====================================================================
class YandereLoveKillFlash(Layer):
    z = 36

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_beat1 = 82.68    # 第一个『愛してる』心跳
        self.t_beat2 = 83.92    # 第二个『愛してる』心跳
        self.t_kill = 85.48     # 『殺したいほどに』病娇突变启动
        self.t_flash = 86.583   # 修正时间轴：对应旧版 85.75s 的同一视频帧

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(68, 10, 24), alpha=68)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(68, 10, 24), alpha=74)

        self.c_b1_jp = BurningChestRose._span_center(jp_line, 0, 3)
        self.c_b2_jp = BurningChestRose._span_center(jp_line, 5, 8)
        self.c_b1_cn = BurningChestRose._span_center(cn_line, 0, 2)
        self.c_b2_cn = BurningChestRose._span_center(cn_line, 4, 6)

        self.c_kill_jp = BurningChestRose._span_center(jp_line, 10, 16)
        self.c_kill_cn = BurningChestRose._span_center(cn_line, 8, 15)

        # 85.75s 瞬间『殺したいほどに / 爱到几欲将你扼杀』的高压战栗钩子
        def _make_yandere_hook(kill_i0: int):
            def _hook(i: int, t: float):
                if i >= kill_i0 and 86.542 <= t <= 87.125:
                    dt = t - 86.542
                    amp = 3.2 * math.exp(-dt * 4.2)
                    jx = amp * math.sin(dt * 68.0 + i * 1.9)
                    jy = amp * 0.65 * math.cos(dt * 57.0 + i * 2.3)
                    return jx, jy, 1.0
                return 0.0, 0.0, 1.0
            return _hook

        jp_line.motion_hook = _make_yandere_hook(10)
        cn_line.motion_hook = _make_yandere_hook(8)

        # 『殺したいほどに (10..16) / 爱到几欲将你扼杀 (8..15)』病娇黑红双层高反差字形!
        self.jp_kill = self._prep_kill_chars(jp_line, font_jp, range(10, 17), 0)
        self.cn_kill = self._prep_kill_chars(cn_line, font_cn, range(8, 16), C.CN_SYNTH_BOLD)

        rng = random.Random(8575)
        self.shards = []
        for cx, cy in (self.c_kill_jp, self.c_kill_cn):
            for k in range(14):
                ang = rng.uniform(-math.pi, math.pi)
                spd = rng.uniform(36.0, 115.0)
                vx = math.cos(ang) * spd
                vy = math.sin(ang) * spd * 0.55
                life = rng.uniform(0.48, 0.88)
                sz = rng.uniform(3.2, 6.2)
                self.shards.append((cx + rng.uniform(-80, 80), cy + rng.uniform(-10, 10), vx, vy, life, sz, ang))

    @staticmethod
    def _prep_kill_chars(line, font, idx_range, sb):
        out = {}
        for i in idx_range:
            if i < len(line.chars) and not line.chars[i][7]:
                _, _, _, _, _, cx, cy, _ = line.chars[i]
                sk, gk = char_sprites(
                    line.text[i], font,
                    fill_top=(255, 250, 252), fill_bot=(255, 58, 86),
                    glow_col=(255, 10, 38), glow_r=10.5,
                    outline=2.8, outline_col=(18, 2, 6),
                    shadow_col=(0, 0, 0), shadow_alpha=0.82,
                    synth_bold=sb,
                )
                out[i] = (sk, gk, cx - sk.width * 0.5, cy - sk.height * 0.5)
        return out

    @staticmethod
    def _draw_heartbeat_ring(canvas: Image.Image, cx: float, cy: float, dt: float):
        if dt < 0.0 or dt > 0.72:
            return
        u = dt / 0.72
        al = (1.0 - ease_in_out(u)) * ease_out(clamp01(u / 0.16))
        if al <= 0.03:
            return
        w, h = 210, 88
        im = Image.new("RGBA", (w, h), (255, 62, 106, 0))
        d = ImageDraw.Draw(im)
        rx = 26.0 + 72.0 * ease_out(u)
        ry = 12.0 + 26.0 * ease_out(u)
        d.ellipse([w * 0.5 - rx, h * 0.5 - ry, w * 0.5 + rx, h * 0.5 + ry],
                  outline=(255, 76, 118, int(190 * al)), width=2)
        composite_alpha(canvas, im, cx - w * 0.5, cy - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        # 83.88s 起窗前逆光拥抱 + 85.75s 右下纯白剪影高亮护航
        w_cloud = ease_out(clamp01((t - 84.708) / 0.30)) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud * 0.82)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)

        self._draw_heartbeat_ring(canvas, self.c_b1_jp[0], self.c_b1_jp[1], t - self.t_beat1)
        self._draw_heartbeat_ring(canvas, self.c_b1_cn[0], self.c_b1_cn[1], t - self.t_beat1)
        self._draw_heartbeat_ring(canvas, self.c_b2_jp[0], self.c_b2_jp[1], t - self.t_beat2)
        self._draw_heartbeat_ring(canvas, self.c_b2_cn[0], self.c_b2_cn[1], t - self.t_beat2)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_kill or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        # 1) 『殺したいほどに / 爱到几欲将你扼杀』病娇高反差黑边血芯覆盖
        if self.jp.exit_progress(t) < 0.25:
            w_k = ease_out(clamp01((t - self.t_kill) / 0.28)) * fo
            for line, k_map in ((self.jp, self.jp_kill), (self.cn, self.cn_kill)):
                for i, (sk, gk, kx, ky) in k_map.items():
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, gk, kx + dx, ky + dy, a_ch * w_k)
                        composite_alpha(canvas, sk, kx + dx, ky + dy, a_ch * w_k)

        # 2) 精确锁定 85.75s 红底白影闪切帧的横贯血白一闪斩击 + 飞散红晶碎片!
        dt_f = t - self.t_flash
        if 0.0 <= dt_f <= 0.85:
            SlashScarsMelt._draw_blade_slash(canvas, self.c_kill_jp[0], self.c_kill_jp[1], dt_f, -8.5)
            SlashScarsMelt._draw_blade_slash(canvas, self.c_kill_cn[0], self.c_kill_cn[1], dt_f, -8.5)

            im = Image.new("RGBA", (canvas.width, canvas.height), (255, 28, 58, 0))
            d = ImageDraw.Draw(im)
            has_s = False
            for sx, sy, vx, vy, life, sz, ang in self.shards:
                if dt_f <= life:
                    u = dt_f / life
                    al = (1.0 - ease_in_out(u)) * fo
                    if al > 0.03:
                        has_s = True
                        px = sx + vx * dt_f
                        py = sy + vy * dt_f + 35.0 * (dt_f ** 2)
                        ca, sa = math.cos(ang + dt_f * 6.0), math.sin(ang + dt_f * 6.0)
                        d.polygon([
                            (px + ca * sz * 1.5, py + sa * sz * 1.5),
                            (px - sa * sz * 0.5, py + ca * sz * 0.5),
                            (px - ca * sz * 1.2, py - sa * sz * 1.2),
                        ], fill=(255, 238, 244, int(235 * al)))
            if has_s:
                canvas.alpha_composite(im)


# =====================================================================
#  [L16] 3D 棋盘箱庭呼应 — 四向哥特金红花丝宝匣合拢锁死! (87.44s ~ 90.67s)
# =====================================================================
class HeartLockboxCage(Layer):
    z = 34

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_lock = 88.88    # 『閉じ込めたい / 锁进心底的匣中』四向合拢上锁!

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(72, 14, 28), alpha=68)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(72, 14, 28), alpha=68)

    @staticmethod
    def _draw_lockbox(canvas: Image.Image, line, u_lock: float, fo: float):
        """绘制从上下左右四侧滑入合拢并在四角星钻扣死的哥特金红花丝匣框!"""
        if u_lock <= 0.02 or fo <= 0.02:
            return
        pad_x, pad_y = 14, 8
        x0 = line.bbox_x0 + 10 - pad_x
        x1 = line.bbox_x1 - 10 + pad_x
        y0 = line.y - pad_y
        y1 = line.y + line.font.size + pad_y

        # 四边从外侧 24px 滑入精准咬合!
        slide = 24.0 * (1.0 - ease_out(u_lock))
        al_main = int(208 * ease_out(clamp01(u_lock / 0.45)) * fo)
        al_gold = int(235 * ease_out(clamp01((u_lock - 0.35) / 0.45)) * fo)
        if al_main <= 3:
            return

        w_buf = int(x1 - x0 + 96)
        h_buf = int(y1 - y0 + 80)
        ox, oy = int(x0 - 48), int(y0 - 40)
        SS = 2
        im = Image.new("RGBA", (w_buf * SS, h_buf * SS), (238, 188, 118, 0))
        d = ImageDraw.Draw(im)

        lx0, lx1 = (x0 - ox) * SS, (x1 - ox) * SS
        ly0, ly1 = (y0 - oy) * SS, (y1 - oy) * SS
        sl = slide * SS

        col_crimson = (212, 34, 66, al_main)
        col_gold = (255, 224, 148, al_gold)

        # 上下双轨水平锁杆 (反向滑入咬合)
        d.line([(lx0 - sl, ly0), (lx1 - sl, ly0)], fill=col_crimson, width=3)
        d.line([(lx0 + sl, ly1), (lx1 + sl, ly1)], fill=col_crimson, width=3)
        # 左右双轨垂直锁杆
        d.line([(lx0, ly0 - sl * 0.6), (lx0, ly1 - sl * 0.6)], fill=col_crimson, width=3)
        d.line([(lx1, ly0 + sl * 0.6), (lx1, ly1 + sl * 0.6)], fill=col_crimson, width=3)

        # 合拢瞬间四角点亮黄金菱形锁扣!
        if al_gold > 8:
            d.rectangle([lx0 + 4, ly0 + 4, lx1 - 4, ly1 - 4], outline=(255, 216, 138, int(al_gold * 0.55)), width=2)
            r_d = (4.8 + 2.2 * math.sin(math.pi * clamp01((u_lock - 0.65) / 0.35))) * SS
            for cx_c, cy_c in ((lx0, ly0), (lx1, ly0), (lx0, ly1), (lx1, ly1)):
                d.polygon([(cx_c, cy_c - r_d), (cx_c + r_d, cy_c), (cx_c, cy_c + r_d), (cx_c - r_d, cy_c)],
                          fill=col_gold)

        out = im.resize((w_buf, h_buf), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, ox, oy, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        w_cloud = (1.0 - ease_in_out(clamp01((t - 90.667) / 0.35))) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_lock or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        u_lock = clamp01((t - self.t_lock) / 0.68)
        self._draw_lockbox(canvas, self.jp, u_lock, fo)
        self._draw_lockbox(canvas, self.cn, u_lock, fo)


# =====================================================================
#  [L17] 暖阳封闭屋室 — 窗棂斜射暖光与虹彩柔焦光斑 (90.67s ~ 94.90s)
# =====================================================================
class ClosedRoomWarmWorld(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_world = 92.80   # 『世界の全てに / 便是世界的全部』暖阳满溢

        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0, 74, rgb=(76, 36, 22), alpha=68)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0, 74, rgb=(76, 36, 22), alpha=68)

        self.jp_warm = _prep_idx_halos(jp_line, font_jp, range(12, 18), (255, 212, 128), 9.5, 0)
        self.cn_warm = _prep_idx_halos(cn_line, font_cn, range(8, 15), (255, 212, 128), 9.5, C.CN_SYNTH_BOLD)

        rng = random.Random(9067)
        self.bokehs = []
        palette = [(255, 220, 142), (255, 168, 186), (178, 232, 255), (255, 238, 178)]
        for k in range(18):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(91.40, 94.05)
            life = rng.uniform(1.05, 1.65)
            x0 = rng.uniform(ln.bbox_x0 + 28, ln.bbox_x1 - 28)
            y0 = ln.y + rng.uniform(4.0, 42.0)
            vx = rng.uniform(-12.0, 16.0)
            vy = rng.uniform(-14.0, -4.0)
            rad = rng.uniform(7.5, 14.5)
            col = palette[k % len(palette)]
            self.bokehs.append((tb, life, x0, y0, vx, vy, rad, col))

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        # 93.55s 起窗外白金暖阳大光晕渐亮
        w_cloud = ease_out(clamp01((t - 94.292) / 0.40)) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 44, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 44, self.cn.y - 52, w_cloud)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        if t >= self.t_world and self.jp.exit_progress(t) < 0.25:
            w_w = ease_out(clamp01((t - self.t_world) / 0.55)) * fo * 0.78
            for line, w_map in ((self.jp, self.jp_warm), (self.cn, self.cn_warm)):
                for i, (wh, wx, wy) in w_map.items():
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, wh, wx + dx, wy + dy, a_ch * w_w)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

        im = Image.new("RGBA", (canvas.width, canvas.height), (255, 224, 168, 0))
        d = ImageDraw.Draw(im)
        has_b = False
        for tb, life, x0, y0, vx, vy, rad, col in self.bokehs:
            age = t - tb
            if 0.0 <= age <= life:
                al = math.sin(math.pi * (age / life)) * fo * 0.42
                if al > 0.02:
                    has_b = True
                    px = x0 + vx * age
                    py = y0 + vy * age
                    d.ellipse([px - rad, py - rad, px + rad, py + rad],
                              fill=(*col, int(110 * al)), outline=(*col, int(185 * al)), width=1)
        if has_b:
            canvas.alpha_composite(im)


# =====================================================================
#  [L18] 『時が 続く 永久へ』逆光亲吻柔云护航 + 永恒流金星河 (94.90s ~ 98.53s)
# =====================================================================
class EternalGoldenStream(Layer):
    z = 34

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_towa = 96.88    # 『永久へ / 迈向永恒』点亮

        # 94.90s~98.00s 全屏高调暖白亲吻特写柔云护航
        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0 + 24, 74, rgb=(78, 34, 24), alpha=74)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0 + 24, 74, rgb=(78, 34, 24), alpha=74)

        self.jp_gold = _prep_idx_halos(jp_line, font_jp, [6, 7, 8], (255, 226, 136), 10.0, 0)
        self.cn_gold = _prep_idx_halos(cn_line, font_cn, [7, 8, 9, 10], (255, 226, 136), 10.0, C.CN_SYNTH_BOLD)

        rng = random.Random(9490)
        self.sands = []
        for k in range(32):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(self.start + 0.10, self.end - 0.85)
            life = rng.uniform(0.90, 1.45)
            x0 = rng.uniform(ln.bbox_x0 + 12, ln.bbox_x1 - 36)
            y0 = ln.y + rng.uniform(8.0, 40.0)
            vx = rng.uniform(28.0, 62.0)
            rad = rng.uniform(1.8, 3.4)
            ph = rng.uniform(0.0, math.tau)
            self.sands.append((tb, life, x0, y0, vx, rad, ph))

    @staticmethod
    def _draw_silk_wave(canvas: Image.Image, line, t: float, fo: float):
        """在字行背后绘制流动的永恒双股暖金丝弦 (z=22)。"""
        u_in = ease_out(clamp01((t - line.start) / 0.55)) * fo
        if u_in <= 0.02:
            return
        w = max(80, int(line.bbox_x1 - line.bbox_x0))
        h = 46
        im = Image.new("RGBA", (w, h), (255, 218, 128, 0))
        d = ImageDraw.Draw(im)
        cy = h * 0.5
        pts1, pts2 = [], []
        for px in range(8, w - 8, 6):
            u = px / max(1.0, w)
            env = math.sin(math.pi * u)
            pts1.append((px, cy + 7.5 * env * math.sin(u * 8.5 - t * 3.8)))
            pts2.append((px, cy - 6.5 * env * math.sin(u * 8.5 - t * 3.8 + 0.8)))
        if len(pts1) >= 2:
            d.line(pts1, fill=(255, 224, 138, int(148 * u_in)), width=2)
            d.line(pts2, fill=(255, 178, 196, int(125 * u_in)), width=2)
        composite_alpha(canvas, im, line.bbox_x0, line.y + line.font.size * 0.54 - h * 0.5, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        w_cloud = (1.0 - 0.35 * ease_in_out(clamp01((t - 98.792) / 0.25))) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 56, self.jp.y - 52, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 56, self.cn.y - 52, w_cloud)
        self._draw_silk_wave(canvas, self.jp, t, fo)
        self._draw_silk_wave(canvas, self.cn, t, fo)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        if t >= self.t_towa and self.jp.exit_progress(t) < 0.25:
            w_g = ease_out(clamp01((t - self.t_towa) / 0.45)) * fo * 0.85
            for line, g_map in ((self.jp, self.jp_gold), (self.cn, self.cn_gold)):
                for i, (gh, gx, gy) in g_map.items():
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, gh, gx + dx, gy + dy, a_ch * w_g)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

        im = Image.new("RGBA", (canvas.width, canvas.height), (255, 232, 156, 0))
        d = ImageDraw.Draw(im)
        has_s = False
        for tb, life, x0, y0, vx, rad, ph in self.sands:
            age = t - tb
            if 0.0 <= age <= life:
                al = math.sin(math.pi * (age / life)) * fo
                if al > 0.03:
                    has_s = True
                    px = x0 + vx * age
                    py = y0 + 5.5 * math.sin(age * 5.2 + ph)
                    r2 = rad * 1.9
                    d.ellipse([px - r2, py - r2, px + r2, py + r2], fill=(255, 212, 118, int(92 * al)))
                    d.ellipse([px - rad * 0.65, py - rad * 0.65, px + rad * 0.65, py + rad * 0.65],
                              fill=(255, 252, 232, int(235 * al)))
        if has_s:
            canvas.alpha_composite(im)


# =====================================================================
#  [L19] 终幕『また 繰り返し 開かれる 舞台』歌剧金红天鹅绒帷幕拉开谢幕! (98.53s ~ 102.80s)
# =====================================================================
class EncoreVelvetCurtain(Layer):
    z = 35

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_open = 100.05   # 『開かれる 舞台 / 拉开帷幕的 舞台』双侧天鹅绒幕布拉开!

        # 99.72s 起切入白底弥生 & 101.83s 纯白双女主特写 (且左下角有『原画 克/月杜尋』, 左上+右下完美零遮挡!)
        self.cloud_jp = soft_cloud(jp_line.bbox_x1 - jp_line.bbox_x0 + 20, 76, rgb=(78, 14, 34), alpha=76)
        self.cloud_cn = soft_cloud(cn_line.bbox_x1 - cn_line.bbox_x0 + 20, 76, rgb=(78, 14, 34), alpha=76)

        self.jp_stage = _prep_idx_halos(jp_line, font_jp, [13, 14], (255, 224, 138), 10.5, 0)
        self.cn_stage = _prep_idx_halos(cn_line, font_cn, [12, 13], (255, 224, 138), 10.5, C.CN_SYNTH_BOLD)

        rng = random.Random(9853)
        self.petals = []
        for k in range(24):
            ln = jp_line if (k % 2 == 0) else cn_line
            tb = rng.uniform(100.10, 102.05)
            life = rng.uniform(0.85, 1.35)
            x0 = rng.uniform(ln.bbox_x0 + 24, ln.bbox_x1 - 24)
            y0 = ln.y + rng.uniform(4.0, 38.0)
            vx = rng.uniform(-24.0, 26.0)
            vy = rng.uniform(-18.0, 22.0)
            sz = rng.uniform(4.2, 6.8)
            ang = rng.uniform(0.0, math.tau)
            self.petals.append((tb, life, x0, y0, vx, vy, sz, ang))

    @staticmethod
    def _draw_stage_curtain(canvas: Image.Image, line, u_open: float, fo: float):
        """2x 超采样在字行两侧绘制向左右优雅拉开的古典歌剧束腰红丝绒帷幕与金色顶楣脚光!"""
        if u_open <= 0.01 or fo <= 0.02:
            return
        w = int(line.bbox_x1 - line.bbox_x0 + 52)
        h = 88
        ox = int(line.bbox_x0 - 26)
        oy = int(line.y - 16)
        SS = 2
        im = Image.new("RGBA", (w * SS, h * SS), (172, 14, 38, 0))
        d = ImageDraw.Draw(im)

        open_k = ease_out(u_open)
        al_v = int(218 * ease_out(clamp01(u_open / 0.25)) * fo)
        al_v_dark = int(232 * ease_out(clamp01(u_open / 0.25)) * fo)
        al_g = int(242 * ease_out(clamp01(u_open / 0.30)) * fo)

        mid_x = (w * 0.5) * SS
        span_half = (w * 0.5 - 8) * SS
        y_top = 8 * SS
        y_bot = (h - 10) * SS

        # 左右对称古典歌剧束腰垂褶幕帘 (顶端宽幅华盖 -> 腰部金绳收束 -> 底端优雅垂摆)
        for sgn in (-1, 1):
            edge_x = (8 * SS) if sgn < 0 else (w * SS - 8 * SS)
            # 拉开后顶部仍保留 30px 歌剧斜垂帘角, 腰部金穗收束为 13px, 形成优美 S 形古典舞台帷幕!
            w_top_drape = (28.0 + 75.0 * (1.0 - open_k)) * SS
            w_waist = (11.5 + 48.0 * (1.0 - open_k)) * SS
            w_skirt = (16.5 + 32.0 * (1.0 - open_k)) * SS

            curve_pts = [(edge_x, y_top)]
            steps = 12
            for st in range(steps + 1):
                v = st / steps
                yy = y_top + (y_bot - y_top) * v
                if v <= 0.58:
                    # 上半帘: 优雅弧形收束至金绳束腰点
                    uv = v / 0.58
                    ww = w_top_drape * ((1.0 - uv) ** 1.35) + w_waist * (1.0 - (1.0 - uv) ** 1.35)
                else:
                    # 下半帘: 从束腰微幅垂散后收尖
                    uv = (v - 0.58) / 0.42
                    ww = w_waist + (w_skirt - w_waist) * math.sin(math.pi * uv * 0.85) * (1.0 - 0.35 * uv)
                curve_pts.append((edge_x - sgn * ww, yy))
            curve_pts.append((edge_x, y_bot))

            d.polygon(curve_pts, fill=(168, 12, 36, al_v))
            # 外缘深红丝绒暗褶 + 内缘金色流苏镶边
            d.line([(edge_x, y_top), (edge_x, y_bot)], fill=(96, 6, 20, al_v_dark), width=3)
            d.line(curve_pts[1:-1], fill=(255, 218, 128, al_g), width=3)

            # 腰部黄金绳结星扣
            wy = y_top + (y_bot - y_top) * 0.58
            wx = edge_x - sgn * w_waist
            _draw_star4(d, wx, wy, 5.2 * SS, (255, 236, 162, al_g))

        # 顶部古典波浪拱门金楣细丝 + 底部暖金舞台脚光线
        reach_x = span_half * (0.25 + 0.75 * open_k)
        arch_pts = []
        for k in range(25):
            u = k / 24.0
            xx = (mid_x - reach_x) + (2.0 * reach_x) * u
            yy = y_top + 3.2 * SS * abs(math.sin(u * math.pi * 3.0))
            arch_pts.append((xx, yy))
        d.line(arch_pts, fill=(255, 222, 136, int(al_g * 0.85)), width=2)
        d.line([(mid_x - reach_x * 0.88, y_bot), (mid_x + reach_x * 0.88, y_bot)],
               fill=(255, 222, 136, int(al_g * 0.72)), width=2)

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, ox, oy, 1.0)

    def draw_under(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        w_cloud = ease_out(clamp01((t - 100.500) / 0.25)) * fo
        if w_cloud > 0.02:
            composite_alpha(canvas, self.cloud_jp, self.jp.bbox_x0 - 54, self.jp.y - 53, w_cloud)
            composite_alpha(canvas, self.cloud_cn, self.cn.bbox_x0 - 54, self.cn.y - 53, w_cloud)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_open or t > self.end:
            return
        fo = 1.0 - ease_in_out(self.jp.exit_progress(t))
        if fo <= 0.02:
            return

        u_open = clamp01((t - self.t_open) / 0.95)
        self._draw_stage_curtain(canvas, self.jp, u_open, fo)
        self._draw_stage_curtain(canvas, self.cn, u_open, fo)

        if t >= 100.68 and self.jp.exit_progress(t) < 0.25:
            w_s = ease_out(clamp01((t - 100.68) / 0.45)) * fo * 0.88
            for line, s_map in ((self.jp, self.jp_stage), (self.cn, self.cn_stage)):
                for i, (sh, sx, sy) in s_map.items():
                    s_core, _, _, px_c, py_c, _, _, _ = line.chars[i]
                    dx, dy, a_ch, _ = line.char_state(i, t)
                    if a_ch > 0.04:
                        composite_alpha(canvas, sh, sx + dx, sy + dy, a_ch * w_s)
                        composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)

        im = Image.new("RGBA", (canvas.width, canvas.height), (218, 28, 62, 0))
        d = ImageDraw.Draw(im)
        has_p = False
        for tb, life, x0, y0, vx, vy, sz, ang in self.petals:
            age = t - tb
            if 0.0 <= age <= life:
                al = math.sin(math.pi * (age / life)) * fo
                if al > 0.03:
                    has_p = True
                    px = x0 + vx * age + 4.5 * math.sin(age * 5.0 + ang)
                    py = y0 + vy * age
                    a_cur = ang + age * 4.0
                    ca, sa = math.cos(a_cur), math.sin(a_cur)
                    rx, ry = sz * 1.35, sz * 0.72
                    d.polygon([
                        (px + ca * rx, py + sa * rx),
                        (px - sa * ry, py + ca * ry),
                        (px - ca * rx * 0.82, py - sa * rx * 0.82),
                        (px + sa * ry, py - ca * ry),
                    ], fill=(226, 30, 64, int(218 * al)))
        if has_p:
            canvas.alpha_composite(im)
