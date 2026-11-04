# -*- coding: utf-8 -*-
"""B 段专属分镜演出图层 (L05 ~ L09, 36.19s ~ 53.19s -> 53.55s 碎裂入副歌)。

全部时间点均与 ../opre.mkv 实测切镜帧和 ../opre.ass 卡拉OK音节严格对齐:
  - ChromaticEntry     : L05/L06/L07 日常 CG 镜头入场时的边缘红青色散收敛 (复刻原片镜头色散)
  - AntiqueBoxFrame    : L05 37.25s 切入古典金画框瞬间, 在『古ぼけた箱…』外围勾勒暗金双线角花画框
  - MemoryAmnesia      : L06 42.55s 画框人物变无脸剪影时,『忘れ』『忘却之物』失焦雾化并化作微尘飘散
  - BrokenKeyFracture  : L07『鍵』『壊』(及中文『损坏』) 沿斜对角裂开错位 + 45.46s『蓋』上方落下暗金盒盖压线
  - RestraintPress     : L08『無理に押さえつけた』重压下沉钩子 + 横贯字面的深绿/暗红荆棘束缚铁丝
  - WarpedStrobeShatter: L09『歪んだままで』扭曲斜切错位排版 + 咬合副歌前 4 次黑白频闪冲击 + 53.19s 玻璃花瓣碎裂炸入副歌
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .base import Layer, clamp01, ease_out, char_sprites, composite_alpha
import config as C


class ChromaticEntry(Layer):
    """L05 ~ L07: 每个字入场前 0.22s 带轻微红/青镜头色散重影并迅速收敛归位, 呼应原片 CG 边缘色散。"""
    z = 48

    def __init__(self, lyric_line, font, max_shift=3.2, dur=0.22, synth_bold=0):
        self.line = lyric_line
        self.max_shift = max_shift
        self.dur = dur
        self.ghosts = []
        for i, (s_orig, _, x, y) in enumerate(lyric_line.chars):
            ch = lyric_line.text[i]
            if ch.isspace():
                continue
            sr, _ = char_sprites(ch, font, (255, 62, 92), (180, 20, 45),
                                 glow_r=3, outline=0, shadow_alpha=0.0, synth_bold=synth_bold)
            sc, _ = char_sprites(ch, font, (72, 232, 255), (30, 150, 210),
                                 glow_r=3, outline=0, shadow_alpha=0.0, synth_bold=synth_bold)
            cx, cy = x + s_orig.width * 0.5, y + s_orig.height * 0.5
            self.ghosts.append((i, sr, sc, cx - sr.width * 0.5, cy - sr.height * 0.5))

    def draw(self, canvas, t):
        if t < self.line.start - 0.05 or t > self.line.end:
            return
        for s0, s1 in self.line.suppress_spans:
            if s0 <= t <= s1:
                return
        for i, sr, sc, rx, ry in self.ghosts:
            dt = t - self.line.t_char[i]
            if dt <= 0.0 or dt >= self.dur:
                continue
            u = dt / self.dur
            decay = (1.0 - ease_out(u))
            shift = self.max_shift * decay
            a_in = ease_out(clamp01(dt / self.line.fade_in))
            dx, dy = 0.0, 0.0
            if self.line.mode in ("karaoke", "chars"):
                dy = -C.RISE * (1.0 - a_in)
            elif self.line.mode == "cn_slide":
                dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - a_in)
            composite_alpha(canvas, sr, rx + dx - shift, ry + dy - 0.6 * decay, 0.58 * decay)
            composite_alpha(canvas, sc, rx + dx + shift, ry + dy + 0.6 * decay, 0.52 * decay)


class AntiqueBoxFrame(Layer):
    """L05 古ぼけた箱の中にある:
    在 37.25s 原片切入红黑古典金画框 (恰逢唱到『箱』37.46s) 时,
    围绕歌词渐显古典暗金双线角花边框与微光浮尘, 将文字装入「陈旧的木盒/画框」之中。
    """
    z = 32

    def __init__(self, lyric_line, t_appear=37.375, pad_x=14, pad_y=6):
        self.line = lyric_line
        self.t0 = t_appear
        self.t_wither = lyric_line.end - C.FADE_OUT
        self.wdur = C.FADE_OUT

        left, right, top, bottom = 1e9, 0.0, 1e9, 0.0
        for s, _, x, y in lyric_line.chars:
            arr = np.array(s)[..., 3]
            ys, xs = np.where(arr > 30)
            if len(xs) == 0:
                continue
            left = min(left, x + xs.min())
            right = max(right, x + xs.max())
            top = min(top, y + ys.min())
            bottom = max(bottom, y + ys.max())

        self.box = (left - pad_x, top - pad_y, right + pad_x, bottom + pad_y)
        rng = random.Random(505)
        self.dust = [
            (t_appear + rng.uniform(0.0, 1.4), rng.uniform(1.1, 1.8),
             rng.uniform(left - 8, right + 8), rng.uniform(top, bottom),
             rng.uniform(-9.0, 9.0), rng.uniform(-14.0, -5.0), rng.uniform(1.8, 3.0))
            for _ in range(8)
        ]

    def draw(self, canvas, t):
        if t < self.t0 or t > self.t_wither + self.wdur:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.t_wither:
            u_out = clamp01((t - self.t_wither) / self.wdur)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        prog = ease_out(clamp01((t - self.t0) / 0.55))
        a = prog * fo
        if a <= 0.005:
            return

        x0, y0, x1, y1 = self.box
        y0 += exit_dy
        y1 += exit_dy
        margin = 18
        rx0, ry0 = max(0, int(x0 - margin)), max(0, int(y0 - margin))
        rx1, ry1 = min(1920, int(x1 + margin)), min(1080, int(y1 + margin))
        rw, rh = rx1 - rx0, ry1 - ry0
        if rw <= 8 or rh <= 8:
            return

        SS = 3
        reg = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(reg)
        bx0, by0 = (x0 - rx0) * SS, (y0 - ry0) * SS
        bx1, by1 = (x1 - rx0) * SS, (y1 - ry0) * SS
        bw, bh = bx1 - bx0, by1 - by0

        # 框内极淡暗金暖底衬, 增强「盒中空间」包裹感
        d.rectangle([bx0, by0, bx1, by1], fill=(32, 16, 12, int(52 * a)))

        gold_main = (216, 168, 84, int(215 * a))
        gold_dim = (148, 104, 46, int(155 * a))
        shadow = (18, 8, 6, int(160 * a))

        # 外框随 prog 从四角向中间合拢
        hx = (bw * 0.5) * prog
        hy = (bh * 0.5) * prog
        for (cx, cy, sx, sy) in (
            (bx0, by0, 1, 1), (bx1, by0, -1, 1),
            (bx0, by1, 1, -1), (bx1, by1, -1, -1),
        ):
            # 阴影
            d.line([cx + 2, cy + 3, cx + sx * hx + 2, cy + 3], fill=shadow, width=3 * SS)
            d.line([cx + 2, cy + 3, cx + 2, cy + sy * hy + 3], fill=shadow, width=3 * SS)
            # 外主金线
            d.line([cx, cy, cx + sx * hx, cy], fill=gold_main, width=max(2, int(1.6 * SS)))
            d.line([cx, cy, cx, cy + sy * hy], fill=gold_main, width=max(2, int(1.6 * SS)))
            # 内层细金线 (偏移 4px, 营造古典双线画框感)
            ins = 4.0 * SS
            ix, iy = cx + sx * ins, cy + sy * ins
            ihx = max(0.0, hx - ins) * 0.88
            ihy = max(0.0, hy - ins) * 0.82
            d.line([ix, iy, ix + sx * ihx, iy], fill=gold_dim, width=max(1, SS))
            d.line([ix, iy, ix, iy + sy * ihy], fill=gold_dim, width=max(1, SS))

            # 四角古典菱形角花装饰
            cr = 3.6 * SS * prog
            d.polygon([(cx, cy - cr), (cx + cr, cy), (cx, cy + cr), (cx - cr, cy)],
                      fill=(245, 208, 130, int(235 * a)))

        out = reg.resize((rw, rh), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, rx0, ry0, 1.0)

        # 古旧金尘微粒
        for st, life, dx0, dy0, vx, vy, rad in self.dust:
            dt = t - st
            if 0.0 < dt < life:
                u = dt / life
                da = math.sin(math.pi * u) * fo * 0.72
                px, py = dx0 + vx * dt, dy0 + vy * dt + exit_dy
                sp = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
                sd = ImageDraw.Draw(sp)
                sd.ellipse([7 - rad, 7 - rad, 7 + rad, 7 + rad], fill=(245, 205, 125, int(210 * da)))
                sp = sp.filter(ImageFilter.GaussianBlur(0.8))
                composite_alpha(canvas, sp, px - 7, py - 7, 1.0)


class MemoryAmnesia(Layer):
    """L06 入れていたことも忘れ / 存放着已经忘却之物:
    42.55s 原片画框里的弥生失去五官变成空白无脸剪影——
    此刻接管日文『忘れ』(idx=8,9) 与中文『忘却』(idx=5,6),
    让字形逐渐失焦雾化为空洞残影, 并向右剥落苍白记忆灰烬微粒消散!
    """
    z = 54

    def __init__(self, jp_line, cn_line, font_jp, font_cn,
                 jp_indices=(8, 9), cn_indices=(5, 6), t_erase=42.50):
        self.jp = jp_line
        self.cn = cn_line
        self.t_erase = t_erase
        self.jp_set = set(jp_indices)
        self.cn_set = set(cn_indices)

        # 预生成多级高斯失焦精灵 (blur 2.5px / 5.5px / 空心残影), 渲染零开销
        self.jp_blur = self._prep_blurs(jp_line, font_jp, self.jp_set, synth_bold=0)
        self.cn_blur = self._prep_blurs(cn_line, font_cn, self.cn_set, synth_bold=C.CN_SYNTH_BOLD)

        # 在 t_erase 后淡去原清晰字形, 交由本层的失焦雾化精灵接管
        def _make_erase_hook(idx_set):
            def _hook(i, t):
                if i in idx_set and t > t_erase:
                    u = clamp01((t - t_erase) / 0.65)
                    return (u * 3.5, -u * 2.0, max(0.0, 1.0 - ease_out(u)))
                return (0.0, 0.0, 1.0)
            return _hook

        jp_line.motion_hook = _make_erase_hook(self.jp_set)
        cn_line.motion_hook = _make_erase_hook(self.cn_set)

        # 剥落飘散的苍白记忆微尘
        rng = random.Random(606)
        self.ash = []
        for line, idx_set in ((jp_line, self.jp_set), (cn_line, self.cn_set)):
            for idx in idx_set:
                if idx >= len(line.chars):
                    continue
                s, _, x, y = line.chars[idx]
                for k in range(7):
                    st = t_erase + 0.08 + k * 0.09 + rng.uniform(0.0, 0.08)
                    life = rng.uniform(0.75, 1.25)
                    ax = x + s.width * 0.5 + rng.uniform(-14.0, 14.0)
                    ay = y + s.height * 0.5 + rng.uniform(-14.0, 14.0)
                    vx = rng.uniform(14.0, 34.0)
                    vy = rng.uniform(-18.0, -4.0)
                    rad = rng.uniform(1.6, 3.1)
                    self.ash.append((st, life, ax, ay, vx, vy, rad))

    @staticmethod
    def _prep_blurs(line, font, idx_set, synth_bold=0):
        packs = []
        for i in sorted(idx_set):
            if i >= len(line.chars):
                continue
            s_orig, g_orig, x, y = line.chars[i]
            b_mid = s_orig.filter(ImageFilter.GaussianBlur(2.6))
            b_far = s_orig.filter(ImageFilter.GaussianBlur(6.2))
            packs.append((i, b_mid, b_far, g_orig, x, y))
        return packs

    def _draw_erasing(self, canvas, line, packs, t, fo, exit_dy):
        u_er = clamp01((t - self.t_erase) / 1.05)
        if u_er <= 0.0:
            return
        for i, b_mid, b_far, g_orig, x, y in packs:
            a_in = ease_out(clamp01((t - line.t_char[i]) / line.fade_in))
            if a_in <= 0.01:
                continue
            drift_x = ease_out(u_er) * 7.5
            drift_y = -ease_out(u_er) * 4.5 + exit_dy
            # 中度失焦过渡到深度雾化残影, 保留约 28% 幽灵般朦胧轮廓直至句尾
            a_mid = math.sin(math.pi * min(1.0, u_er * 1.15)) * 0.78 * fo * a_in
            a_far = ease_out(min(1.0, u_er * 1.3)) * (0.72 - 0.38 * u_er) * fo * a_in
            composite_alpha(canvas, g_orig, x + drift_x, y + drift_y, (1.0 - 0.65 * u_er) * fo * a_in)
            composite_alpha(canvas, b_mid, x + drift_x * 0.6, y + drift_y * 0.6, a_mid)
            composite_alpha(canvas, b_far, x + drift_x, y + drift_y, a_far)

    def draw(self, canvas, t):
        if t < self.t_erase or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)

        self._draw_erasing(canvas, self.jp, self.jp_blur, t, fo, exit_dy)
        self._draw_erasing(canvas, self.cn, self.cn_blur, t, fo, exit_dy)

        for st, life, ax0, ay0, vx, vy, rad in self.ash:
            dt = t - st
            if 0.0 < dt < life:
                u = dt / life
                aa = math.sin(math.pi * u) * fo * 0.80
                px = ax0 + vx * dt
                py = ay0 + vy * dt + math.sin(dt * 6.0 + ax0) * 2.5 + exit_dy
                sp = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
                sd = ImageDraw.Draw(sp)
                sd.ellipse([6 - rad, 6 - rad, 6 + rad, 6 + rad], fill=(245, 232, 240, int(215 * aa)))
                sp = sp.filter(ImageFilter.GaussianBlur(0.9))
                composite_alpha(canvas, sp, px - 6, py - 6, 1.0)


class BrokenKeyFracture(Layer):
    """L07 鍵が壊れてる蓋のままで / 钥匙已经损坏 只能让盒盖:
      1) 44.37s 唱响『壊』瞬间, 日文『鍵(0)』『壊(2)』与中文『损(4)』『坏(5)』沿斜对角线咔嚓断裂错位,
         裂口闪过暗金绯红火花并保持错位断裂姿态直至句尾 (与副歌 L16 修复钥匙形成前后伏笔回收!);
      2) 45.46s 唱响『蓋』瞬间, 在『蓋のままで』正上方压下一道沉重的暗金盒盖横梁, 令字面微沉。
    """
    z = 56

    def __init__(self, jp_line, cn_line, jp_break=(0, 2), cn_break=(4, 5),
                 t_break=44.37, lid_span=(6, 10), t_lid=45.46):
        self.jp = jp_line
        self.cn = cn_line
        self.t_break = t_break
        self.t_lid = t_lid
        self.jp_break = set(jp_break)
        self.cn_break = set(cn_break)
        self.lid_span = lid_span

        # 预切分断裂字的左上/右下两半精灵
        self.jp_halves = self._slice_chars(jp_line, self.jp_break)
        self.cn_halves = self._slice_chars(cn_line, self.cn_break)

        # 断裂发生后隐藏原完整字, 并将『蓋のままで』在盒盖压下时微压 +2.5px
        l0, l1 = lid_span

        def _jp_hook(i, t):
            if i in self.jp_break and t >= t_break:
                return (0.0, 0.0, 0.0)
            if l0 <= i <= l1 and t >= t_lid:
                press = ease_out(clamp01((t - t_lid) / 0.20))
                return (0.0, 2.6 * press, 1.0)
            return (0.0, 0.0, 1.0)

        def _cn_hook(i, t):
            if i in self.cn_break and t >= t_break:
                return (0.0, 0.0, 0.0)
            return (0.0, 0.0, 1.0)

        jp_line.motion_hook = _jp_hook
        cn_line.motion_hook = _cn_hook

        # 计算『蓋のままで』顶部横梁区间
        xs_lid, y_top_lid = [], 1e9
        for idx in range(l0, min(l1 + 1, len(jp_line.chars))):
            s, _, x, y = jp_line.chars[idx]
            arr = np.array(s)[..., 3]
            ys_nz, xs_nz = np.where(arr > 30)
            if len(xs_nz) > 0:
                xs_lid.extend([x + xs_nz.min(), x + xs_nz.max()])
                y_top_lid = min(y_top_lid, y + ys_nz.min())
        self.lid_box = (min(xs_lid) - 6, max(xs_lid) + 6, y_top_lid - 6) if xs_lid else None

    @staticmethod
    def _slice_chars(line, idx_set):
        out = []
        for i in sorted(idx_set):
            if i >= len(line.chars):
                continue
            s, g, x, y = line.chars[i]
            h, w = s.height, s.width
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            # 斜约 -58 度裂纹线 (带锯齿折痕)
            diag = (xx - w * 0.5) * 0.84 + (yy - h * 0.5) * 0.54
            jag = 1.6 * np.sin(yy * 0.45 + i)
            mask_a = (diag + jag <= 0).astype(np.float32)
            mask_b = 1.0 - mask_a

            sa, sb = np.array(s), np.array(s)
            ga, gb = np.array(g), np.array(g)
            sa[..., 3] = (sa[..., 3] * mask_a).astype(np.uint8)
            sb[..., 3] = (sb[..., 3] * mask_b).astype(np.uint8)
            ga[..., 3] = (ga[..., 3] * mask_a).astype(np.uint8)
            gb[..., 3] = (gb[..., 3] * mask_b).astype(np.uint8)
            out.append((i, Image.fromarray(sa), Image.fromarray(sb),
                        Image.fromarray(ga), Image.fromarray(gb), x, y, w, h))
        return out

    def _draw_broken_group(self, canvas, line, halves, t, fo, exit_dy):
        dt = t - self.t_break
        if dt < 0.0:
            return
        # 咔嚓错位弹开并定格在 ±2.5px 错位裂痕姿态
        snap = ease_out(clamp01(dt / 0.14))
        jolt = math.sin(dt * 75.0) * 1.4 * max(0.0, 1.0 - dt / 0.22)
        off = 2.4 * snap + jolt

        for i, sa, sb, ga, gb, x, y, w, h in halves:
            a_in = ease_out(clamp01((t - line.t_char[i]) / line.fade_in))
            if a_in <= 0.01:
                continue
            a = a_in * fo
            base_dy = -C.RISE * (1.0 - a_in) if line.mode in ("karaoke", "chars") else 0.0
            base_dx = -(C.CN_SLIDE_X + i * 1.4) * (1.0 - a_in) if line.mode == "cn_slide" else 0.0
            px, py = x + base_dx, y + base_dy + exit_dy

            # 左上半向左上错移, 右下半向右下下坠微倾
            composite_alpha(canvas, ga, px - off * 0.9, py - off * 0.7, a)
            composite_alpha(canvas, gb, px + off * 1.0, py + off * 1.1, a)
            composite_alpha(canvas, sa, px - off * 0.9, py - off * 0.7, a)
            composite_alpha(canvas, sb, px + off * 1.0, py + off * 1.1, a)

            # 断裂瞬间的暗金+绯红裂纹闪光 (0.32s 内消退)
            if dt < 0.34:
                fa = (1.0 - dt / 0.34) ** 1.6 * a
                SS = 2
                sp = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
                d = ImageDraw.Draw(sp)
                cx, cy = w * 0.5 * SS, h * 0.5 * SS
                dx_l, dy_l = -14 * SS, 22 * SS
                d.line([cx - dx_l, cy - dy_l, cx + dx_l, cy + dy_l],
                       fill=(255, 195, 110, int(230 * fa)), width=2 * SS)
                sp = sp.resize((w, h), Image.Resampling.LANCZOS)
                composite_alpha(canvas, sp, px, py, 1.0)

    def draw(self, canvas, t):
        if t < self.t_break or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)

        self._draw_broken_group(canvas, self.jp, self.jp_halves, t, fo, exit_dy)
        self._draw_broken_group(canvas, self.cn, self.cn_halves, t, fo, exit_dy)

        # 『蓋のままで』上方压下的暗金盒盖压条
        if self.lid_box and t >= self.t_lid:
            u_lid = ease_out(clamp01((t - self.t_lid) / 0.22))
            la = u_lid * fo
            lx0, lx1, ly = self.lid_box
            drop_y = ly - 7.0 * (1.0 - u_lid) + 2.2 * u_lid + exit_dy
            pw = int(lx1 - lx0 + 24)
            ph = 24
            SS = 3
            bar = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(bar)
            x_a, x_b = 12 * SS, (pw - 12) * SS
            ym = 12 * SS
            d.line([x_a, ym + 2 * SS, x_b, ym + 2 * SS], fill=(16, 8, 10, int(170 * la)), width=4 * SS)
            d.line([x_a, ym, x_b, ym], fill=(208, 158, 82, int(225 * la)), width=max(2, int(2.2 * SS)))
            # 两端向下扣合的盒盖折角
            d.line([x_a, ym, x_a, ym + 6 * SS], fill=(208, 158, 82, int(225 * la)), width=2 * SS)
            d.line([x_b, ym, x_b, ym + 6 * SS], fill=(208, 158, 82, int(225 * la)), width=2 * SS)
            bar_1x = bar.resize((pw, ph), Image.Resampling.LANCZOS)
            composite_alpha(canvas, bar_1x, lx0 - 12, drop_y - 12, 1.0)


class RestraintPress(Layer):
    """L08 無理に押さえつけた / 强行保持 (47.85s ~ 51.23s):
    呼应原片密布镜头的墨绿带刺荆棘铁丝与紧闭木门——
    唱到『押さえつけた』(49.09s) 时字面被强行向下重压并带紧绷微颤,
    两道紧绷的暗绿/绯红带刺束缚藤丝横贯日/中字幕将其死死勒住。
    """
    z = 58

    def __init__(self, jp_line, cn_line, t_press=49.05):
        self.jp = jp_line
        self.cn = cn_line
        self.t_press = t_press

        def _press_hook(i, t):
            if t < t_press:
                return (0.0, 0.0, 1.0)
            dt = t - t_press
            p = ease_out(clamp01(dt / 0.26))
            strain = math.sin(dt * 52.0 + i) * 0.9 * max(0.0, 1.0 - dt / 0.9)
            return (strain, 4.8 * p, 1.0)

        jp_line.motion_hook = _press_hook
        cn_line.motion_hook = _press_hook

        self.jp_bounds = self._bounds(jp_line)
        self.cn_bounds = self._bounds(cn_line)

    @staticmethod
    def _bounds(line):
        left, right, top, bottom = 1e9, 0.0, 1e9, 0.0
        for s, _, x, y in line.chars:
            arr = np.array(s)[..., 3]
            ys, xs = np.where(arr > 30)
            if len(xs) == 0:
                continue
            left = min(left, x + xs.min())
            right = max(right, x + xs.max())
            top = min(top, y + ys.min())
            bottom = max(bottom, y + ys.max())
        return (left, right, top, bottom)

    def _draw_wires(self, canvas, bounds, t, fo, exit_dy):
        left, right, top, bottom = bounds
        u = ease_out(clamp01((t - (self.t_press - 0.15)) / 0.32))
        if u <= 0.01:
            return
        a = u * fo
        rx0 = max(0, int(left - 34))
        rx1 = min(1920, int(right + 34))
        ry0 = max(0, int(top - 14 + exit_dy))
        ry1 = min(1080, int(bottom + 22 + exit_dy))
        rw, rh = rx1 - rx0, ry1 - ry0
        if rw <= 8 or rh <= 8:
            return

        SS = 3
        reg = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(reg)
        w_full = (rx1 - rx0 - 12) * SS
        x_start = 6 * SS
        x_end = x_start + w_full * u

        # 上下两根带弧度的荆棘藤丝从文字上下肩部向内勒紧(两端交叉锁死, 不横穿字心遮挡笔画!)
        h_box = max(12.0, bottom - top)
        N_seg = 64
        x_span = w_full * u

        for idx_w, (is_top, col_main, col_hi) in enumerate([
            (True,  (42, 92, 56), (126, 195, 122)),
            (False, (138, 26, 48), (228, 78, 98)),
        ]):
            pts = []
            for k in range(N_seg + 1):
                ku = k / N_seg
                px = x_start + x_span * ku
                # 中段紧贴文字上下沿向内微弓压迫, 两端交叉收束成荆棘死结
                arch = math.sin(ku * math.pi)
                if is_top:
                    base_y = top + exit_dy + 4.5 * u + (5.5 * (1.0 - arch) - 2.0 * arch)
                else:
                    base_y = bottom + exit_dy + 4.5 * u - (6.5 * (1.0 - arch) - 2.5 * arch)
                wob = math.sin(ku * math.pi * 3.0 + idx_w * 2.1) * 1.4
                pts.append((px, (base_y + wob - ry0) * SS))

            for k in range(len(pts) - 1):
                x1, y1 = pts[k]
                x2, y2 = pts[k + 1]
                d.line([x1, y1 + 2 * SS, x2, y2 + 2 * SS],
                       fill=(10, 6, 8, int(170 * a)), width=3 * SS)
                d.line([x1, y1, x2, y2],
                       fill=col_main + (int(225 * a),), width=max(2, int(1.8 * SS)))
                d.line([x1, y1 - 1, x2, y2 - 1],
                       fill=col_hi + (int(135 * a),), width=max(1, SS // 2))

            for k in range(5, len(pts) - 4, 8):
                tx, ty = pts[k]
                # 尖刺朝向字内侧刺入, 强化「押さえつけた」压迫感
                side = 1 if is_top else -1
                d.polygon([(tx - 2.0 * SS, ty), (tx + 2.0 * SS, ty),
                           (tx + 1.2 * SS, ty + side * 5.6 * SS)],
                          fill=col_hi + (int(215 * a),))

        out = reg.resize((rw, rh), Image.Resampling.LANCZOS)
        composite_alpha(canvas, out, rx0, ry0, 1.0)

    def draw(self, canvas, t):
        if t < self.t_press - 0.15 or t > self.jp.end + C.FADE_OUT:
            return
        fo = 1.0
        exit_dy = 0.0
        if t > self.jp.end - C.FADE_OUT:
            u_out = clamp01((t - (self.jp.end - C.FADE_OUT)) / C.FADE_OUT)
            fo = 1.0 - ease_out(u_out)
            exit_dy = -4.5 * (u_out ** 1.6)
        self._draw_wires(canvas, self.jp_bounds, t, fo, exit_dy)
        self._draw_wires(canvas, self.cn_bounds, t, fo, exit_dy)


class WarpedStrobeShatter(Layer):
    """L09 歪んだままで / 异常闭合的模样 (51.23s ~ 53.19s -> 53.62s 碎裂炸入副歌!):
      - 完全接管 L09 的日/中双语绘制 (屏蔽常规静态行), 移至更有张力的内收电影感对角构图,
        同时严密避开 51.42s 中央木门与 52.83s 中央黑白手绘有栖脸部;
      - 每个字带不规则歪斜旋转 (±5°~8°) + 错位高低基线 + 扫描线横向撕裂错移 (呼应『歪んだ』);
      - 精准咬合原片 51.58s / 52.00s / 52.45s / 52.83s 四次鼓点黑白频闪切镜, 迸发红青涂鸦色散震动
        (直接呼应 51.65s 原片画面上的红青油彩大字 YMA!), 黑场间隙则在纯黑中泛出暗红幽光;
      - 53.19s~53.62s 副歌红玫瑰炸裂第一拍: 整句文字瞬间崩裂成数十枚锋利碎片与绯红花瓣向四周炸散!
    """
    z = 64

    # 实测原片 4 次鼓点频闪切入时刻
    STROBE_HITS = (51.708, 52.125, 52.583, 52.958)

    def __init__(self, line_obj, jp_line, cn_line, font_jp_path, font_cn_path):
        self.L = line_obj
        self.t0 = line_obj.start
        self.t_shatter = line_obj.end - 0.11   # 53.08s 提前半拍引爆碎裂, 让开 53.19s L10 新词入场区!
        self.t_end = self.t_shatter + 0.36     # 碎片向画面内侧高速飞散至 53.44s 汇入副歌红玫瑰风暴

        # 彻底接管 L09 原图层
        jp_line.suppress_spans.append((0.0, 999.0))
        cn_line.suppress_spans.append((0.0, 999.0))

        f_jp = ImageFont_load(font_jp_path, 52)
        f_cn = ImageFont_load(font_cn_path, 48)

        # 内收对角张力构图 (避开中央 x=660..1260 的木门与手绘有栖面容)
        self.jp_units = self._build_warped_units(
            line_obj.jp, f_jp, align="right", x_edge=1812, y_base=92,
            t_chars=jp_line.t_char, fade_in=jp_line.fade_in, synth_bold=1, seed=901
        )
        cn_t_chars = [self.t0 + i * 0.026 for i in range(len(line_obj.cn))]
        self.cn_units = self._build_warped_units(
            line_obj.cn, f_cn, align="left", x_edge=118, y_base=862,
            t_chars=cn_t_chars, fade_in=0.26, synth_bold=C.CN_SYNTH_BOLD + 1, seed=902
        )

        # 预切分每个字的玻璃裂片: 右上日文向左下内侧爆射, 左下中文向右上内侧爆射, 绝不糊住 L10 新句!
        self.shards = []
        rng = random.Random(909)
        for is_jp, group in ((True, self.jp_units), (False, self.cn_units)):
            group_cx = sum(u["x"] + u["w"] * 0.5 for u in group) / max(1, len(group))
            group_cy = sum(u["y"] + u["h"] * 0.5 for u in group) / max(1, len(group))
            for u in group:
                self._make_shards_for_unit(u, group_cx, group_cy, is_jp, rng)

    @staticmethod
    def _build_warped_units(text, font, align, x_edge, y_base, t_chars, fade_in, synth_bold, seed):
        rng = random.Random(seed)
        spacing = 5
        widths = [font.getlength(c) for c in text]
        total = sum(widths) + spacing * max(0, len(text) - 1)
        x0 = (x_edge - total) if align == "right" else x_edge

        # 预定的歪斜角度与错位基线, 让整句呈现「强行闭合却扭曲错位」的不安定感
        tilts = [-6.5, 5.2, -4.0, 7.2, -5.5, 4.8, -6.0, 5.5]
        y_jitters = [-4.0, 5.5, -3.5, 6.0, -5.0, 3.5, -4.5, 5.0]

        units = []
        for i, ch in enumerate(text):
            if ch.isspace():
                continue
            s, g = char_sprites(
                ch, font, fill=(255, 249, 251), glow_col=(196, 24, 54),
                glow_r=12, outline=2.2, outline_col=(28, 10, 18),
                shadow_alpha=0.72, synth_bold=synth_bold
            )
            sr, _ = char_sprites(
                ch, font, fill=(242, 26, 62), glow_col=(220, 20, 50),
                glow_r=4, outline=0, shadow_alpha=0.0, synth_bold=synth_bold
            )
            sc, _ = char_sprites(
                ch, font, fill=(24, 228, 245), glow_col=(20, 185, 215),
                glow_r=4, outline=0, shadow_alpha=0.0, synth_bold=synth_bold
            )

            # 对主字做一道细微横向错位切片 (歪曲感)
            s_warp = _slice_glitch(s, shift_px=3 if i % 2 == 0 else -3, band_ratio=0.46 + 0.08 * (i % 3))
            ang = tilts[i % len(tilts)]
            s_rot = s_warp.rotate(ang, resample=Image.Resampling.BICUBIC, expand=False)
            g_rot = g.rotate(ang, resample=Image.Resampling.BICUBIC, expand=False)
            sr_rot = sr.rotate(ang, resample=Image.Resampling.BICUBIC, expand=False)
            sc_rot = sc.rotate(ang, resample=Image.Resampling.BICUBIC, expand=False)

            cx = x0 + sum(widths[:i]) + spacing * i + widths[i] * 0.5
            px = cx - s_rot.width * 0.5
            py = y_base + y_jitters[i % len(y_jitters)]
            units.append({
                "i": i, "s": s_rot, "g": g_rot, "sr": sr_rot, "sc": sc_rot,
                "x": px, "y": py, "w": s_rot.width, "h": s_rot.height,
                "t_in": t_chars[min(i, len(t_chars) - 1)], "fade_in": fade_in,
                "phase": rng.uniform(0, math.pi * 2),
            })
        return units

    def _make_shards_for_unit(self, u, gcx, gcy, is_jp, rng):
        s_arr = np.array(u["s"])
        h, w = s_arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w * 0.5 + rng.uniform(-4, 4), h * 0.5 + rng.uniform(-4, 4)
        ang_map = np.arctan2(yy - cy, xx - cx)
        cuts = [-math.pi, -math.pi * 0.45, 0.12, math.pi * 0.58, math.pi + 0.01]
        for k in range(4):
            m = ((ang_map >= cuts[k]) & (ang_map < cuts[k + 1])).astype(np.uint8)
            part = s_arr.copy()
            part[..., 3] = part[..., 3] * m
            if part[..., 3].max() < 25:
                continue
            sp = Image.fromarray(part)
            # 径向扩散 + 强力向画面中心花瓣风暴牵引, 迅速腾空角落给 L10 新词!
            ux = (u["x"] + w * 0.5) - gcx + (k - 1.5) * 22.0
            uy = (u["y"] + h * 0.5) - gcy + ((k % 2) * 2 - 1) * 18.0
            norm = max(12.0, math.hypot(ux, uy))
            speed = rng.uniform(180.0, 320.0)
            inward_vx = rng.uniform(-220.0, -90.0) if is_jp else rng.uniform(90.0, 220.0)
            inward_vy = rng.uniform(110.0, 240.0) if is_jp else rng.uniform(-240.0, -95.0)
            vx = (ux / norm) * speed * 0.55 + inward_vx
            vy = (uy / norm) * speed * 0.45 + inward_vy
            rot_v = rng.uniform(-340.0, 340.0)
            is_red = rng.random() < 0.45
            if is_red:
                # 部分裂片在炸开时染成深红玫瑰瓣色, 无缝汇入 53.33s 副歌漫天红瓣!
                pa = np.array(sp)
                bright = pa[..., 3] > 80
                pa[..., 0] = np.where(bright, 235, pa[..., 0])
                pa[..., 1] = np.where(bright, 42, pa[..., 1])
                pa[..., 2] = np.where(bright, 68, pa[..., 2])
                sp = Image.fromarray(pa)
            self.shards.append((sp, u["x"], u["y"], vx, vy, rot_v))

    def draw(self, canvas, t):
        if t < self.t0 - 0.05 or t > self.t_end:
            return

        # 阶段 B: 53.19s ~ 53.65s 碎裂飞散入副歌!
        if t >= self.t_shatter:
            dt = t - self.t_shatter
            u = clamp01(dt / (self.t_end - self.t_shatter))
            fade = (1.0 - u) ** 1.45

            # 碎裂第一帧闪过一道柔和绯白冲击光晕
            if dt < 0.14:
                fa = (1.0 - dt / 0.14) ** 2 * 0.55
                for grp in (self.jp_units, self.cn_units):
                    for unit in grp:
                        composite_alpha(canvas, unit["g"], unit["x"], unit["y"], fa)

            for sp, x0, y0, vx, vy, rot_v in self.shards:
                # 初速极快爆开, 随后受空气阻力减速飘散
                decel = dt * (1.0 - 0.38 * u)
                px = x0 + vx * decel
                py = y0 + vy * decel + 42.0 * (dt ** 2)
                ang = rot_v * dt
                s_rot = sp.rotate(ang, resample=Image.Resampling.BILINEAR, expand=False)
                composite_alpha(canvas, s_rot, px, py, fade)
            return

        # 阶段 A: 51.23s ~ 53.19s 鼓点频闪蓄力 + 扭曲红青色散
        strobe_pulse = 0.0
        for th in self.STROBE_HITS:
            d_st = t - th
            if 0.0 <= d_st <= 0.18:
                strobe_pulse = max(strobe_pulse, (1.0 - d_st / 0.18) ** 1.6)

        for grp in (self.jp_units, self.cn_units):
            for u in grp:
                a_in = clamp01((t - u["t_in"]) / u["fade_in"])
                if a_in <= 0.0:
                    continue
                e_in = ease_out(a_in)

                # 越临近 53.19s 副歌引爆点, 内部紧绷微颤越明显
                tension = clamp01((t - (self.t_shatter - 0.9)) / 0.9)
                trem_x = math.sin(t * 68.0 + u["phase"]) * (0.6 + 2.0 * strobe_pulse + 1.5 * tension)
                trem_y = math.cos(t * 57.0 - u["phase"]) * (0.5 + 1.4 * strobe_pulse + 1.1 * tension)
                scale_in = -8.0 * (1.0 - e_in)

                px = u["x"] + trem_x
                py = u["y"] + scale_in + trem_y

                # 红青油彩色散错位 (频闪切镜瞬间猛烈撕开 ±6px, 平时保持 ±1.8px 诡谲微偏)
                split = (1.6 + 5.2 * strobe_pulse + 2.0 * tension) * e_in
                composite_alpha(canvas, u["g"], px, py, e_in * (0.92 + 0.08 * strobe_pulse))
                composite_alpha(canvas, u["sr"], px - split, py - 0.8, e_in * (0.45 + 0.42 * strobe_pulse))
                composite_alpha(canvas, u["sc"], px + split, py + 0.8, e_in * (0.42 + 0.42 * strobe_pulse))
                composite_alpha(canvas, u["s"], px, py, e_in)


def ImageFont_load(path, size):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _slice_glitch(img: Image.Image, shift_px: int = 3, band_ratio: float = 0.5) -> Image.Image:
    """将字形中间一道水平窄带微移 shift_px 像素, 制造克制而锐利的『歪曲/错位』质感。"""
    arr = np.array(img)
    h = arr.shape[0]
    y0 = int(h * band_ratio)
    y1 = min(h, y0 + max(4, int(h * 0.14)))
    out = arr.copy()
    out[y0:y1] = np.roll(arr[y0:y1], shift_px, axis=1)
    return Image.fromarray(out)
