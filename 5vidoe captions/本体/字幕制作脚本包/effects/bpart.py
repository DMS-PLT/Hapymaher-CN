# -*- coding: utf-8 -*-
"""本体 OP B段 (L04 ~ L05, 44.57s ~ 63.48s) 红黑棋盘坠落与五女主蔷薇巡礼演出。

包含两组高定制舞台图层:
  1. CheckerboardChaseEscape (L04: 追いかける ほどに逃げていく / 越是执着追逐 便越是远逃而去, 右上双行并列)
     - 暗丝绒柔光衬底护盾 (确保在有栖红白高亮棋盘上依然具备剧院级锐利反差)
     - 西洋菱格暗金双行分隔丝线 + 48.42s 角色切镜处红白棋盘菱形翻转涟漪
     - 追逃字距动力学: 前半『追いかける / 执着追逐』微倾紧追; 49.64s 唱响『逃げていく / 远逃而去』时
       句尾字符向左加速拉开逃逸, 并在身后剥落半透明蔷薇残影!
  2. HeroineTriadOverexpose  (L05: 恋と 同じ 皮肉なものね / 就如同恋情一般 真是讽刺呢, 左上双行并列)
     - 随三位女主切镜丝滑流转代表色暗纹与花瓣微尘:
         * 52.94s ~ 56.58s 弥生 (绯红兔耳暗纹)
         * 56.58s ~ 60.40s 景子 (翠玉薄荷流光 + 双行分隔弦线在 57.15s/58.15s 如吉他琴弦般拨动震颤!)
         * 60.40s ~ 63.15s 舞亚 (哥特暗紫幽光 + 『皮肉 / 讽刺』冷艳微芒)
     - 63.12s ~ 63.58s 完美咬合原片冲入副歌的纯白强光爆闪: 隐去暗色描边, 化作圣洁纯白过曝流光消融于白幕!
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out,
    composite_alpha, char_sprites, char_halo,
)


# =====================================================================
#  [L04] 右上哥特双行衬底 + 棋盘菱形切镜涟漪 + 『逃げていく』拉开残影逃逸!
# =====================================================================
class CheckerboardChaseEscape(Layer):
    z = 26  # 衬底与分隔丝线在 z=26, 残影与前景菱形通过双层或同层叠绘呈现

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end
        self.t_wipe = 48.42     # 有栖 -> 莲乃咲 红白棋盘翻转切镜时刻
        self.t_escape = 49.62   # 『逃げていく』起唱时刻

        # 右上双行并列联合包围盒 (用于暗丝绒柔光衬底与菱格分隔线)
        self.x0 = min(jp_line.bbox_x0, cn_line.bbox_x0) + 18
        self.x1 = max(jp_line.bbox_x1, cn_line.bbox_x1) - 18
        self.y_mid = 0.5 * (jp_line.y + jp_line.font.size + cn_line.y) + 2

        # 预烘暗红黑丝绒羽化衬底板 (对抗 45.0s~48.4s 有栖背景高亮白棋盘格的眩光)
        self.velvet_pad = self._build_velvet_pad(
            w=int(self.x1 - self.x0 + 96), h=156
        )

        # 追逃动力学 motion_hook:
        #   - 右对齐下, 向左逃离屏幕外侧即 dx < 0, 且越靠左的字或按逃跑顺序拉开字距!
        #   - 注意: 『逃(9)げ(10)て(11)い(12)く(13)』在右对齐行位于最右侧, 若让『逃げていく』整体向右或向左?
        #     右对齐时左侧是空白暗纹区! 让前半句微追而『逃げていく / 远逃而去』逐字向右散开或向左飘离?
        #     等等: 屏幕右边缘 x=1836 只剩 84px 裕量; 而左侧 x=1160 往左有整片 1000px 广阔空间!
        #     更妙的是: 如果前半句『追いかける ほどに』在 49.6s 起向左下方微沉, 而『逃げていく』(9..13)
        #     逐字向上/向右微扬并拉开字距 (控制在 +42px 安全区内, 绝不出画!), 视觉上就像句尾正从掌心向画外挣脱溜走!
        def _jp_hook(i, t):
            dx, dy = 0.0, 0.0
            # 前半『追いかける (0..4)』唱到时轻微向右前倾追赶 (+4px)
            if i <= 4 and t >= self.start + 0.15:
                u_ch = ease_out(clamp01((t - (self.start + i * 0.16)) / 0.35))
                chase_relax = 1.0 - 0.5 * clamp01((t - self.t_escape) / 1.2)
                dx += 4.5 * u_ch * chase_relax
            # 后半『逃げていく (9..13)』从 49.62s 起逐字向右上方加速挣脱拉开字距!
            if i >= 9 and t >= self.t_escape:
                k = i - 9  # 0..4
                u_esc = ease_out(clamp01((t - (self.t_escape + k * 0.14)) / 1.45))
                dx += (6.0 + k * 7.8) * u_esc       # 最末字『く』+37px -> x≈1873 仍在 1920 安全区内!
                dy += -(2.0 + k * 2.2) * u_esc      # 轻盈向上飘离
            return (dx, dy, 1.0)

        def _cn_hook(i, t):
            dx, dy = 0.0, 0.0
            if i <= 5 and t >= self.start + 0.20:
                u_ch = ease_out(clamp01((t - (self.start + 0.20 + i * 0.08)) / 0.40))
                chase_relax = 1.0 - 0.5 * clamp01((t - self.t_escape) / 1.2)
                dx += 4.0 * u_ch * chase_relax
            # 中文『远逃而去 (10..13)』同步挣脱拉开字距!
            if i >= 10 and t >= self.t_escape + 0.06:
                k = i - 10  # 0..3
                u_esc = ease_out(clamp01((t - (self.t_escape + 0.06 + k * 0.16)) / 1.45))
                dx += (7.0 + k * 9.0) * u_esc
                dy += (1.8 + k * 1.8) * u_esc       # 与上方日文微呈上下分道扬镳之势!
            return (dx, dy, 1.0)

        jp_line.motion_hook = _jp_hook
        cn_line.motion_hook = _cn_hook

        # 蔷薇暗纹花瓣微粒
        rng = random.Random(4457)
        self.petals = []
        for _ in range(10):
            self.petals.append((
                rng.uniform(self.start + 0.2, self.end - 1.1),
                rng.uniform(1.5, 2.4),
                rng.uniform(self.x0 + 30, self.x1 - 20),
                rng.uniform(42.0, 150.0),
                rng.uniform(-28.0, -10.0),
                rng.uniform(12.0, 26.0),
                rng.uniform(4.2, 6.8),
                rng.uniform(0.0, math.tau),
                rng.uniform(-3.2, 3.2),
            ))

    @staticmethod
    def _build_velvet_pad(w: int, h: int) -> Image.Image:
        im = Image.new("RGBA", (w, h), (22, 6, 14, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([24, 18, w - 24, h - 18], radius=28, fill=(22, 6, 14, 155))
        return im.filter(ImageFilter.GaussianBlur(16.0))

    def _draw_divider_and_wipe(self, canvas: Image.Image, t: float, fo: float):
        SS = 2
        w = int(self.x1 - self.x0 + 40)
        h = 34
        im = Image.new("RGBA", (w * SS, h * SS), (225, 175, 188, 0))
        d = ImageDraw.Draw(im)
        cy = (h // 2) * SS

        a_in = ease_out(clamp01((t - self.start) / 0.50)) * fo
        line_col = (224, 168, 184, int(145 * a_in))
        gem_col = (248, 212, 220, int(215 * a_in))

        # 纤细哥特双侧渐隐丝线 + 中央/两端西洋棋盘小菱星
        lx0 = int(16 * SS * (1.0 - 0.3 * (1.0 - a_in)))
        lx1 = w * SS - lx0
        mid_x = (w * SS) // 2
        d.line([(lx0, cy), (mid_x - 12 * SS, cy)], fill=line_col, width=2)
        d.line([(mid_x + 12 * SS, cy), (lx1, cy)], fill=line_col, width=2)

        for cx_d, r_d in ((lx0, 3.5), (mid_x, 5.2), (lx1, 3.5)):
            rr = r_d * SS
            d.polygon([(cx_d, cy - rr), (cx_d + rr, cy), (cx_d, cy + rr), (cx_d - rr, cy)], fill=gem_col)

        # 48.42s ~ 49.25s: 咬合有栖->咲切镜的红白西洋棋盘菱形翻转波!
        dt_w = t - self.t_wipe
        if 0.0 <= dt_w <= 0.85:
            n_tiles = 9
            for k in range(n_tiles):
                # 从右向左依次翻转掠过
                tk = dt_w - k * 0.048
                if 0.0 <= tk <= 0.46:
                    u = tk / 0.46
                    spin_w = abs(math.cos(u * math.pi))  # 3D 翻面宽度缩放 1 -> 0 -> 1
                    ta = math.sin(u * math.pi) * fo
                    tx = lx1 - (lx1 - lx0) * (k / (n_tiles - 1))
                    rx = max(1.5, 7.5 * spin_w) * SS
                    ry = 7.5 * SS
                    is_red = ((k + (1 if u > 0.5 else 0)) % 2 == 0)
                    t_col = (228, 28, 58, int(235 * ta)) if is_red else (255, 246, 248, int(235 * ta))
                    d.polygon([(tx, cy - ry), (tx + rx, cy), (tx, cy + ry), (tx - rx, cy)], fill=t_col)

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, self.x0 - 20, self.y_mid - h * 0.5, 1.0)

    def _draw_escape_ghosts(self, canvas: Image.Image, t: float, fo: float):
        """49.62s 起在向右上方挣脱逃逸的『逃げていく / 远逃而去』原位与半途留下淡蔷薇残影!"""
        if t < self.t_escape:
            return
        dt = t - self.t_escape
        if dt > 2.6:
            return
        ghost_a = math.sin(math.pi * clamp01(dt / 2.6)) * 0.34 * fo
        if ghost_a <= 0.01:
            return

        for line, start_idx in ((self.jp, 9), (self.cn, 10)):
            for i in range(start_idx, len(line.chars)):
                s, g, _, px, py, _, _, is_sp = line.chars[i]
                if is_sp:
                    continue
                dx, dy, a_ch, _ = line.char_state(i, t)
                if dx < 3.0 or a_ch <= 0.05:
                    continue
                # 两级滞后残影 (35% 位移处与 68% 位移处)
                composite_alpha(canvas, g, px + dx * 0.32, py + dy * 0.32, ghost_a * 0.85)
                composite_alpha(canvas, s, px + dx * 0.32, py + dy * 0.32, ghost_a * 0.55)
                composite_alpha(canvas, s, px + dx * 0.66, py + dy * 0.66, ghost_a * 0.35)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        u_exit = self.jp.exit_progress(t)
        fo = 1.0 - ease_in_out(u_exit)
        if fo <= 0.01:
            return

        # 1) 44.6s ~ 48.8s 有栖高亮棋盘段叠暗丝绒柔光护盾, 48.8s 切入咲的暗红绸缎底后自然减淡
        a_in = ease_out(clamp01((t - self.start) / 0.40))
        alice_weight = 1.0 - 0.45 * clamp01((t - 48.65) / 0.50)
        composite_alpha(canvas, self.velvet_pad, self.x0 - 48, 22, a_in * alice_weight * fo)

        # 2) 西洋双行菱格丝线 + 48.42s 红白棋盘翻转波
        self._draw_divider_and_wipe(canvas, t, fo)

        # 3) 『逃げていく / 远逃而去』挣脱残影
        if u_exit < 0.15:
            self._draw_escape_ghosts(canvas, t, fo)

        # 4) 飘零暗红蔷薇花瓣微粒
        p_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
        pd = ImageDraw.Draw(p_layer)
        has_p = False
        for tb, life, x0, y0, vx, vy, rad, ang0, vang in self.petals:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                pa = math.sin(math.pi * u) * 0.72 * fo
                if pa > 0.02:
                    has_p = True
                    x = x0 + vx * age + 5.0 * math.sin(age * 4.2 + ang0)
                    y = y0 + vy * age
                    ang = ang0 + vang * age
                    ca, sa = math.cos(ang), math.sin(ang)
                    rx, ry = rad * 1.35, rad * 0.72
                    pd.polygon([
                        (x + ca * rx, y + sa * rx),
                        (x - sa * ry, y + ca * ry),
                        (x - ca * rx * 0.85, y - sa * rx * 0.85),
                        (x + sa * ry, y - ca * ry),
                    ], fill=(214, 28, 58, int(220 * pa)))
        if has_p:
            canvas.alpha_composite(p_layer)


# =====================================================================
#  [L05] 三女主代表色流转 + 景子吉他拨弦共振 + 63.12s 纯白圣光过曝消融!
# =====================================================================
class HeroineTriadOverexpose(Layer):
    z = 36

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.t_keiko = 56.58        # 弥生 -> 景子切镜
        self.t_maia = 60.38         # 景子 -> 舞亚切镜
        self.t_white = 63.30        # 精准卡在舞亚横向亮线起爆 (63.33s) -> 全白强光爆闪 (63.50s)!
        self.white_end = 63.64

        # 在 63.10s 之后接管底层暗描边字幕, 改绘无暗边纯白过曝消融层 (彻底杜绝白场上的黑边灰影!)
        jp_line.suppress_spans.append((self.t_white, jp_line.end + 0.1))
        cn_line.suppress_spans.append((self.t_white, cn_line.end + 0.1))

        self.x0 = min(jp_line.bbox_x0, cn_line.bbox_x0) + 22
        self.x1 = max(jp_line.bbox_x1, cn_line.bbox_x1) - 22
        self.y_mid = 0.5 * (jp_line.y + jp_line.font.size + cn_line.y) + 2

        # 预缓存三女主代表色微光晕 (弥生绯红 / 景子翠玉薄荷 / 舞亚哥特暗紫)
        self.jp_halos_keiko = self._prep_line_halos(jp_line, font_jp, (64, 236, 192), 9.5, 0)
        self.cn_halos_keiko = self._prep_line_halos(cn_line, font_cn, (64, 236, 192), 9.0, C.CN_SYNTH_BOLD)
        self.jp_halos_maia = self._prep_line_halos(jp_line, font_jp, (192, 68, 248), 10.0, 0)
        self.cn_halos_maia = self._prep_line_halos(cn_line, font_cn, (192, 68, 248), 9.5, C.CN_SYNTH_BOLD)

        # 预缓存 63.10s~63.58s 纯白圣光无黑边字形精灵 (用于融入原片白场爆闪!)
        self.jp_pure_white = self._prep_pure_white(jp_line, font_jp, 0)
        self.cn_pure_white = self._prep_pure_white(cn_line, font_cn, C.CN_SYNTH_BOLD)

    @staticmethod
    def _prep_line_halos(line, font, col, br, sb):
        out = {}
        for i, (s, _, _, px, py, cx, cy, is_sp) in enumerate(line.chars):
            if not is_sp:
                h = char_halo(line.text[i], font, halo_col=col, blur_r=br, synth_bold=sb)
                out[i] = (h, cx - h.width * 0.5, cy - h.height * 0.5)
        return out

    @staticmethod
    def _prep_pure_white(line, font, sb):
        out = []
        for i, (s_orig, _, _, px, py, cx, cy, is_sp) in enumerate(line.chars):
            if is_sp:
                out.append(None)
                continue
            s_w, g_w = char_sprites(
                line.text[i], font,
                fill_top=(255, 255, 255), fill_bot=(255, 250, 254),
                glow_col=(255, 228, 242), glow_r=12.0,
                outline=1.2, outline_col=(255, 245, 250),
                shadow_col=(255, 255, 255), shadow_alpha=0.0,
                synth_bold=sb,
            )
            out.append((s_w, g_w, cx - s_w.width * 0.5, cy - s_w.height * 0.5))
        return out

    def _heroine_color(self, t: float):
        """平滑插值当前时刻的三女主主题色: 弥生(绯红) -> 景子(翠玉薄荷) -> 舞亚(哥特紫红)。"""
        c_yayoi = np.array([238.0, 56.0, 96.0])
        c_keiko = np.array([72.0, 236.0, 192.0])
        c_maia = np.array([196.0, 74.0, 248.0])
        if t < self.t_keiko:
            col = c_yayoi
        elif t < self.t_maia:
            u = ease_in_out(clamp01((t - self.t_keiko) / 0.55))
            col = c_yayoi * (1.0 - u) + c_keiko * u
        else:
            u = ease_in_out(clamp01((t - self.t_maia) / 0.55))
            col = c_keiko * (1.0 - u) + c_maia * u
        return tuple(int(round(v)) for v in col)

    def _draw_guitar_string_divider(self, canvas: Image.Image, t: float, alpha_mul: float):
        """绘制双行间哥特丝线: 在景子登场 (56.8s~60.2s) 尤其是『皮肉な』(58.12s) 处如吉他琴弦般拨动震颤!"""
        SS = 2
        w = int(self.x1 - self.x0 + 36)
        h = 36
        col = self._heroine_color(t)
        im = Image.new("RGBA", (w * SS, h * SS), (*col, 0))
        d = ImageDraw.Draw(im)
        cy = (h // 2) * SS
        lx0 = 14 * SS
        lx1 = (w - 14) * SS

        # 计算吉他琴弦驻波振幅 (三次拨弦共振: 56.95s 景子入场 / 58.12s『皮肉な』/ 59.10s 余韵拨弦)
        vib_amp = 0.0
        for t_pluck, max_a in ((56.95, 8.2), (58.12, 9.8), (59.15, 6.8)):
            dt_p = t - t_pluck
            if 0.0 <= dt_p <= 1.35:
                vib_amp += max_a * math.exp(-dt_p * 2.8) * math.sin(dt_p * 36.0)

        a_line = int(190 * alpha_mul)
        a_gem = int(235 * alpha_mul)
        n_seg = 56
        # 若琴弦正在振动, 先叠一条反相半透明泛音弦影以强化肉眼可见的拨弦残影感!
        if abs(vib_amp) > 0.6:
            pts_echo = []
            for k in range(n_seg + 1):
                u = k / n_seg
                px = lx0 + (lx1 - lx0) * u
                env = math.sin(math.pi * u)
                py = cy - (vib_amp * 0.65 * env) * SS
                pts_echo.append((px, py))
            d.line(pts_echo, fill=(*col, int(a_line * 0.48)), width=2)

        pts = []
        for k in range(n_seg + 1):
            u = k / n_seg
            px = lx0 + (lx1 - lx0) * u
            # 两端固定、中央最大振幅的琴弦一阶+二阶驻波!
            env = math.sin(math.pi * u)
            py = cy + (vib_amp * env + 0.25 * vib_amp * math.sin(2 * math.pi * u)) * SS
            pts.append((px, py))
        d.line(pts, fill=(*col, a_line), width=2)

        # 两端哥特小菱钻
        for cx_d in (lx0, lx1):
            rr = 4.0 * SS
            d.polygon([(cx_d, cy - rr), (cx_d + rr, cy), (cx_d, cy + rr), (cx_d - rr, cy)],
                      fill=(255, 240, 248, a_gem))

        # 56.60s & 60.40s 两次切镜瞬间沿弦线滑过一颗高光流星星芒!
        for t_sw in (self.t_keiko, self.t_maia):
            dt_s = t - t_sw
            if 0.0 <= dt_s <= 0.55:
                us = ease_out(dt_s / 0.55)
                sx = lx0 + (lx1 - lx0) * us
                sa = int(245 * math.sin(math.pi * (dt_s / 0.55)) * alpha_mul)
                rr = 6.5 * SS
                d.ellipse([sx - rr, cy - rr, sx + rr, cy + rr], fill=(255, 255, 255, sa))

        out = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, self.x0 - 18, self.y_mid - h * 0.5, 1.0)

    def _draw_white_overexpose_exit(self, canvas: Image.Image, t: float):
        """63.10s ~ 63.58s: 将底层暗边平滑过渡为纯白圣光字形并横向拉丝消融进 63.50s 的纯白爆闪!"""
        u = clamp01((t - self.t_white) / (self.white_end - self.t_white))
        # 前 0.16s 从原深描边字交叉淡入纯白发光字, 随后伴随高斯白芒消融进白幕
        cross = clamp01(u / 0.34)
        fade_white = 1.0 - ease_in_out(clamp01((u - 0.22) / 0.78))

        # 前段仍保留渐隐的原字以防跳变
        if cross < 0.99:
            self.jp.render_to_buffer(canvas, self.t_white - 0.01, 0, 0)
            self.cn.render_to_buffer(canvas, self.t_white - 0.01, 0, 0)

        # 叠加纯白无黑边圣光层 + 横向流光晕染
        bx0 = max(0, self.x0 - 40)
        bx1 = min(canvas.width, self.x1 + 60)
        by0 = 20
        by1 = 205
        bw, bh = bx1 - bx0, by1 - by0
        w_buf = Image.new("RGBA", (bw, bh), (255, 255, 255, 0))

        for line, packs in ((self.jp, self.jp_pure_white), (self.cn, self.cn_pure_white)):
            for p in packs:
                if p is None:
                    continue
                sw, gw, px, py = p
                composite_alpha(w_buf, gw, px - bx0, py - by0, fade_white)
                composite_alpha(w_buf, sw, px - bx0, py - by0, fade_white)

        if u > 0.15:
            blur_r = 6.5 * ((u - 0.15) / 0.85)
            w_buf = w_buf.filter(ImageFilter.GaussianBlur(blur_r))

        composite_alpha(canvas, w_buf, bx0, by0, clamp01(cross * 1.15))

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.white_end:
            return

        if t >= self.t_white:
            self._draw_guitar_string_divider(canvas, t, 1.0 - clamp01((t - self.t_white) / 0.30))
            self._draw_white_overexpose_exit(canvas, t)
            return

        a_in = ease_out(clamp01((t - self.start) / 0.45))
        self._draw_guitar_string_divider(canvas, t, a_in)

        # 叠加景子段翠玉光晕 (56.58s~60.38s) 或舞亚段哥特紫光晕 (60.38s~63.10s), 并重绘清晰字芯!
        w_keiko = 0.0
        w_maia = 0.0
        if self.t_keiko <= t < self.t_maia + 0.45:
            u_in = ease_out(clamp01((t - self.t_keiko) / 0.45))
            u_out = 1.0 - clamp01((t - self.t_maia) / 0.45)
            w_keiko = u_in * u_out * 0.58
        if t >= self.t_maia:
            w_maia = ease_out(clamp01((t - self.t_maia) / 0.45)) * 0.68

        for line, hk_map, hm_map in (
            (self.jp, self.jp_halos_keiko, self.jp_halos_maia),
            (self.cn, self.cn_halos_keiko, self.cn_halos_maia),
        ):
            if w_keiko <= 0.01 and w_maia <= 0.01:
                continue
            for i, (s_core, _, _, px_c, py_c, _, _, is_sp) in enumerate(line.chars):
                if is_sp:
                    continue
                dx, dy, a_ch, _ = line.char_state(i, t)
                if a_ch <= 0.02:
                    continue
                if w_keiko > 0.01 and i in hk_map:
                    hk, hx, hy = hk_map[i]
                    composite_alpha(canvas, hk, hx + dx, hy + dy, a_ch * w_keiko)
                if w_maia > 0.01 and i in hm_map:
                    hm, hx, hy = hm_map[i]
                    composite_alpha(canvas, hm, hx + dx, hy + dy, a_ch * w_maia)
                composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)
