# -*- coding: utf-8 -*-
"""歌词行渲染层 (支持昼夜双极配色预设、气口空格、卡拉OK在唱呼吸高光与清风波纹退场)。"""
import math
from PIL import Image

import config as C
from effects.base import (
    Layer, clamp01, ease_out, composite_alpha,
    char_sprites, char_halo, apply_rose_breeze,
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
        theme: str = "night",
        is_cn: bool = False,
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
        self.theme_name = theme
        self.is_cn = is_cn
        self.spacing = spacing
        self.synth_bold = synth_bold
        self.slide_dir = slide_dir
        self.z = z
        self.motion_hook = None      # fn(i, t) -> (dx, dy, alpha_mul)
        self.suppress_spans = []     # [(t0, t1), ...]

        th = C.CRIMSON_THEME if theme == "crimson" else C.NIGHT_THEME
        fill_top = th["cn_top"] if is_cn else th["jp_top"]
        fill_bot = th["cn_bot"] if is_cn else th["jp_bot"]
        glow_col = th["glow_cn"] if is_cn else th["glow_jp"]

        self.chars = self._build_chars(
            text, font, anchor_x, y, align, spacing,
            fill_top, fill_bot, glow_col,
            th["outline_w"], th["outline_col"], th["shadow_col"], th["shadow_alpha"],
            th["active_glow"], mode == "karaoke", synth_bold,
        )

        # 包围盒计算
        xs_valid = [px for (s, _, _, px, _, _, _, is_sp) in self.chars if not is_sp]
        ws_valid = [px + s.width for (s, _, _, px, _, _, _, is_sp) in self.chars if not is_sp]
        if xs_valid:
            self.bbox_x0 = int(min(xs_valid) - 24)
            self.bbox_x1 = int(max(ws_valid) + 28)
        else:
            self.bbox_x0, self.bbox_x1 = int(anchor_x - 40), int(anchor_x + 40)
        self.bbox_y0 = int(y - 34)
        self.bbox_y1 = int(y + font.size + 42)

        # 卡拉OK音节映射
        self.char_syl = [None] * len(text)
        if mode == "karaoke" and self.syls:
            ci = 0
            for syl in self.syls:
                for _ in syl.text:
                    if ci < len(text):
                        self.char_syl[ci] = syl
                        ci += 1

    @staticmethod
    def _build_chars(text, font, anchor_x, y, align, spacing,
                     fill_top, fill_bot, glow_col, outline_w, outline_col,
                     shadow_col, shadow_alpha, active_col, make_halo, synth_bold):
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
                    glow_col=glow_col, glow_r=8.8, outline=outline_w,
                    outline_col=outline_col, shadow_col=shadow_col,
                    shadow_alpha=shadow_alpha, synth_bold=synth_bold,
                )
                h = char_halo(ch, font, halo_col=active_col, blur_r=8.2, synth_bold=synth_bold) if make_halo else None
                raw_packs.append((s, g, h))

        total_w = sum(advs) + spacing * max(0, len(text) - 1)
        x0 = anchor_x if align == "left" else (anchor_x - total_w)

        chars = []
        cur_x = x0
        for idx, ch in enumerate(text):
            w_ch = advs[idx]
            s, g, h = raw_packs[idx]
            if s is None:
                chars.append((None, None, None, cur_x, y, cur_x + w_ch * 0.5, y + font.size * 0.5, True))
            else:
                px = cur_x + w_ch * 0.5 - s.width * 0.5
                py = y + font.size * 0.5 - s.height * 0.5
                chars.append((s, g, h, px, py, cur_x + w_ch * 0.5, y + font.size * 0.5, False))
            cur_x += w_ch + spacing
        return chars

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
        if self.mode == "karaoke" and self.char_syl[i] is not None:
            syl = self.char_syl[i]
            pre_u = ease_out(clamp01((t - self.start) / (0.26 + i * 0.014)))
            base_pre = 0.48 if self.theme_name == "crimson" else 0.40
            if t < syl.start:
                a = base_pre * pre_u
                dy = C.RISE * 0.45 * (1.0 - pre_u)
                pulse = 0.0
            else:
                u_on = ease_out(clamp01((t - syl.start) / C.SYL_FADE))
                a = base_pre + (1.0 - base_pre) * u_on
                dy = -3.0 * math.sin(math.pi * clamp01((t - syl.start) / max(0.20, min(0.52, syl.dur))))
                if t <= syl.end + 0.14:
                    u_p = clamp01((t - syl.start) / max(0.15, syl.dur + 0.14))
                    pulse = math.sin(math.pi * u_p) ** 0.75
                else:
                    pulse = 0.0
            dx = 0.0
        else:
            t_ch = self.start + i * C.CN_CHAR_STEP
            u = ease_out(clamp01((t - t_ch) / C.LINE_FADE))
            a = u
            dx = C.CN_SLIDE_X * self.slide_dir * (1.0 - u)
            dy = (1.0 - u) * 3.8
            pulse = 0.0

        if self.motion_hook is not None:
            h_dx, h_dy, h_amul = self.motion_hook(i, t)
            dx += h_dx
            dy += h_dy
            a *= h_amul

        return dx, dy, clamp01(a), pulse

    def render_to_buffer(self, dst_im: Image.Image, t: float, ox: int = 0, oy: int = 0, chars_override=None):
        ch_list = chars_override if chars_override is not None else self.chars
        for i, (s, g, h, px, py, _, _, is_sp) in enumerate(ch_list):
            if is_sp:
                continue
            dx, dy, a, pulse = self.char_state(i, t)
            if a <= 0.004:
                continue
            composite_alpha(dst_im, g, px + dx - ox, py + dy - oy, a)
            if h is not None and pulse > 0.01:
                composite_alpha(dst_im, h, px + dx - ox, py + dy - oy, a * pulse * 0.90)

        for i, (s, g, h, px, py, _, _, is_sp) in enumerate(ch_list):
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
            bx0 = max(0, self.bbox_x0 - 24)
            by0 = max(0, self.bbox_y0 - 16)
            bx1 = min(canvas.width, self.bbox_x1 + 24)
            by1 = min(canvas.height, self.bbox_y1 + 16)
            bw, bh = max(8, bx1 - bx0), max(8, by1 - by0)
            strip = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            self.render_to_buffer(strip, t, bx0, by0)
            breeze_dir = 1.0 if self.align == "left" else -1.0
            warped = apply_rose_breeze(strip, u_exit, phase_seed=self.start * 2.9, dir_x=breeze_dir)
            composite_alpha(canvas, warped, bx0, by0 - 5.5 * (u_exit ** 1.3), 1.0)
