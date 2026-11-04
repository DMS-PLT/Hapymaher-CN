# -*- coding: utf-8 -*-
"""A 段专属分镜演出图层 (L00 ~ L04, 20.80s ~ 36.19s)。

全部时间点均与 ../opre.mkv 实测切镜帧和 ../opre.ass 卡拉OK音节严格对齐:
  - ThornPierce       : L00 「棘」「刺」穿刺寒芒细线 + 微颤痛感 (呼应桌面红线穿刺标题)
  - RosePetals        : L00 / L02 随字飘落并带景深翻转的深红蔷薇花瓣
  - MemoryStingMotes  : L01 「痛み」色散刺痛重影 + 25.50s 切有栖角色卡时升起的蓝蝶微光尘
  - NegativeFlashSync : L03 32.333s~32.500s 精准 4 帧青蓝负片反相闪白接管 (深绯黑字+青红色散)
  - VioletFlameStage  : L04 34.167s 舞亚唇燃紫炎光晕接管 + 升腾紫火微焰 + 35.30s「噛む」轻咬牙印
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .base import Layer, clamp01, ease_out, char_sprites, char_halo, composite_alpha
import config as C


class ThornPierce(Layer):
    """L00 バラの棘が刺さる: 在『棘』『刺』唱响瞬间划过锐利绯白穿刺针芒, 并触发微幅刺痛震颤。"""
    z = 62

    def __init__(self, jp_line, cn_line=None, jp_indices=(3, 5)):
        self.jp = jp_line
        self.cn = cn_line
        self.targets = []  # (cx, cy, t_hit, angle_deg)
        angles = (-28.0, -21.0)
        for k, idx in enumerate(jp_indices):
            if idx >= len(jp_line.chars):
                continue
            s, _, x, y = jp_line.chars[idx]
            cx = x + s.width * 0.5
            cy = y + s.height * 0.5
            t_hit = jp_line.t_syl_span[idx][0] + 0.02
            self.targets.append((idx, cx, cy, t_hit, angles[k % len(angles)]))

        # 挂载单字刺痛震颤钩子
        hit_map = {idx: t_hit for idx, _, _, t_hit, _ in self.targets}

        def _hook(i, t):
            if i not in hit_map:
                return (0.0, 0.0, 1.0)
            dt = t - hit_map[i]
            if 0.0 <= dt <= 0.20:
                decay = (1.0 - dt / 0.20) ** 2
                dx = math.sin(dt * 95.0) * 2.4 * decay
                dy = math.cos(dt * 72.0) * 1.4 * decay
                return (dx, dy, 1.0)
            return (0.0, 0.0, 1.0)

        jp_line.motion_hook = _hook

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + 0.2:
            return
        for _, cx, cy, t_hit, ang_deg in self.targets:
            dt = t - t_hit
            if dt < 0.0 or dt > 0.36:
                continue
            u = dt / 0.36
            # 前 25% 极速刺穿伸展, 后 75% 锋芒收缩消散
            reach = ease_out(min(1.0, u / 0.24))
            fade = (1.0 - clamp01((u - 0.16) / 0.84)) ** 1.7

            SS = 3
            pw, ph = 130, 96
            patch = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(patch)
            ox, oy = pw * 0.5 * SS, ph * 0.5 * SS
            rad = math.radians(ang_deg)
            ux, uy = math.cos(rad), math.sin(rad)
            half_len = 50.0 * SS * reach

            x0, y0 = ox - ux * half_len, oy - uy * half_len
            x1, y1 = ox + ux * half_len, oy + uy * half_len

            # 外层绯红晕光 + 锐利白芯针芒
            d.line([x0, y0, x1, y1], fill=(215, 26, 58, int(195 * fade)), width=4 * SS)
            d.line([x0 + ux * 6 * SS, y0 + uy * 6 * SS, x1 - ux * 4 * SS, y1 - uy * 4 * SS],
                   fill=(255, 236, 242, int(245 * fade)), width=max(1, int(1.4 * SS)))

            # 中心微星芒闪点
            spark_r = 7.5 * SS * (1.0 - u * 0.6)
            for s_ang in (0.0, math.pi * 0.5):
                sx, sy = math.cos(s_ang) * spark_r, math.sin(s_ang) * spark_r
                d.line([ox - sx, oy - sy, ox + sx, oy + sy],
                       fill=(255, 210, 220, int(210 * fade)), width=max(1, SS))

            out = patch.resize((pw, ph), Image.Resampling.LANCZOS)
            composite_alpha(canvas, out, cx - pw * 0.5, cy - ph * 0.5, 1.0)


class RosePetals(Layer):
    """在歌词区域周围轻柔飘落的景深蔷薇花瓣 (呼应 L00 庭院落瓣与 L02 绯红空间)。"""
    z = 57

    def __init__(self, lyric_line, count=7, seed=42, color=(196, 22, 48)):
        self.line = lyric_line
        self.t0 = lyric_line.start - 0.10
        self.t1 = lyric_line.end + C.FADE_OUT + 0.15
        rng = random.Random(seed)
        self.petals = []

        xs = [x for _, _, x, _ in lyric_line.chars]
        ys = [y for _, _, _, y in lyric_line.chars]
        x_min, x_max = min(xs) - 25, max(xs) + 55
        y_base = sum(ys) / max(1, len(ys))

        for i in range(count):
            st = lyric_line.start + (lyric_line.end - lyric_line.start) * (i / max(1, count)) * 0.78 + rng.uniform(-0.08, 0.12)
            life = rng.uniform(1.35, 2.05)
            px0 = rng.uniform(x_min, x_max)
            py0 = y_base + rng.uniform(-12.0, 22.0)
            vx = rng.uniform(-34.0, -14.0)     # 向左下轻飘
            vy = rng.uniform(22.0, 40.0)
            sway_amp = rng.uniform(5.0, 11.0)
            sway_freq = rng.uniform(2.6, 4.2)
            rot0 = rng.uniform(0, math.pi * 2)
            rot_v = rng.uniform(-2.6, 2.6)
            size = rng.uniform(5.5, 9.2)
            blur = rng.choice([0.0, 0.6, 1.4])  # 远近景深层次
            sprite = self._make_petal_sprite(size, color, blur)
            self.petals.append((st, life, px0, py0, vx, vy, sway_amp, sway_freq, rot0, rot_v, sprite))

    @staticmethod
    def _make_petal_sprite(size, col, blur):
        SS = 3
        dim = int(math.ceil(size * 3.4))
        im2 = Image.new("RGBA", (dim * SS, dim * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im2)
        c = dim * 0.5 * SS
        r = size * SS
        # 水滴心形花瓣轮廓
        pts = []
        for k in range(28):
            th = k / 28.0 * math.pi * 2
            rx = r * 0.85 * math.sin(th)
            ry = -r * (0.95 * math.cos(th) - 0.28 * math.cos(2 * th))
            pts.append((c + rx, c + ry))
        dark = (max(0, col[0] - 75), max(0, col[1] - 15), max(0, col[2] - 22), 230)
        bright = (min(255, col[0] + 38), min(255, col[1] + 24), min(255, col[2] + 28), 235)
        d.polygon(pts, fill=dark)
        inner = [(c + (px - c) * 0.72, c + (py - c) * 0.72 - 0.8 * SS) for px, py in pts]
        d.polygon(inner, fill=bright)
        im = im2.resize((dim, dim), Image.Resampling.LANCZOS)
        if blur > 0.1:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return im

    def draw(self, canvas, t):
        if t < self.t0 or t > self.t1:
            return
        for st, life, px0, py0, vx, vy, s_amp, s_freq, rot0, rot_v, sp in self.petals:
            dt = t - st
            if dt <= 0.0 or dt >= life:
                continue
            u = dt / life
            a = math.sin(math.pi * u) ** 0.75 * 0.88
            px = px0 + vx * dt + math.sin(dt * s_freq + rot0) * s_amp
            py = py0 + vy * dt
            # 模拟三维翻飞: 旋转 + 轻微横向压缩透视
            ang = math.degrees(rot0 + rot_v * dt)
            squash = 0.55 + 0.45 * abs(math.cos(dt * s_freq * 0.8 + rot0))
            w_s = max(2, int(round(sp.width * squash)))
            s_squashed = sp.resize((w_s, sp.height), Image.Resampling.BILINEAR)
            s_rot = s_squashed.rotate(ang, resample=Image.Resampling.BILINEAR, expand=True)
            composite_alpha(canvas, s_rot, px - s_rot.width * 0.5, py - s_rot.height * 0.5, a)


class MemoryStingMotes(Layer):
    """L01 痛みの記憶ふいに思い出して:
      - 句首『痛み』(23.41s~24.2s) 触发红青色散刺痛重影;
      - 25.50s 切入有栖角色卡时, 伴随发光蓝蝴蝶升起柔和幽蓝微光萤尘。
    """
    z = 56

    def __init__(self, jp_line, font_jp, t_card_cut=25.625):
        self.jp = jp_line
        self.t_cut = t_card_cut
        # 预生成『痛』『み』红/青色散重影字形
        self.ghosts = []
        for idx in (0, 1):
            if idx < len(jp_line.chars):
                ch = jp_line.text[idx]
                s_red, _ = char_sprites(ch, font_jp, (255, 55, 85), (200, 20, 50),
                                        glow_r=4, outline=0, shadow_alpha=0.0)
                s_cya, _ = char_sprites(ch, font_jp, (80, 225, 255), (40, 160, 220),
                                        glow_r=4, outline=0, shadow_alpha=0.0)
                _, _, x, y = jp_line.chars[idx]
                self.ghosts.append((idx, s_red, s_cya, x, y, jp_line.t_char[idx]))

        # 25.50s 有栖蓝蝶微光粒子
        rng = random.Random(101)
        xs = [x for _, _, x, _ in jp_line.chars]
        x_min, x_max = min(xs), max(xs) + 36
        y_mid = jp_line.chars[0][3] + 28
        self.motes = []
        for i in range(9):
            st = t_card_cut + i * 0.16 + rng.uniform(0.0, 0.12)
            life = rng.uniform(1.2, 1.8)
            mx = rng.uniform(x_min, x_max)
            my = y_mid + rng.uniform(-6.0, 26.0)
            vy = rng.uniform(-24.0, -13.0)
            vx = rng.uniform(-8.0, 10.0)
            rad = rng.uniform(3.2, 5.6)
            self.motes.append((st, life, mx, my, vx, vy, rad, i))

    def draw(self, canvas, t):
        if t < self.jp.start or t > self.jp.end + C.FADE_OUT:
            return

        # 1) 『痛み』刺痛色散震荡
        for idx, s_red, s_cya, x, y, t0 in self.ghosts:
            dt = t - t0
            if 0.0 <= dt <= 0.42:
                u = dt / 0.42
                decay = (1.0 - u) ** 1.8
                shift = (3.8 * math.cos(dt * 42.0)) * decay
                a_in = ease_out(clamp01((t - t0) / self.jp.fade_in))
                ry = y - C.RISE * (1.0 - a_in)
                composite_alpha(canvas, s_red, x - shift, ry - 0.8 * decay, 0.62 * decay)
                composite_alpha(canvas, s_cya, x + shift, ry + 0.8 * decay, 0.55 * decay)

        # 2) 25.50s 切卡后升起的幽蓝蝶粉微光 (呼应有栖发间蓝蝴蝶)
        for st, life, mx0, my0, vx, vy, rad, seed in self.motes:
            dt = t - st
            if dt <= 0.0 or dt >= life or t > self.jp.end + 0.15:
                continue
            u = dt / life
            twinkle = 0.72 + 0.28 * math.sin(dt * 11.0 + seed)
            a = math.sin(math.pi * u) * twinkle * 0.85
            px = mx0 + vx * dt + math.sin(dt * 3.5 + seed) * 5.0
            py = my0 + vy * dt
            dim = int(rad * 6)
            sp = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
            d = ImageDraw.Draw(sp)
            c = dim // 2
            d.ellipse([c - rad * 2.1, c - rad * 2.1, c + rad * 2.1, c + rad * 2.1],
                      fill=(55, 165, 255, int(95 * a)))
            d.ellipse([c - rad * 0.9, c - rad * 0.9, c + rad * 0.9, c + rad * 0.9],
                      fill=(210, 245, 255, int(235 * a)))
            sp = sp.filter(ImageFilter.GaussianBlur(1.1))
            composite_alpha(canvas, sp, px - c, py - c, 1.0)


class NegativeFlashSync(Layer):
    """L03 果実の味が (32.333s ~ 32.500s):
    原片在此处有精准 4 帧青蓝负片反相闪白冲击帧!
    接管日/中两行字幕, 切换为「深渊黑绯字芯 + 电光青/绯红双通道色散撕裂」,
    既在刺眼青白背景上保持 100% 锐利可读, 又与画面反相冲击帧严丝合缝咬合。
    """
    z = 65

    def __init__(self, jp_line, cn_line, font_jp, font_cn,
                 t_flash_start=32.458, t_flash_end=32.625):
        self.jp = jp_line
        self.cn = cn_line
        self.t0 = t_flash_start
        self.t1 = t_flash_end

        jp_line.suppress_spans.append((t_flash_start, t_flash_end))
        cn_line.suppress_spans.append((t_flash_start, t_flash_end))

        self.jp_packs = self._build_inv_packs(jp_line, font_jp, synth_bold=0)
        self.cn_packs = self._build_inv_packs(cn_line, font_cn, synth_bold=C.CN_SYNTH_BOLD)

    @staticmethod
    def _build_inv_packs(line, font, synth_bold=0):
        packs = []
        for i, (s_orig, _, x, y) in enumerate(line.chars):
            ch = line.text[i]
            if ch.isspace():
                continue
            # 深暗酒红黑主字 + 亮白细外廓, 在青白反相底上极度醒目
            s_dark, g_cyan = char_sprites(
                ch, font, fill=(26, 8, 18), glow_col=(0, 235, 255),
                glow_r=9, outline=2.2, outline_col=(245, 252, 255),
                shadow_alpha=0.0, synth_bold=synth_bold
            )
            s_red, _ = char_sprites(
                ch, font, fill=(235, 25, 65), glow_col=(235, 25, 65),
                glow_r=3, outline=0, shadow_alpha=0.0, synth_bold=synth_bold
            )
            s_cya, _ = char_sprites(
                ch, font, fill=(20, 225, 255), glow_col=(20, 225, 255),
                glow_r=3, outline=0, shadow_alpha=0.0, synth_bold=synth_bold
            )
            cx = x + s_orig.width * 0.5
            cy = y + s_orig.height * 0.5
            packs.append((i, s_dark, g_cyan, s_red, s_cya,
                          cx - s_dark.width * 0.5, cy - s_dark.height * 0.5))
        return packs

    def _draw_line_inv(self, canvas, line, packs, t):
        u_flash = clamp01((t - self.t0) / max(1e-3, self.t1 - self.t0))
        # 冲击瞬间色散最大 (±5px), 4 帧内高频微震收敛
        split = 5.2 * (1.0 - 0.35 * u_flash) * (1.0 if int((t - self.t0) * 48) % 2 == 0 else -0.8)
        jit_y = 1.2 * math.sin((t - self.t0) * 140.0)

        for i, s_dark, g_cyan, s_red, s_cya, rx, ry in packs:
            a_in = clamp01((t - line.t_char[i]) / line.fade_in)
            if a_in <= 0.0:
                continue
            e_in = ease_out(a_in)
            dy = -C.RISE * (1.0 - e_in) if line.mode in ("karaoke", "chars") else 0.0
            dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in) if line.mode == "cn_slide" else 0.0

            px, py = rx + dx, ry + dy + jit_y
            composite_alpha(canvas, g_cyan, px, py, e_in * 0.85)
            composite_alpha(canvas, s_red, px - split, py - 1.0, e_in * 0.78)
            composite_alpha(canvas, s_cya, px + split, py + 1.0, e_in * 0.78)
            composite_alpha(canvas, s_dark, px, py, e_in)

    def draw(self, canvas, t):
        if t < self.t0 or t > self.t1:
            return
        self._draw_line_inv(canvas, self.jp, self.jp_packs, t)
        self._draw_line_inv(canvas, self.cn, self.cn_packs, t)


class VioletFlameStage(Layer):
    """L04 懐かしくて唇を噛む (32.60s ~ 36.19s):
      1) 34.167s 原片切入舞亚指抵双唇燃起紫白妖火 -> 日/中字幕辉光同步渐变为妖紫罗兰色,
         并从字间升腾起细碎的紫白幽火微焰;
      2) 35.30s 唱到『噛む』(舞亚荆棘后露齿一笑) -> 『唇』『噛む』触发轻咬上下内缩 + 绯紫尖牙微痕。
    """
    z = 56

    def __init__(self, jp_line, cn_line, font_jp, font_cn,
                 t_flame=34.292, t_bite=35.30):
        self.jp = jp_line
        self.cn = cn_line
        self.t_flame = t_flame
        self.t_bite = t_bite

        # 预生成紫炎光晕与淡紫染字精灵 (盖在原白字外围与边缘, 平滑过渡)
        self.jp_violet = []
        for i, (s_orig, _, x, y) in enumerate(jp_line.chars):
            ch = jp_line.text[i]
            vs, vg = char_sprites(
                ch, font_jp, fill=(252, 232, 255), glow_col=C.VIOLET_GLOW,
                glow_r=12, outline=2.5, outline_col=(46, 12, 58), shadow_alpha=0.0
            )
            vh = char_halo(ch, font_jp, halo_col=(218, 120, 255), blur_r=9.5)
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            self.jp_violet.append((i, vs, vg, vh, cx - vs.width * 0.5, cy - vs.height * 0.5))

        self.cn_violet = []
        for i, (s_orig, _, x, y) in enumerate(cn_line.chars):
            ch = cn_line.text[i]
            if ch.isspace():
                continue
            vs, vg = char_sprites(
                ch, font_cn, fill=(250, 234, 255), glow_col=C.VIOLET_GLOW,
                glow_r=11, outline=2.5, outline_col=(46, 12, 58),
                shadow_alpha=0.0, synth_bold=C.CN_SYNTH_BOLD
            )
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            self.cn_violet.append((i, vs, vg, cx - vs.width * 0.5, cy - vs.height * 0.5))

        # 升腾紫白妖火微焰粒子 (34.17s ~ 36.1s)
        rng = random.Random(404)
        xs = [x for _, _, x, _ in jp_line.chars]
        x_min, x_max = min(xs), max(xs) + 34
        y_base = jp_line.chars[0][3] + 34
        self.wisps = []
        for k in range(14):
            st = t_flame + k * 0.11 + rng.uniform(0.0, 0.08)
            life = rng.uniform(0.75, 1.15)
            wx = rng.uniform(x_min, x_max)
            wy = y_base + rng.uniform(-4.0, 14.0)
            vy = rng.uniform(-38.0, -22.0)
            sway = rng.uniform(3.5, 7.5)
            rad = rng.uniform(3.0, 5.2)
            self.wisps.append((st, life, wx, wy, vy, sway, rad, k))

        # 挂载『噛む』(最后两字 idx=7,8) 轻咬内缩动作钩子
        bite_indices = {len(jp_line.chars) - 2, len(jp_line.chars) - 1}

        def _bite_hook(i, t):
            if i not in bite_indices:
                return (0.0, 0.0, 1.0)
            dt = t - t_bite
            if 0.0 <= dt <= 0.28:
                pinch = math.sin(math.pi * (dt / 0.28))
                # 两字微微向中间咬合靠拢 + 轻微下顿
                dir_x = 1.8 if i == min(bite_indices) else -1.8
                return (dir_x * pinch, 2.2 * pinch, 1.0)
            return (0.0, 0.0, 1.0)

        jp_line.motion_hook = _bite_hook

    def draw(self, canvas, t):
        if t < self.t_flame or t > self.jp.end + C.FADE_OUT:
            return

        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        if fo <= 0.004:
            return

        # 1) 34.167s 紫炎光晕平滑接管 (0.28s 内切入)
        flame_a = ease_out(clamp01((t - self.t_flame) / 0.28)) * fo
        flicker = 0.88 + 0.12 * math.sin((t - self.t_flame) * 19.0)

        for i, vs, vg, vh, rx, ry in self.jp_violet:
            a_in = clamp01((t - self.jp.t_char[i]) / self.jp.fade_in)
            if a_in <= 0.0:
                continue
            e_in = ease_out(a_in)
            dy = -C.RISE * (1.0 - e_in) + exit_dy
            dx = 0.0
            if self.jp.motion_hook is not None:
                hdx, hdy, _ = self.jp.motion_hook(i, t)
                dx += hdx
                dy += hdy
            st, ed = self.jp.t_syl_span[i]
            sing_p = 0.0
            if st <= t <= ed + 0.14:
                sing_p = math.sin(math.pi * clamp01((t - st) / max(0.2, ed - st + 0.14))) ** 0.75
                dy -= 1.6 * sing_p

            composite_alpha(canvas, vg, rx + dx, ry + dy, flame_a * e_in * flicker)
            if sing_p > 0.02:
                composite_alpha(canvas, vh, rx + dx, ry + dy, flame_a * e_in * sing_p * 0.82)
            composite_alpha(canvas, vs, rx + dx, ry + dy, flame_a * e_in * 0.92)

        for i, vs, vg, rx, ry in self.cn_violet:
            a_in = clamp01((t - self.cn.t_char[i]) / self.cn.fade_in)
            if a_in <= 0.0:
                continue
            e_in = ease_out(a_in)
            dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in)
            composite_alpha(canvas, vg, rx + dx, ry + exit_dy, flame_a * e_in * flicker * 0.9)
            composite_alpha(canvas, vs, rx + dx, ry + exit_dy, flame_a * e_in * 0.88)

        # 2) 升腾紫白妖火微焰
        for st, life, wx0, wy0, vy, sway, rad, seed in self.wisps:
            dt = t - st
            if dt <= 0.0 or dt >= life:
                continue
            u = dt / life
            wa = math.sin(math.pi * u) ** 0.7 * fo * 0.82
            px = wx0 + math.sin(dt * 7.5 + seed) * sway * (0.4 + 0.6 * u)
            py = wy0 + vy * dt + exit_dy
            r_cur = rad * (1.0 - 0.55 * u)
            dim = max(8, int(rad * 6))
            sp = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
            d = ImageDraw.Draw(sp)
            c = dim // 2
            # 纵向拉长的火苗形椭圆
            d.ellipse([c - r_cur * 1.6, c - r_cur * 2.4, c + r_cur * 1.6, c + r_cur * 1.8],
                      fill=(178, 52, 242, int(135 * wa)))
            d.ellipse([c - r_cur * 0.75, c - r_cur * 1.2, c + r_cur * 0.75, c + r_cur * 0.9],
                      fill=(248, 220, 255, int(230 * wa)))
            sp = sp.filter(ImageFilter.GaussianBlur(1.2))
            composite_alpha(canvas, sp, px - c, py - c, 1.0)

        # 3) 35.30s 『噛む』上下轻咬尖牙/荆棘微痕
        dt_b = t - self.t_bite
        if 0.0 <= dt_b <= 0.58 and len(self.jp.chars) >= 2:
            ub = dt_b / 0.58
            snap = ease_out(min(1.0, ub / 0.22))
            fade_b = (1.0 - clamp01((ub - 0.25) / 0.75)) ** 1.5 * fo
            s_b, _, bx0, by0 = self.jp.chars[-2]   # 『噛』
            s_m, _, mx0, _ = self.jp.chars[-1]     # 『む』
            cx = (bx0 + mx0 + s_m.width) * 0.5
            cy = by0 + s_b.height * 0.5 + exit_dy

            SS = 3
            pw, ph = 92, 84
            patch = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
            pd = ImageDraw.Draw(patch)
            ox, oy = pw * 0.5 * SS, ph * 0.5 * SS
            gap = (29.0 - 9.5 * snap) * SS  # 上下向字心咬合收拢

            for dx_off in (-11.0 * SS, 11.0 * SS):
                # 上方尖牙刺痕 (向下刺)
                pd.polygon([
                    (ox + dx_off - 3.2 * SS, oy - gap - 8.5 * SS),
                    (ox + dx_off + 3.2 * SS, oy - gap - 8.5 * SS),
                    (ox + dx_off, oy - gap + 1.5 * SS),
                ], fill=(245, 95, 165, int(225 * fade_b)))
                # 下方尖牙刺痕 (向上刺)
                pd.polygon([
                    (ox + dx_off - 2.8 * SS, oy + gap + 7.5 * SS),
                    (ox + dx_off + 2.8 * SS, oy + gap + 7.5 * SS),
                    (ox + dx_off, oy + gap - 1.5 * SS),
                ], fill=(205, 80, 245, int(215 * fade_b)))

            out_b = patch.resize((pw, ph), Image.Resampling.LANCZOS)
            composite_alpha(canvas, out_b, cx - pw * 0.5, cy - ph * 0.5, 1.0)
