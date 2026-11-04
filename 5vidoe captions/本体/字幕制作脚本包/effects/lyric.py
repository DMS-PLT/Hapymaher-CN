# -*- coding: utf-8 -*-
"""歌词行渲染层 (支持左右对齐、半句气口空格、在唱呼吸高光与原生水波烟散退场)。"""
import math
from PIL import Image

import config as C
from effects.base import (
    Layer, clamp01, ease_out, composite_alpha,
    char_sprites, char_halo, apply_water_smoke,
)


class LyricLine(Layer):
    z = 30

    def __init__(
        self,
        text: str,
        font,
        anchor_x: float,
        y: float,
        start: float,
        end: float,
        align: str = "left",
        mode: str = "karaoke",
        syls=None,
        fill_top=C.JP_TOP_COL,
        fill_bot=C.JP_BOT_COL,
        glow_col=C.GLOW_JP,
        active_col=C.ACTIVE_GLOW,
        spacing: float = C.CHAR_SPACING_JP,
        synth_bold: int = 0,
        slide_dir: float = 1.0,
        z: int = 30,
    ):
        self.text = text
        self.font = font
        self.anchor_x = anchor_x
        self.y = y
        self.start = start
        self.end = end
        self.align = align
        self.mode = mode
        self.syls = syls or []
        self.spacing = spacing
        self.synth_bold = synth_bold
        self.slide_dir = slide_dir
        self.z = z
        self.motion_hook = None      # fn(i, t) -> (dx, dy, alpha_mul)
        self.suppress_spans = []     # [(t0, t1), ...]

        # 逐字排版与精灵预缓存 (句中空格占半角气口宽度, 不生成精灵)
        advs = []
        raw_packs = []
        space_w = font.size * C.SPACE_ADV_RATIO
        for ch in text:
            if ch == " ":
                advs.append(space_w)
                raw_packs.append((None, None, None))
            else:
                adv = font.getlength(ch)
                advs.append(adv)
                s, g = char_sprites(
                    ch, font, fill_top=fill_top, fill_bot=fill_bot,
                    glow_col=glow_col, glow_r=9.0, outline=2.4,
                    outline_col=C.OUTLINE_COL, shadow_col=C.SHADOW_COL,
                    shadow_alpha=0.70, synth_bold=synth_bold,
                )
                h = char_halo(ch, font, halo_col=active_col, blur_r=8.5, synth_bold=synth_bold) if mode == "karaoke" else None
                raw_packs.append((s, g, h))

        total_w = sum(advs) + spacing * max(0, len(text) - 1)
        x0 = anchor_x if align == "left" else (anchor_x - total_w)

        self.chars = []  # [(sprite, glow, halo, x_draw, y_draw, cx, cy, is_space)]
        cur_x = x0
        for idx, ch in enumerate(text):
            w_ch = advs[idx]
            s, g, h = raw_packs[idx]
            if s is None:
                self.chars.append((None, None, None, cur_x, y, cur_x + w_ch * 0.5, y + font.size * 0.5, True))
            else:
                px = cur_x + w_ch * 0.5 - s.width * 0.5
                py = y + font.size * 0.5 - s.height * 0.5
                self.chars.append((s, g, h, px, py, cur_x + w_ch * 0.5, y + font.size * 0.5, False))
            cur_x += w_ch + spacing

        self.bbox_x0 = int(x0 - 36)
        self.bbox_x1 = int(x0 + total_w + 48)
        self.bbox_y0 = int(y - 34)
        self.bbox_y1 = int(y + font.size + 42)

        # 卡拉OK音节映射到字符索引
        self.char_syl = [None] * len(text)
        if mode == "karaoke" and self.syls:
            ci = 0
            for syl in self.syls:
                for _ in syl.text:
                    if ci < len(text):
                        self.char_syl[ci] = syl
                        ci += 1

    def is_active(self, t: float) -> bool:
        if t < self.start or t > self.end:
            return False
        for a, b in self.suppress_spans:
            if a <= t <= b:
                return False
        return True

    def exit_progress(self, t: float) -> float:
        if t <= self.end - C.FADE_OUT:
            return 0.0
        return clamp01((t - (self.end - C.FADE_OUT)) / C.FADE_OUT)

    def char_state(self, i: int, t: float):
        """返回第 i 个字符在时刻 t 的 (dx, dy, alpha, active_pulse) [不含句尾水波退场]。"""
        if self.mode == "karaoke" and self.char_syl[i] is not None:
            syl = self.char_syl[i]
            # 整句提前轻柔铺底微显 (0.24 alpha), 唱到时亮起上浮!
            pre_u = ease_out(clamp01((t - self.start) / (0.28 + i * 0.015)))
            if t < syl.start:
                a = 0.28 * pre_u
                dy = C.RISE * 0.45 * (1.0 - pre_u)
                pulse = 0.0
            else:
                u_on = ease_out(clamp01((t - syl.start) / C.SYL_FADE))
                a = 0.28 + 0.72 * u_on
                dy = -3.2 * math.sin(math.pi * clamp01((t - syl.start) / max(0.22, min(0.55, syl.dur))))
                if t <= syl.end + 0.14:
                    u_p = clamp01((t - syl.start) / max(0.16, syl.dur + 0.14))
                    pulse = math.sin(math.pi * u_p) ** 0.75
                else:
                    pulse = 0.0
            dx = 0.0
        else:
            # 中文级联滑入 + 字距微聚拢
            t_ch = self.start + i * C.CN_CHAR_STEP
            u = ease_out(clamp01((t - t_ch) / C.LINE_FADE))
            a = u
            dx = C.CN_SLIDE_X * self.slide_dir * (1.0 - u)
            dy = (1.0 - u) * 4.0
            pulse = 0.0

        if self.motion_hook is not None:
            h_dx, h_dy, h_amul = self.motion_hook(i, t)
            dx += h_dx
            dy += h_dy
            a *= h_amul

        return dx, dy, clamp01(a), pulse

    def render_to_buffer(self, dst_im: Image.Image, t: float, ox: int = 0, oy: int = 0):
        """将当前时刻未退场的字形绘制到指定画布 (偏移 -ox, -oy)。"""
        # 第一遍: 辉光 + 在唱光晕
        for i, (s, g, h, px, py, _, _, is_sp) in enumerate(self.chars):
            if is_sp:
                continue
            dx, dy, a, pulse = self.char_state(i, t)
            if a <= 0.004:
                continue
            composite_alpha(dst_im, g, px + dx - ox, py + dy - oy, a)
            if h is not None and pulse > 0.01:
                composite_alpha(dst_im, h, px + dx - ox, py + dy - oy, a * pulse * 0.92)

        # 第二遍: 清晰字芯 (保证邻字辉光绝不遮盖本字笔画)
        for i, (s, g, h, px, py, _, _, is_sp) in enumerate(self.chars):
            if is_sp:
                continue
            dx, dy, a, _ = self.char_state(i, t)
            if a <= 0.004:
                continue
            composite_alpha(dst_im, s, px + dx - ox, py + dy - oy, a)

    def draw(self, canvas: Image.Image, t: float):
        if not self.is_active(t):
            return

        u_exit = self.exit_progress(t)
        if u_exit <= 0.005:
            self.render_to_buffer(canvas, t, 0, 0)
        else:
            # 句尾原生『横向正弦水波纹扭曲 + 青烟上浮消散』!
            bx0 = max(0, self.bbox_x0 - 20)
            by0 = max(0, self.bbox_y0 - 16)
            bx1 = min(canvas.width, self.bbox_x1 + 20)
            by1 = min(canvas.height, self.bbox_y1 + 16)
            bw, bh = max(8, bx1 - bx0), max(8, by1 - by0)
            strip = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            self.render_to_buffer(strip, t, bx0, by0)
            warped = apply_water_smoke(strip, u_exit, phase_seed=self.start * 3.1)
            smoke_dy = -8.0 * (u_exit ** 1.25)
            composite_alpha(canvas, warped, bx0, by0 + smoke_dy, 1.0)
