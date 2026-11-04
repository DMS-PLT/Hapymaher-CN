# -*- coding: utf-8 -*-
"""歌词图层: 一行字幕的排版 + 逐字/逐音节入场 + 在唱高光呼吸 + 辉光 + 句尾微飘淡出。

支持模式 (mode):
  "karaoke"  - 日文: 每个字跟随所属 \\k 音节起点上浮淡入, 演唱区间内泛起柔和脉冲光晕
  "cn_slide" - 中文: 逐字微错开左滑 + 字距微收拢入场, 兼具整句可读性与丝滑呼吸感
  "chars"    - 匀速逐字入场, 间隔 CHAR_DELAY
  "whole"    - 整行同时淡入
"""
import math
from .base import Layer, clamp01, ease_out, char_sprites, char_halo, composite_alpha
import config as C


class LyricLine(Layer):
    z = 50

    def __init__(self, line, text, *, font, fill, glow, align, x_edge, y_edge,
                 mode="karaoke", spacing=None, synth_bold=0, halo_col=None):
        self.line = line
        self.start, self.end = line.start, line.end
        if mode == "karaoke" and not line.syls:
            mode = "chars"
        self.mode = mode
        self.text = text
        self.font = font
        self.synth_bold = synth_bold
        self.spacing = C.CHAR_SPACING if spacing is None else spacing
        self.halo_col = halo_col or C.ACTIVE_GLOW
        # 可选钩子: (char_idx, t) -> (dx, dy, extra_alpha_mul) 供特定演出微调单字位移/显隐
        self.motion_hook = None
        # 可选全局遮蔽区间: [(t0, t1), ...] 在反相闪白等特殊帧交由接管层绘制
        self.suppress_spans = []

        widths = [font.getlength(c) for c in text]
        total = sum(widths) + self.spacing * max(0, len(text) - 1)
        x0 = (x_edge - total) if align == "right" else x_edge

        # 每个字: (主精灵, 背板辉光精灵, 左上x, 左上y) —— 保持旧版四元组结构完全兼容!
        self.chars = []
        self.halos = []
        for i, c in enumerate(text):
            s, g = char_sprites(c, font, fill, glow, outline_col=C.OUTLINE,
                                shadow_col=C.SHADOW_COL, synth_bold=synth_bold)
            cx = x0 + sum(widths[:i]) + self.spacing * i + widths[i] / 2
            self.chars.append((s, g, cx - s.width / 2, y_edge))
            self.halos.append(char_halo(c, font, halo_col=self.halo_col, synth_bold=synth_bold))

        # 每个字的入场时刻 & 音节演唱区间 (start, end)
        self.t_syl_span = [(self.start, self.start + 0.35)] * len(text)
        if mode == "karaoke":
            self.fade_in = C.SYL_FADE
            self.t_char, self.t_syl_span = self._map_chars_to_syllables(text, line.syls)
        elif mode == "cn_slide":
            self.t_char = [self.start + i * C.CN_CHAR_STEP for i in range(len(text))]
            self.fade_in = C.LINE_FADE
        elif mode == "chars":
            self.t_char = [self.start + i * C.CHAR_DELAY for i in range(len(text))]
            self.fade_in = C.CHAR_FADE
        else:
            self.t_char = [self.start] * len(text)
            self.fade_in = C.LINE_FADE

    def _map_chars_to_syllables(self, text, syls):
        """把整句里的每个字对到提前导前入场时刻 t_char 与真实演唱高光区间 spans。"""
        raw_st = []
        spans = []
        si = 0
        consumed = 0
        for _ in text:
            if si < len(syls) and consumed >= len(syls[si].text):
                si += 1
                consumed = 0
            s = syls[min(si, len(syls) - 1)]
            st = s.start + consumed * 0.045
            raw_st.append(st)
            spans.append((st, max(st + 0.18, s.end)))
            consumed += 1

        if not raw_st:
            return [], spans

        # 1) 单字入场提前 KARAOKE_LEAD 秒 (首句 L00 前方为空镜可微提前 0.10s, 其余紧接句不早于 self.start)
        min_t0 = (self.start - 0.10) if self.line.li == 0 else self.start
        lead = getattr(C, "KARAOKE_LEAD", 0.26)
        min_dwell = getattr(C, "MIN_FULL_DWELL", 0.34)
        t_char = [max(min_t0, st - lead) for st in raw_st]

        # 2) 保底句尾驻留: 确保最后一字完全浮现后至少有 min_dwell 秒 100% 清晰停留再进入句尾淡出!
        t_fade_start = self.end - C.FADE_OUT
        latest_last = max(min_t0 + 0.15, t_fade_start - self.fade_in - min_dwell)
        if t_char[-1] > latest_last:
            t_char[-1] = latest_last
            for k in range(len(t_char) - 2, -1, -1):
                t_char[k] = min(t_char[k], max(min_t0, t_char[k + 1] - 0.055))

        # 3) 保持从左到右轻盈递进次序
        for k in range(1, len(t_char)):
            if t_char[k] < t_char[k - 1] + 0.030:
                t_char[k] = min(latest_last, t_char[k - 1] + 0.030)

        return t_char, spans

    def draw(self, canvas, t):
        if t < self.start - 0.05 or t > self.end + C.FADE_OUT + 0.05:
            return
        for s0, s1 in self.suppress_spans:
            if s0 <= t <= s1:
                return

        fade_out = 1.0
        exit_drift_y = 0.0
        if t > self.end - C.FADE_OUT:
            u_out = clamp01((t - (self.end - C.FADE_OUT)) / C.FADE_OUT)
            fade_out = 1.0 - ease_out(u_out)
            exit_drift_y = -4.5 * (u_out ** 1.6)

        n_chars = max(1, len(self.chars))
        for i, (s, g, x, y) in enumerate(self.chars):
            if self.text[i].isspace():
                continue
            a_in = clamp01((t - self.t_char[i]) / self.fade_in)
            if a_in <= 0.0:
                continue
            e_in = ease_out(a_in)
            a = e_in * fade_out
            if a <= 0.004:
                continue

            dx, dy = 0.0, exit_drift_y
            if self.mode == "karaoke" or self.mode == "chars":
                dy -= C.RISE * (1.0 - e_in)
            elif self.mode == "cn_slide":
                # 丝滑左滑入场 + 轻微字距聚拢 (越靠右的字初始略多一点间距, 落定后严丝合缝)
                dx -= (C.CN_SLIDE_X + i * 1.4) * (1.0 - e_in)

            if self.motion_hook is not None:
                h_dx, h_dy, h_mul = self.motion_hook(i, t)
                dx += h_dx
                dy += h_dy
                a *= h_mul
                if a <= 0.004:
                    continue

            # 在唱音节脉冲呼吸 (仅日文卡拉OK模式)
            sing_pulse = 0.0
            if self.mode == "karaoke":
                st, ed = self.t_syl_span[i]
                if st <= t <= ed + 0.14:
                    dur = max(0.18, ed - st)
                    u = (t - st) / (dur + 0.14)
                    sing_pulse = math.sin(math.pi * clamp01(u)) ** 0.75
                    dy -= 1.6 * sing_pulse

            px, py = x + dx, y + dy
            composite_alpha(canvas, g, px, py, a)
            if sing_pulse > 0.02:
                composite_alpha(canvas, self.halos[i], px, py, a * sing_pulse * 0.72)
            composite_alpha(canvas, s, px, py, a)
