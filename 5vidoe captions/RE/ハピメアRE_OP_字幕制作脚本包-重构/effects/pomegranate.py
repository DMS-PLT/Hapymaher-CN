# -*- coding: utf-8 -*-
"""石榴渗红层 (有机墨汁晕染遮罩 + 欲滴红珠升级版)。

用于 "赤く滲むザクロ" / "石榴果渗出的红色":
  - 不再是整字生硬平涂变色, 而是用多波叠加的有机渗染场从笔画中下部向外晕开;
  - 在重点字 ("滲", "ロ", "渗", "红") 底部凝结细小深红果汁珠并缓缓垂落消散。
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from .base import Layer, clamp01, ease_out, char_sprites, composite_alpha
import config as C


class RedBleed(Layer):
    z = 55   # 盖在白字(50)之上

    def __init__(self, lyric_line, font, red_fill=(255, 74, 96), glow=(245, 36, 68),
                 char_indices=None, delay=0.06, bleed_dur=0.62,
                 drip_indices=None, synth_bold=0):
        self.line = lyric_line
        self.start, self.end = lyric_line.start, lyric_line.end
        red = red_fill or C.RED_FILL
        indices = set(range(len(lyric_line.chars))) if char_indices is None else set(char_indices)
        self.bleed_dur = bleed_dur

        self.items = []   # (rs_arr, rg, field, x, y, ta, ch_idx)
        self.drips = []   # (cx, bottom_y, t_drip_start, seed)

        for i, (s, g, x, y) in enumerate(lyric_line.chars):
            if i not in indices or lyric_line.text[i].isspace():
                continue
            ch = lyric_line.text[i]
            # 石榴籽透光宝石红: 鲜亮绯红字芯 + 深红黑描边 + 饱满绯红辉光, 暗场下依然通透发亮
            rs, rg = char_sprites(
                ch, font, red, glow, glow_r=12,
                outline=2.5, outline_col=(42, 8, 16), shadow_alpha=0.35, synth_bold=synth_bold
            )
            # 笔画上半部略带暖粉红高光渐变, 模拟石榴汁液通透感
            rs_np = np.array(rs)
            h_s = rs_np.shape[0]
            grad = np.linspace(1.0, 0.0, h_s, dtype=np.float32)[:, None]
            alpha_mask = rs_np[..., 3] > 140
            # 仅提亮红字内部亮部像素(避开深色描边)
            inner_mask = alpha_mask & (rs_np[..., 0] > 150)
            boost = (grad * 58.0).astype(np.float32)
            rs_np[..., 0] = np.where(inner_mask, np.clip(rs_np[..., 0] + boost * 0.4, 0, 255), rs_np[..., 0]).astype(np.uint8)
            rs_np[..., 1] = np.where(inner_mask, np.clip(rs_np[..., 1] + boost * 1.15, 0, 255), rs_np[..., 1]).astype(np.uint8)
            rs_np[..., 2] = np.where(inner_mask, np.clip(rs_np[..., 2] + boost * 1.10, 0, 255), rs_np[..., 2]).astype(np.uint8)
            ta = lyric_line.t_char[i] + delay
            cx = x + s.width / 2
            rx = cx - rs.width / 2
            ry = y - (rs.height - s.height) / 2

            # 预计算有机渗染场 field (0..1): 底部/中心数值小(先渗出), 顶部边缘数值大(后染透)
            h, w = rs.height, rs.width
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            nx = (xx - w * 0.5) / max(1.0, w * 0.36)
            ny = (yy - h * 0.62) / max(1.0, h * 0.38)
            dist = np.sqrt(nx * nx * 0.65 + ny * ny * 0.85)
            # 叠加柔和有机波纹, 让渗红边缘呈水墨毛细扩散状
            phase = i * 1.73
            wave = (
                0.14 * np.sin(xx * 0.24 + phase)
                + 0.11 * np.cos(yy * 0.29 - phase * 0.7)
                + 0.08 * np.sin((xx + yy) * 0.18 + phase * 1.3)
            )
            # 偏下先红, 向上蔓延
            field = np.clip(0.45 * dist + 0.30 * (1.0 - yy / max(1.0, h)) + wave, 0.0, 1.0)
            f_min, f_max = float(field.min()), float(field.max())
            if f_max > f_min + 1e-4:
                field = (field - f_min) / (f_max - f_min)

            self.items.append((rs_np, rg, field, rx, ry, ta, i))

            # 若指定该字滴落石榴汁珠, 算出笔画真实底端位置
            if drip_indices and i in drip_indices:
                alpha_s = np.array(s)[..., 3]
                ys_nz, xs_nz = np.where(alpha_s > 60)
                if len(ys_nz) > 0:
                    bx = x + float(np.median(xs_nz)) + ((i % 2) * 4 - 2)
                    by = y + float(ys_nz.max()) - 1.0
                    self.drips.append((bx, by, ta + 0.26, i))

    def draw(self, canvas, t):
        if t < self.start or t > self.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.end - C.FADE_OUT:
            u_out = clamp01((t - (self.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        if fo <= 0.004:
            return

        for rs_arr, rg, field, x, y, ta, i in self.items:
            u = clamp01((t - ta) / self.bleed_dur)
            if u <= 0.0:
                continue
            prog = ease_out(u)

            # 跟随原歌词行的入场上浮/左滑位移, 确保红字与白字像素级严丝合缝!
            a_in = clamp01((t - self.line.t_char[i]) / self.line.fade_in)
            e_in = ease_out(a_in)
            dx, dy = 0.0, exit_dy
            if self.line.mode in ("karaoke", "chars"):
                dy -= C.RISE * (1.0 - e_in)
            elif self.line.mode == "cn_slide":
                dx -= (C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in)

            # 1) 红辉光柔和渐起
            composite_alpha(canvas, rg, x + dx, y + dy, prog * fo * 0.88)

            # 2) 有机毛细扩散遮罩: 软羽化宽度 0.28, prog=1 时完全覆盖整字
            mask = np.clip((prog * 1.28 - field) / 0.28, 0.0, 1.0)
            cur = rs_arr.copy()
            cur[..., 3] = (cur[..., 3].astype(np.float32) * mask * fo).astype(np.uint8)
            composite_alpha(canvas, Image.fromarray(cur), x + dx, y + dy, 1.0)

        # 3) 欲滴石榴红珠 (小巧克制: 凝珠 -> 缓坠 14px -> 拉丝消散)
        for bx, by, td, seed in self.drips:
            du = (t - td) / 1.15
            if du <= 0.0 or du >= 1.0:
                continue
            # 前 30% 在笔画底端凝结变大, 后 70% 缓慢下坠消融
            if du < 0.28:
                grow = du / 0.28
                drop_y = grow * 1.8
                rad = 1.4 + 1.5 * grow
                da = grow * fo
            else:
                fall = (du - 0.28) / 0.72
                drop_y = 1.8 + (fall ** 1.75) * 15.0
                rad = 2.9 * (1.0 - 0.45 * fall)
                da = (1.0 - fall ** 1.4) * fo

            SS = 3
            pw, ph = 20, 34
            patch = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
            pd = ImageDraw.Draw(patch)
            cx2, cy2 = 10 * SS, int((4 + drop_y) * SS)
            r2 = max(2, int(rad * SS))
            # 细微液丝尾迹
            if drop_y > 2.2:
                pd.line([cx2, int(4 * SS), cx2, cy2],
                        fill=(175, 22, 42, int(115 * da)), width=max(1, SS - 1))
            # 外层暗红光晕 + 深红珠体 + 微小高光点
            pd.ellipse([cx2 - r2 - 2, cy2 - r2 - 2, cx2 + r2 + 2, cy2 + r2 + 2],
                       fill=(190, 26, 48, int(95 * da)))
            pd.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2],
                       fill=(228, 38, 60, int(235 * da)))
            pd.ellipse([cx2 - r2 // 2, cy2 - r2 // 2, cx2, cy2],
                       fill=(255, 195, 205, int(170 * da)))
            p1 = patch.resize((pw, ph), Image.Resampling.LANCZOS)
            composite_alpha(canvas, p1, bx - 10, by - 3 + exit_dy, 1.0)
