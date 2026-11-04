# -*- coding: utf-8 -*-
"""本体 OP A段 (L00 ~ L03, 27.31s ~ 44.57s) 哥特爱丽丝暗黑童话分镜演出。

包含四组定制图层:
  1. StorybookDreamTruth (L00: 夢かまことか どちらを望む / 是梦境抑或真实 你渴求哪一方)
     - 羊皮纸古书翻页暖金浮尘 + 哥特菱花引线装饰
     - 『夢 / 梦境』迷幻紫粉柔光蝶影 vs 『まこと / 真实』冷澈银青实像高光
  2. EphemeralCrumble    (L01: 手にしたそれは とても儚く / 握于掌心之物 却如此虚幻易碎)
     - 金色棋盘影绘暖光衬底
     - 34.45s 苍白之手抓向红瓣坠入棋盘: 句尾『とても儚く / 虚幻易碎』逐粒剥落化作发光金尘与猩红花瓣!
  3. PhantomTouchCandles (L02: 触れば消える 刹那の光 / 触碰便会消散 那刹那的微光)
     - 前半『触れば消える / 触碰便会消散』音节触碰瞬间泛起泡沫光圈并微颤半透隐去 (“一触即逝”)
     - 后半『刹那の光 / 那刹那的微光』逐帧卡准原片黑暗中依次燃起的四色幽冥烛火 (38.35s青/38.86s品红/39.50s琥珀/39.85s翠光)!
  4. ConvexMirrorEternity(L03: 鏡に写し 永遠に残して / 映入镜中 将它永远留存)
     - 40.62s 凸面黑魔镜球凝聚: 双语正下方浮现带曲面折射与五色微芒的实时水波镜像倒影
     - 44.57s 句尾本体随烟消散后, 『永遠に残して / 将它永远留存』的镜中倒影独自多滞留 0.42s 才随涟漪隐没!
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import config as C
from effects.base import (
    Layer, clamp01, ease_out, ease_in_out,
    composite_alpha, char_sprites, char_halo, apply_water_smoke,
)


# =====================================================================
#  [L00] 绘本暖金浮尘 + 『夢(虚幻紫蝶) vs まこと(冷银实像)』双生对照
# =====================================================================
class StorybookDreamTruth(Layer):
    z = 36

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end

        # 预缓存『夢(0)』&『梦(1)境(2)』迷幻紫粉光晕, 以及『ま(2)こ(3)と(4)』&『真(5)实(6)』冷银青高光
        self.jp_dream_halos = self._prep_halos(jp_line, font_jp, [0], (208, 78, 248), 10.5, 0)
        self.cn_dream_halos = self._prep_halos(cn_line, font_cn, [1, 2], (208, 78, 248), 10.0, C.CN_SYNTH_BOLD)

        self.jp_truth_packs = self._prep_tinted(
            jp_line, font_jp, [2, 3, 4],
            top=(240, 252, 255), bot=(186, 226, 252), glow=(72, 182, 245), sb=0
        )
        self.cn_truth_packs = self._prep_tinted(
            cn_line, font_cn, [5, 6],
            top=(240, 252, 255), bot=(186, 226, 252), glow=(72, 182, 245), sb=C.CN_SYNTH_BOLD
        )

        # 羊皮纸暖金浮尘粒子 (围绕 JP 与 CN 缓慢升腾)
        rng = random.Random(2731)
        self.motes = []
        for line in (jp_line, cn_line):
            x_min = line.bbox_x0 + 20
            x_max = line.bbox_x1 - 20
            y_mid = line.y + line.font.size * 0.5
            for _ in range(11):
                self.motes.append((
                    rng.uniform(x_min, x_max),
                    y_mid + rng.uniform(-14, 22),
                    rng.uniform(0.0, 1.3),         # birth offset
                    rng.uniform(1.6, 2.8),         # life
                    rng.uniform(-16.0, -30.0),     # vy
                    rng.uniform(2.0, 4.6),         # radius
                    rng.uniform(0.0, math.tau),    # phase
                ))

        # 预绘『夢』字左上角微型幻紫发光蝶精灵
        self.mini_bfly = self._make_butterfly_wing()

    @staticmethod
    def _prep_halos(line, font, indices, col, br, sb):
        out = []
        for idx in indices:
            if idx < len(line.chars):
                s, _, _, px, py, cx, cy, _ = line.chars[idx]
                h = char_halo(line.text[idx], font, halo_col=col, blur_r=br, synth_bold=sb)
                out.append((idx, h, cx - h.width * 0.5, cy - h.height * 0.5))
        return out

    @staticmethod
    def _prep_tinted(line, font, indices, top, bot, glow, sb):
        out = []
        for idx in indices:
            if idx < len(line.chars):
                s, g = char_sprites(
                    line.text[idx], font, fill_top=top, fill_bot=bot,
                    glow_col=glow, glow_r=9.0, outline=2.4,
                    outline_col=(16, 24, 38), shadow_col=(6, 10, 18),
                    shadow_alpha=0.65, synth_bold=sb,
                )
                _, _, _, _, _, cx, cy, _ = line.chars[idx]
                out.append((idx, s, g, cx - s.width * 0.5, cy - s.height * 0.5))
        return out

    @staticmethod
    def _make_butterfly_wing():
        SS = 3
        dim = 44
        im = Image.new("RGBA", (dim * SS, dim * SS), (205, 95, 255, 0))
        d = ImageDraw.Draw(im)
        c = dim * 0.5 * SS
        # 上下双翼多边形
        d.polygon([(c, c), (c - 14 * SS, c - 13 * SS), (c - 17 * SS, c - 2 * SS), (c - 5 * SS, c + 2 * SS)],
                  fill=(216, 118, 255, 220))
        d.polygon([(c, c), (c + 13 * SS, c - 14 * SS), (c + 16 * SS, c - 3 * SS), (c + 5 * SS, c + 2 * SS)],
                  fill=(216, 118, 255, 220))
        d.polygon([(c, c), (c - 11 * SS, c + 4 * SS), (c - 8 * SS, c + 13 * SS), (c - 2 * SS, c + 7 * SS)],
                  fill=(162, 86, 255, 195))
        d.polygon([(c, c), (c + 10 * SS, c + 4 * SS), (c + 7 * SS, c + 13 * SS), (c + 2 * SS, c + 7 * SS)],
                  fill=(162, 86, 255, 195))
        im = im.filter(ImageFilter.GaussianBlur(1.1 * SS))
        return im.resize((dim, dim), Image.Resampling.LANCZOS)

    @staticmethod
    def _draw_filigree(canvas, x_edge, y_line, align_left, alpha):
        """绘制精巧西洋绘本暗金菱格引线装饰 (◆────)。"""
        SS = 2
        w, h = 110, 24
        im = Image.new("RGBA", (w * SS, h * SS), (235, 195, 118, 0))
        d = ImageDraw.Draw(im)
        cy = 12 * SS
        gold = (236, 198, 122, int(205 * alpha))
        gold_dim = (212, 168, 92, int(130 * alpha))
        if align_left:
            cx = 10 * SS
            d.polygon([(cx, cy - 5 * SS), (cx + 5 * SS, cy), (cx, cy + 5 * SS), (cx - 5 * SS, cy)], fill=gold)
            d.line([(cx + 8 * SS, cy), (w * SS - 6 * SS, cy)], fill=gold_dim, width=2)
            px = x_edge
        else:
            cx = (w - 10) * SS
            d.polygon([(cx, cy - 5 * SS), (cx + 5 * SS, cy), (cx, cy + 5 * SS), (cx - 5 * SS, cy)], fill=gold)
            d.line([(6 * SS, cy), (cx - 8 * SS, cy)], fill=gold_dim, width=2)
            px = x_edge - w
        im1 = im.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, im1, px, y_line, 1.0)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        u_exit = self.jp.exit_progress(t)
        fo = 1.0 - ease_in_out(u_exit)
        if fo <= 0.01:
            return

        # 1) 西洋绘本菱格暗金引线 (衬在日文下沿与中文上沿)
        a_in = ease_out(clamp01((t - self.start) / 0.55)) * fo
        self._draw_filigree(canvas, self.jp.anchor_x, self.jp.y + self.jp.font.size + 4, True, a_in)
        self._draw_filigree(canvas, self.cn.anchor_x, self.cn.y - 22, False, a_in)

        # 2) 老羊皮纸暖金微尘升腾
        dt0 = t - self.start
        mote_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
        md = ImageDraw.Draw(mote_layer)
        has_mote = False
        for mx, my, b_off, life, vy, rad, ph in self.motes:
            age = dt0 - b_off
            if 0.0 <= age <= life:
                u = age / life
                ma = math.sin(math.pi * u) * 0.78 * fo
                if ma > 0.03:
                    has_mote = True
                    px = mx + math.sin(age * 2.8 + ph) * 8.0
                    py = my + vy * age
                    r = rad * (0.65 + 0.35 * math.sin(math.pi * u))
                    md.ellipse([px - r, py - r, px + r, py + r],
                               fill=(255, 224, 148, int(225 * ma)))
        if has_mote:
            mote_layer = mote_layer.filter(ImageFilter.GaussianBlur(1.2))
            canvas.alpha_composite(mote_layer)

        # 3) 『夢 / 梦境』迷幻紫粉呼吸光晕 + 微型振翅幻蝶 (重绘字芯保证笔画锐利不糊!)
        dream_pulse = (0.62 + 0.38 * math.sin((t - self.start) * 4.2)) * fo
        if u_exit < 0.15:
            for idx, h, hx, hy in self.jp_dream_halos:
                s_core, _, _, px_c, py_c, _, _, _ = self.jp.chars[idx]
                dx, dy, a, _ = self.jp.char_state(idx, t)
                composite_alpha(canvas, h, hx + dx, hy + dy, a * dream_pulse * 0.88)
                composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a)
                # 『夢』左上振翅微蝶
                flap = 0.55 + 0.45 * abs(math.sin((t - self.start) * 7.5))
                bw = max(8, int(round(self.mini_bfly.width * flap)))
                bf = self.mini_bfly.resize((bw, self.mini_bfly.height), Image.Resampling.BILINEAR)
                composite_alpha(
                    canvas, bf,
                    hx - 10 + (self.mini_bfly.width - bw) * 0.5,
                    hy - 12 - 5.0 * math.sin((t - self.start) * 2.4),
                    a * fo * 0.85,
                )
            for idx, h, hx, hy in self.cn_dream_halos:
                s_core, _, _, px_c, py_c, _, _, _ = self.cn.chars[idx]
                dx, dy, a, _ = self.cn.char_state(idx, t)
                composite_alpha(canvas, h, hx + dx, hy + dy, a * dream_pulse * 0.85)
                composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a)

            # 4) 28.50s 唱到『まこと / 真实』时: 冷澈银青实像覆写 (与迷幻紫『夢』形成鲜明冷暖虚实对照!)
            u_truth = ease_out(clamp01((t - 28.46) / 0.28)) * fo
            if u_truth > 0.02:
                for idx, s, g, px, py in self.jp_truth_packs:
                    dx, dy, a, _ = self.jp.char_state(idx, t)
                    composite_alpha(canvas, g, px + dx, py + dy, a * u_truth * 0.90)
                    composite_alpha(canvas, s, px + dx, py + dy, a * u_truth)
                for idx, s, g, px, py in self.cn_truth_packs:
                    dx, dy, a, _ = self.cn.char_state(idx, t)
                    composite_alpha(canvas, g, px + dx, py + dy, a * u_truth * 0.90)
                    composite_alpha(canvas, s, px + dx, py + dy, a * u_truth)


# =====================================================================
#  [L01] 34.45s 苍白之手抓向红瓣坠入棋盘: 句尾『とても儚く / 虚幻易碎』剥落化尘与红瓣!
# =====================================================================
class EphemeralCrumble(Layer):
    z = 38

    def __init__(self, jp_line, cn_line, t_crumble: float = 34.86):
        self.jp = jp_line
        self.cn = cn_line
        self.t_crumble = t_crumble
        self.end = jp_line.end + 0.25

        # 句尾易碎剥落目标字符: JP『とても儚く』(8..12), CN『虚幻易碎』(10..13)
        self.jp_targets = [i for i in range(8, len(jp_line.text)) if not jp_line.chars[i][7]]
        self.cn_targets = [i for i in range(10, len(cn_line.text)) if not cn_line.chars[i][7]]

        # 用 motion_hook 在剥落开始后接管这些句尾字符的本体绘制
        jp_set = set(self.jp_targets)
        cn_set = set(self.cn_targets)

        def _make_hook(t_set, order_list):
            rank = {idx: r for r, idx in enumerate(order_list)}
            def _hook(i, t):
                if i in t_set:
                    t_c = t_crumble + rank[i] * 0.075
                    if t >= t_c:
                        return (0.0, 0.0, 0.0)
                return (0.0, 0.0, 1.0)
            return _hook

        jp_line.motion_hook = _make_hook(jp_set, self.jp_targets)
        cn_line.motion_hook = _make_hook(cn_set, self.cn_targets)

        # 为每个目标字预生成噪声高度场 + 细碎发光沙尘 & 微型红玫瑰瓣粒子!
        rng = random.Random(3448)
        np_rng = np.random.RandomState(3448)
        self.erode_items = []   # (line, idx, t_c, s_np, g_np, noise_map, px, py)
        self.dust = []          # (t_birth, life, x0, y0, vx, vy, rad, is_petal, ang0, vang)

        for line, targets in ((jp_line, self.jp_targets), (cn_line, self.cn_targets)):
            for r, idx in enumerate(targets):
                s, g, _, px, py, cx, cy, _ = line.chars[idx]
                t_c = t_crumble + r * 0.075
                s_np = np.array(s)
                g_np = np.array(g)
                h, w = s_np.shape[:2]
                # 平滑有机风化噪声场 (从右上向左下逐块剥蚀)
                small = np_rng.rand(max(4, h // 5), max(4, w // 5)).astype(np.float32)
                n_im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR)
                n_field = np.array(n_im, dtype=np.float32) / 255.0
                yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
                sweep = 0.55 * (xx / max(1.0, w)) + 0.45 * (1.0 - yy / max(1.0, h))
                erosion_score = 0.62 * sweep + 0.38 * n_field
                self.erode_items.append((line, idx, t_c, s_np, g_np, erosion_score, px, py))

                # 从有效笔画像素采样剥落沙尘与猩红花瓣
                ys_on, xs_on = np.where(s_np[..., 3] > 110)
                if len(xs_on) > 0:
                    for k in range(12):
                        pick = rng.randrange(len(xs_on))
                        lx, ly = float(xs_on[pick]), float(ys_on[pick])
                        sc = float(erosion_score[int(ly), int(lx)])
                        tb = t_c + (1.0 - sc) * 0.52 + rng.uniform(-0.03, 0.05)
                        is_pet = (k % 5 == 0)
                        self.dust.append((
                            tb,
                            rng.uniform(0.65, 1.05),
                            px + lx,
                            py + ly,
                            rng.uniform(14.0, 46.0),
                            rng.uniform(10.0, 38.0) if is_pet else rng.uniform(-12.0, 26.0),
                            rng.uniform(4.2, 6.4) if is_pet else rng.uniform(1.4, 2.8),
                            is_pet,
                            rng.uniform(0.0, math.tau),
                            rng.uniform(-4.5, 4.5),
                        ))

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_crumble or t > self.end:
            return

        # 1) 绘制正在被风化剥蚀的句尾残字 (边缘泛暖金微红碎裂高光)
        for line, idx, t_c, s_np, g_np, score, px, py in self.erode_items:
            if t < t_c:
                continue
            u = clamp01((t - t_c) / 0.72)
            if u >= 0.995:
                continue
            thresh = 1.04 - 1.12 * ease_in_out(u)
            keep = np.clip((thresh - score) / 0.14, 0.0, 1.0)
            rim = np.clip(1.0 - np.abs(score - thresh) / 0.08, 0.0, 1.0) * (s_np[..., 3] > 60)

            cur_g = g_np.copy()
            cur_g[..., 3] = (cur_g[..., 3].astype(np.float32) * keep).astype(np.uint8)
            cur_s = s_np.copy()
            cur_s[..., 3] = (cur_s[..., 3].astype(np.float32) * keep).astype(np.uint8)
            # 碎裂剥落前沿染上一圈暖金绯红微芒
            cur_s[..., 0] = np.clip(cur_s[..., 0].astype(np.float32) + rim * 45.0, 0, 255).astype(np.uint8)
            cur_s[..., 1] = np.clip(cur_s[..., 1].astype(np.float32) - rim * 35.0, 0, 255).astype(np.uint8)
            cur_s[..., 2] = np.clip(cur_s[..., 2].astype(np.float32) - rim * 55.0, 0, 255).astype(np.uint8)

            drift_x = 5.0 * u
            drift_y = 3.5 * u
            composite_alpha(canvas, Image.fromarray(cur_g), px + drift_x, py + drift_y, 1.0)
            composite_alpha(canvas, Image.fromarray(cur_s), px + drift_x, py + drift_y, 1.0)

        # 2) 绘制随风飘散的发光微尘与猩红小玫瑰瓣 (呼应 34.5s~35.6s 满屏红瓣坠入棋盘!)
        p_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
        pd = ImageDraw.Draw(p_layer)
        has_p = False
        for tb, life, x0, y0, vx, vy, rad, is_pet, ang0, vang in self.dust:
            age = t - tb
            if 0.0 <= age <= life:
                u = age / life
                pa = math.sin(math.pi * u) ** 0.72
                if pa <= 0.02:
                    continue
                has_p = True
                x = x0 + vx * age + 6.0 * math.sin(age * 5.0 + ang0)
                y = y0 + vy * age + 18.0 * (age ** 2)
                if is_pet:
                    ang = ang0 + vang * age
                    ca, sa = math.cos(ang), math.sin(ang)
                    rx, ry = rad * 1.35, rad * 0.72
                    pts = [
                        (x + ca * rx, y + sa * rx),
                        (x - sa * ry, y + ca * ry),
                        (x - ca * rx * 0.85, y - sa * rx * 0.85),
                        (x + sa * ry, y - ca * ry),
                    ]
                    pd.polygon(pts, fill=(216, 28, 54, int(230 * pa)))
                else:
                    r = rad * (1.0 - 0.35 * u)
                    pd.ellipse([x - r, y - r, x + r, y + r],
                               fill=(255, 232, 178, int(235 * pa)))
        if has_p:
            canvas.alpha_composite(p_layer)


# =====================================================================
#  [L02] 『触れば消える』触碰半透泡沫 + 『刹那の光』四色幽冥烛火逐帧同步!
# =====================================================================
class PhantomTouchCandles(Layer):
    z = 38

    def __init__(self, jp_line, cn_line, font_jp, font_cn):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.end = jp_line.end

        # 1) 前半句『触れば消える (0..5)』与中文『触碰便会消散 (0..5)』: 音节唱过即泛起幻影涟漪并半透淡隐!
        self.jp_touch_times = {}
        for i in range(min(6, len(jp_line.text))):
            syl = jp_line.char_syl[i]
            if syl is not None:
                self.jp_touch_times[i] = syl.start + 0.14
        # 中文前半句跟随日文前半句时间跨度 (35.84s -> 38.05s) 依次触发触碰淡隐
        self.cn_touch_times = {i: 36.15 + i * 0.31 for i in range(6)}

        def _make_touch_hook(t_map):
            def _hook(i, t):
                if i in t_map and t >= t_map[i]:
                    u = ease_out(clamp01((t - t_map[i]) / 0.42))
                    # 触碰后轻轻上浮并退为 34% 幽灵半透明态 ("触れば消える")!
                    return (0.0, -3.5 * u, 1.0 - 0.66 * u)
                return (0.0, 0.0, 1.0)
            return _hook

        jp_line.motion_hook = _make_touch_hook(self.jp_touch_times)
        cn_line.motion_hook = _make_touch_hook(self.cn_touch_times)

        # 2) 后半句『刹(7)那(8)の(9)光(10)』与中文『刹(8)那(9)的(10)微(11)光(12)』:
        # 严格对齐原片黑暗中依次燃起的四盏幽冥彩烛时刻!
        #   38.35s 青蓝烛 | 38.86s 品红烛 | 39.50s 琥珀金烛 | 39.85s 翠绿星烛
        candle_specs_jp = [
            (7, 38.35, (48, 236, 255)),   # 刹 -> 青蓝幽烛
            (8, 38.86, (255, 58, 182)),   # 那 -> 品红幽烛
            (9, 39.50, (255, 198, 46)),   # の -> 琥珀金烛
            (10, 39.85, (82, 255, 156)),  # 光 -> 翠绿星烛
        ]
        candle_specs_cn = [
            (8, 38.35, (48, 236, 255)),   # 刹
            (9, 38.86, (255, 58, 182)),   # 那
            (11, 39.50, (255, 198, 46)),  # 微
            (12, 39.85, (82, 255, 156)),  # 光
        ]
        self.candles = []
        for idx, t_ign, col in candle_specs_jp:
            if idx < len(jp_line.chars):
                _, _, _, _, _, cx, cy, _ = jp_line.chars[idx]
                h = char_halo(jp_line.text[idx], font_jp, halo_col=col, blur_r=11.0, synth_bold=0)
                self.candles.append((jp_line, idx, t_ign, col, h, cx, cy))
        for idx, t_ign, col in candle_specs_cn:
            if idx < len(cn_line.chars):
                _, _, _, _, _, cx, cy, _ = cn_line.chars[idx]
                h = char_halo(cn_line.text[idx], font_cn, halo_col=col, blur_r=10.5, synth_bold=C.CN_SYNTH_BOLD)
                self.candles.append((cn_line, idx, t_ign, col, h, cx, cy))

    @staticmethod
    def _draw_flame_wisp(canvas: Image.Image, cx: float, top_y: float, col, alpha: float, t: float, seed: float):
        """3x 超采样绘制摇曳幽冥烛火火苗 (外焰彩晕 + 亮白内焰芯)。"""
        SS = 3
        w, h = 44, 62
        im = Image.new("RGBA", (w * SS, h * SS), (*col, 0))
        d = ImageDraw.Draw(im)
        sway = math.sin(t * 9.5 + seed) * 3.8 * SS + math.cos(t * 15.2 + seed * 2.1) * 1.6 * SS
        stretch = 1.0 + 0.12 * math.sin(t * 12.0 + seed * 1.3)

        bx = w * 0.5 * SS
        by = (h - 12) * SS
        tip_x = bx + sway
        tip_y = by - 36.0 * SS * stretch

        # 外焰泪滴多边形
        pts_out = [
            (tip_x, tip_y),
            (bx + 9.5 * SS + sway * 0.35, by - 16 * SS),
            (bx + 7.5 * SS, by - 4 * SS),
            (bx, by + 3 * SS),
            (bx - 7.5 * SS, by - 4 * SS),
            (bx - 9.5 * SS + sway * 0.35, by - 16 * SS),
        ]
        d.polygon(pts_out, fill=(*col, int(195 * alpha)))
        im_blur = im.filter(ImageFilter.GaussianBlur(2.8 * SS))

        # 亮白内焰火芯
        core = Image.new("RGBA", (w * SS, h * SS), (255, 255, 255, 0))
        dc = ImageDraw.Draw(core)
        pts_in = [
            (bx + sway * 0.55, by - 23.0 * SS * stretch),
            (bx + 4.2 * SS + sway * 0.2, by - 11 * SS),
            (bx, by + 1 * SS),
            (bx - 4.2 * SS + sway * 0.2, by - 11 * SS),
        ]
        dc.polygon(pts_in, fill=(255, 252, 245, int(235 * alpha)))
        core = core.filter(ImageFilter.GaussianBlur(1.1 * SS))
        im_blur.alpha_composite(core)

        sp = im_blur.resize((w, h), Image.Resampling.LANCZOS)
        composite_alpha(canvas, sp, cx - w * 0.5, top_y - h + 16, 1.0)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.start or t > self.end:
            return
        u_exit = self.jp.exit_progress(t)
        fo = 1.0 - ease_in_out(u_exit)
        if fo <= 0.01:
            return

        # 1) 『触れば消える / 触碰便会消散』触碰瞬间扩散的纤细幻影泡沫光圈
        for line, t_map in ((self.jp, self.jp_touch_times), (self.cn, self.cn_touch_times)):
            for idx, t0 in t_map.items():
                dt = t - t0
                if 0.0 <= dt <= 0.52:
                    u = dt / 0.52
                    ra = math.sin(math.pi * u) * 0.68 * fo
                    _, _, _, _, _, cx, cy, _ = line.chars[idx]
                    SS = 2
                    dim = 68
                    ring = Image.new("RGBA", (dim * SS, dim * SS), (225, 235, 255, 0))
                    rd = ImageDraw.Draw(ring)
                    c = dim * 0.5 * SS
                    rr = (10.0 + 19.0 * ease_out(u)) * SS
                    rd.ellipse([c - rr, c - rr, c + rr, c + rr],
                               outline=(228, 238, 255, int(195 * ra)), width=2)
                    r1 = ring.resize((dim, dim), Image.Resampling.LANCZOS)
                    composite_alpha(canvas, r1, cx - dim * 0.5, cy - dim * 0.5, 1.0)

        # 2) 『刹那の光 / 那刹那的微光』四色幽冥烛火燃亮!
        for k, (line, idx, t_ign, col, halo, cx, cy) in enumerate(self.candles):
            if t < t_ign:
                continue
            u_ign = ease_out(clamp01((t - t_ign) / 0.26))
            flicker = 0.78 + 0.22 * math.sin(t * 11.0 + k * 1.7)
            a_flame = u_ign * flicker * fo
            dx, dy, a_ch, _ = line.char_state(idx, t)
            s_core, _, _, px_c, py_c, _, _, _ = line.chars[idx]
            # 先垫彩色烛光光晕与字顶摇曳烛苗, 再盖回清晰字芯!
            composite_alpha(canvas, halo, cx - halo.width * 0.5 + dx, cy - halo.height * 0.5 + dy, a_flame * 0.90)
            self._draw_flame_wisp(canvas, cx + dx, line.y + dy, col, a_flame * 0.85, t, seed=k * 2.3)
            if u_exit < 0.08:
                composite_alpha(canvas, s_core, px_c + dx, py_c + dy, a_ch)


# =====================================================================
#  [L03] 40.60s 凸面黑魔镜实时水波倒影 + 句尾『永遠に残して / 将它永远留存』镜中封存留驻!
#    三幕式精准叙事 (40.60s ~ 44.56s, 绝不侵入 44.57s B段!):
#      1) 40.60s ~ 43.80s: 现实正字与魔镜水波倒影完整呼应
#      2) 43.80s ~ 44.15s: 现实正字与前半句『鏡に写し / 映入镜中』化烟散去,
#         镜面水线向内收束并以双菱星锁住后半句『永遠に残して / 将它永远留存』, 泛起银紫镜晶辉光!
#      3) 44.15s ~ 44.56s: 唯有镜中『永遠に残して / 将它永远留存』在暗夜中静谧闪耀一瞬后水波隐没!
# =====================================================================
class ConvexMirrorEternity(Layer):
    z = 26  # 衬在主字幕层 (z=30) 下方; 43.80s 后接管正字提前烟散, 留足镜中独白纯净空间!

    def __init__(self, jp_line, cn_line):
        self.jp = jp_line
        self.cn = cn_line
        self.start = jp_line.start
        self.t_mirror = 40.60
        self.t_seal = 44.02      # 尾音『て』点亮之际: 现实正字开始烟散, 镜中后半句结晶封存!
        self.t_real_end = 44.28  # 现实正字与前半句倒影 100% 散尽时刻
        self.end = 44.64         # 镜中『永遠に残して』水波隐没完毕时刻 (不与 L04 右端字重叠!)

        # 44.02s 起接管默认 LyricLine 退场, 让现实正字提前于 44.28s 散尽, 留出纯净镜中独白!
        jp_line.suppress_spans.append((self.t_seal, jp_line.end + 0.1))
        cn_line.suppress_spans.append((self.t_seal, cn_line.end + 0.1))

    def _draw_early_real_smoke(self, line, canvas: Image.Image, t: float):
        """44.02s ~ 44.28s: 将现实世界的整行正字化作水波青烟提前散去。"""
        u = clamp01((t - self.t_seal) / (self.t_real_end - self.t_seal))
        if u >= 0.995:
            return
        bx0 = max(0, line.bbox_x0 - 20)
        by0 = max(0, line.bbox_y0 - 16)
        bx1 = min(canvas.width, line.bbox_x1 + 20)
        by1 = min(canvas.height, line.bbox_y1 + 16)
        bw, bh = max(8, bx1 - bx0), max(8, by1 - by0)
        strip = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        # 用 44.22s 确保句末『て』也已完整亮起后再整体水波烟散
        line.render_to_buffer(strip, min(line.end - C.FADE_OUT - 0.01, max(t, 44.12)), bx0, by0)
        warped = apply_water_smoke(strip, u, phase_seed=line.start * 3.1)
        smoke_dy = -8.5 * (u ** 1.25)
        composite_alpha(canvas, warped, bx0, by0 + smoke_dy, 1.0)

    def _render_mirror_reflection(self, line, canvas: Image.Image, t: float, keep_from_idx: int, alpha_scale: float):
        """绘制魔镜倒影与自适应收束的菱星镜界水线。"""
        bx0 = max(0, line.bbox_x0 - 16)
        by0 = max(0, line.bbox_y0 - 8)
        bx1 = min(canvas.width, line.bbox_x1 + 16)
        by1 = min(canvas.height, line.bbox_y1 + 8)
        bw, bh = max(8, bx1 - bx0), max(8, by1 - by0)

        # 封存进度 u_seal (0 -> 1: 前半句消散 & 镜线收束 & 后半句银紫结晶提亮)
        u_seal = ease_in_out(clamp01((t - self.t_seal) / (self.t_real_end - self.t_seal)))
        # 最终镜中独白退场进度 u_final (44.44s -> 44.64s 水波涟漪隐入黑场)
        u_final = clamp01((t - 44.44) / (self.end - 44.44))
        fo_final = (1.0 - ease_in_out(u_final)) ** 1.15
        if alpha_scale * fo_final <= 0.006:
            return

        t_src_first = min(t, self.t_seal - 0.01)
        # 封存期确保后半句含尾字『て』100% 满亮定格!
        t_src_keep = min(line.end - C.FADE_OUT - 0.01, max(t, 44.12) if t >= self.t_seal else t)
        buf = Image.new("RGBA", (bw, bh), (195, 205, 255, 0))

        # 记录全行与后半句『永遠に残して / 将它永远留存』的水平区间以驱动镜线精准收束!
        full_x0, full_x1 = None, None
        keep_x0, keep_x1 = None, None

        for i, (s, g, _, px, py, cx, _, is_sp) in enumerate(line.chars):
            if is_sp or s is None:
                continue
            ch_l = cx - line.font.size * 0.48 - bx0
            ch_r = cx + line.font.size * 0.48 - bx0
            full_x0 = ch_l if full_x0 is None else min(full_x0, ch_l)
            full_x1 = ch_r if full_x1 is None else max(full_x1, ch_r)
            if i >= keep_from_idx:
                keep_x0 = ch_l if keep_x0 is None else min(keep_x0, ch_l)
                keep_x1 = ch_r if keep_x1 is None else max(keep_x1, ch_r)

            extra_mul = (1.0 - u_seal) if i < keep_from_idx else 1.0
            if extra_mul <= 0.008:
                continue
            dx, dy, a, _ = line.char_state(i, t_src_keep if i >= keep_from_idx else t_src_first)
            if a * extra_mul <= 0.008:
                continue
            # 封存阶段为留驻镜中的后半句叠加温润辉光
            glow_boost = 0.75 + (0.45 * u_seal if i >= keep_from_idx else 0.0)
            composite_alpha(buf, g, px + dx - bx0, py + dy - by0, clamp01(a * extra_mul * glow_boost))
            composite_alpha(buf, s, px + dx - bx0, py + dy - by0, a * extra_mul)

        # 垂直翻转: 封存后略微舒展纵向比例 (0.74 -> 0.84) 令镜中留字更清透隽永
        flipped = buf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        v_ratio = 0.74 + 0.10 * u_seal
        rh = max(8, int(round(bh * v_ratio)))
        refl = flipped.resize((bw, rh), Image.Resampling.LANCZOS)

        arr = np.array(refl, dtype=np.float32)
        # 冷银紫魔镜玻璃色调 (封存独白期泛起冰晶银紫光泽!)
        bright = 1.0 + 0.22 * u_seal
        arr[..., 0] = np.clip((arr[..., 0] * 0.80 + 36.0) * bright, 0, 255)
        arr[..., 1] = np.clip((arr[..., 1] * 0.84 + 42.0) * bright, 0, 255)
        arr[..., 2] = np.clip((arr[..., 2] * 0.98 + 58.0) * bright, 0, 255)

        # 镜面水波横向微折射: 封存独白期平静清澈, 44.30s~44.56s 终幕泛起水波涟漪散去!
        ys = np.arange(rh, dtype=np.float32)
        xs = np.arange(bw, dtype=np.float32)
        calm = 1.0 - 0.55 * u_seal * (1.0 - u_final)
        amp_main = 2.4 * calm + 10.5 * (u_final ** 1.35)
        amp_sub = 1.1 * calm + 4.5 * (u_final ** 1.55)
        shifts = (
            amp_main * np.sin(ys * 0.34 - t * 5.2 - u_final * 7.0)
            + amp_sub * np.cos(ys * 0.62 + t * 3.7 + u_final * 9.0)
        )
        src_x = xs[None, :] - shifts[:, None]
        valid = (src_x >= 0.0) & (src_x < (bw - 1.0))
        x0 = np.clip(np.floor(src_x).astype(np.int32), 0, bw - 1)
        x1 = np.clip(x0 + 1, 0, bw - 1)
        fx = (src_x - np.floor(src_x))[..., None]
        r_idx = np.arange(rh, dtype=np.int32)[:, None]
        warped = (arr[r_idx, x0] * (1.0 - fx) + arr[r_idx, x1] * fx) * valid[..., None]

        # 封存期提升镜中留字通透度 (0.64 -> 0.88), 使『永遠に残して / 将它永远留存』一目了然!
        v_span = 0.88 + 0.10 * u_seal
        v_fade = np.clip(1.0 - (ys / max(1.0, rh * v_span)), 0.0, 1.0) ** (1.30 - 0.25 * u_seal)
        mirror_op = (0.64 + 0.24 * u_seal) * alpha_scale * fo_final
        warped[..., 3] *= v_fade[:, None] * mirror_op

        out_im = Image.fromarray(np.clip(warped, 0.0, 255.0).astype(np.uint8))
        blur_r = max(0.35, 0.80 - 0.35 * u_seal + 2.4 * u_final)
        out_im = out_im.filter(ImageFilter.GaussianBlur(blur_r))

        dest_y = int(round(line.y + line.font.size + 2))
        composite_alpha(canvas, out_im, bx0, dest_y + 3.5 * u_final, 1.0)

        # ---- 自适应收束的五彩魔镜水线 + 双端银紫菱星锁扣! ----
        # 随前半句消散, 镜线从全句宽度平滑收束至『永遠に残して / 将它永远留存』精确宽度, 绝无左侧悬空残线!
        if full_x0 is not None and keep_x0 is not None:
            lx0 = full_x0 * (1.0 - u_seal) + (keep_x0 - 8.0) * u_seal
            lx1 = full_x1 * (1.0 - u_seal) + (keep_x1 + 8.0) * u_seal
            a_line = int((140 + 75 * u_seal) * alpha_scale * fo_final)
            if a_line > 4 and lx1 - lx0 > 12:
                SS = 2
                lh = 18
                lim = Image.new("RGBA", (bw * SS, lh * SS), (200, 190, 255, 0))
                ld = ImageDraw.Draw(lim)
                cy_l = (lh // 2) * SS
                cols_5 = [(68, 228, 255), (245, 76, 185), (188, 122, 255), (255, 206, 72), (88, 245, 162)]
                seg_w = (lx1 - lx0) / 5.0
                for si, c5 in enumerate(cols_5):
                    sx0 = (lx0 + si * seg_w) * SS
                    sx1 = (lx0 + (si + 1) * seg_w) * SS
                    ld.line([(sx0, cy_l), (sx1, cy_l)], fill=(*c5, a_line), width=2)

                # 封存收束时两端亮起精致银紫四芒菱星锁扣, 宣告此半句被魔镜永恒定格!
                if u_seal > 0.08:
                    a_star = int(235 * u_seal * alpha_scale * fo_final)
                    rr = (2.2 + 1.8 * math.sin(math.pi * clamp01(u_seal))) * SS
                    for ex in (lx0 * SS, lx1 * SS):
                        ld.polygon([(ex, cy_l - rr * 1.4), (ex + rr, cy_l),
                                    (ex, cy_l + rr * 1.4), (ex - rr, cy_l)],
                                   fill=(242, 234, 255, a_star))
                lim_1x = lim.resize((bw, lh), Image.Resampling.LANCZOS)
                composite_alpha(canvas, lim_1x, bx0, dest_y + 3 - lh // 2, 1.0)

    def draw(self, canvas: Image.Image, t: float):
        if t < self.t_mirror or t > self.end:
            return

        # 43.80s ~ 44.15s: 现实正字提前化作水波青烟散尽
        if t >= self.t_seal:
            self._draw_early_real_smoke(self.jp, canvas, t)
            self._draw_early_real_smoke(self.cn, canvas, t)

        u_in = ease_out(clamp01((t - self.t_mirror) / 0.45))
        # 注意: JP『鏡(0)に(1)写(2)し(3) (4)永(5)遠(6)に(7)残(8)し(9)て(10)』与 CN『映(0)入(1)镜(2)中(3) (4)将(5)...』后半句均从 idx=5 起!
        self._render_mirror_reflection(self.jp, canvas, t, keep_from_idx=5, alpha_scale=u_in)
        self._render_mirror_reflection(self.cn, canvas, t, keep_from_idx=5, alpha_scale=u_in)
