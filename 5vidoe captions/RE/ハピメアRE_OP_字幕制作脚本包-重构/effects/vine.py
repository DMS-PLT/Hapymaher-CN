# -*- coding: utf-8 -*-
"""荆棘藤蔓效果层 (3x 超采样抗锯齿升级版)。

VineUnder  - 文字下方横向贝塞尔生长蔷薇荆棘藤 (带弧形玫瑰刺、卷须与立体明暗脊线)
VineChars  - 逐字缠绕螺旋藤 (已修复底层 want_front=False 前后穿插遮挡)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .base import Layer, clamp01, ease_out, composite_alpha


class VineUnder(Layer):
    z = 18

    def __init__(self, lyric_line, color, t0, t_wither, wdur, grow=None,
                 thorn_hi=None, align_dir="right_to_left"):
        self.col = color
        self.hi = thorn_hi or tuple(min(255, int(c * 1.45 + 28)) for c in color)
        self.dark = tuple(max(0, int(c * 0.32)) for c in color)
        self.t0 = t0
        self.grow = grow if grow is not None else max(0.8, (t_wither - t0) * 0.72)
        self.t_wither, self.wdur = t_wither, wdur
        self.align_dir = align_dir

        left, right, bottom = 1e9, 0.0, 0.0
        for s, g, x, y in lyric_line.chars:
            arr = np.array(s)[..., 3]
            ys, xs = np.where(arr > 25)
            if len(xs) == 0:
                continue
            left = min(left, x + xs.min())
            right = max(right, x + xs.max())
            bottom = max(bottom, y + ys.max())
        self.left, self.right, self.bottom = float(left), float(right), float(bottom)
        self.rx0 = max(0, int(left - 44))
        self.ry0 = max(0, int(bottom - 26))
        self.rx1 = min(1920, int(right + 44))
        self.ry1 = min(1080, int(bottom + 46))

    def _alpha(self, t):
        if t < self.t0 or t > self.t_wither + self.wdur:
            return 0.0
        if t > self.t_wither:
            return 1.0 - ease_out((t - self.t_wither) / self.wdur)
        return min(1.0, (t - self.t0) / 0.22)

    @staticmethod
    def _bez(t, p0, p1, p2, p3):
        mt = 1.0 - t
        return (
            mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
            mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1],
        )

    def draw(self, canvas, t):
        a = self._alpha(t)
        if a <= 0.005:
            return

        SS = 3  # 3x 超采样彻底消除折线与尖刺锯齿
        rw, rh = self.rx1 - self.rx0, self.ry1 - self.ry0
        if rw <= 4 or rh <= 4:
            return
        reg2 = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(reg2)

        xa = (self.left - 18 - self.rx0) * SS
        xb = (self.right + 18 - self.rx0) * SS
        yb = (self.bottom + 9 - self.ry0) * SS
        span = xb - xa

        P0 = (xa, yb + 3 * SS)
        P1 = (xa + span * 0.33, yb - 10 * SS)
        P2 = (xa + span * 0.67, yb + 11 * SS)
        P3 = (xb, yb - 2 * SS)

        raw_p = clamp01((t - self.t0) / self.grow)
        prog = 0.55 * raw_p + 0.45 * ease_out(raw_p)
        if prog <= 0.01:
            return

        N = 120
        n_draw = max(2, int(N * prog))
        pts = []
        for i in range(n_draw + 1):
            u = i / N
            bx, by = self._bez(u, P0, P1, P2, P3)
            # 轻微有机藤蔓起伏 (比旧版高频锯齿柔和得多)
            by += math.sin(u * math.pi * 3.5) * 1.6 * SS
            pts.append((bx, by, u))

        # 1) 抗亮底柔暗底影 (让藤蔓在 21.6s 白理石桌面上也清晰立体)
        for i in range(len(pts) - 1):
            x1, y1, u1 = pts[i]
            x2, y2, _ = pts[i + 1]
            tip_taper = clamp01((prog - u1) / 0.14)
            w = max(2, int(round((3.4 * (1.0 - 0.42 * u1) * tip_taper + 1.2) * SS)))
            d.line([x1 + 1.5 * SS, y1 + 2.2 * SS, x2 + 1.5 * SS, y2 + 2.2 * SS],
                   fill=(14, 6, 10, int(135 * a)), width=w)

        # 2) 主茎干
        for i in range(len(pts) - 1):
            x1, y1, u1 = pts[i]
            x2, y2, _ = pts[i + 1]
            tip_taper = clamp01((prog - u1) / 0.14)
            w = max(1, int(round(3.1 * (1.0 - 0.45 * u1) * tip_taper * SS)))
            d.line([x1, y1, x2, y2], fill=self.col + (int(235 * a),), width=w)
            if w >= 4:
                d.line([x1, y1 - 0.8 * SS, x2, y2 - 0.8 * SS],
                       fill=self.hi + (int(120 * a),), width=max(1, SS // 2))

        # 3) 弧形蔷薇弯刺 (沿切线法向斜掠, 带尖锋而非生硬等腰三角)
        for idx, ti in enumerate(range(10, N - 6, 11)):
            u = ti / N
            if u > prog - 0.03 or ti >= len(pts) - 1:
                break
            grow_s = ease_out(clamp01((prog - u) / 0.12))
            x, y, _ = pts[ti]
            nx_pt, ny_pt, _ = pts[min(len(pts) - 1, ti + 1)]
            tx, ty = nx_pt - x, ny_pt - y
            tlen = max(1e-4, math.hypot(tx, ty))
            tx, ty = tx / tlen, ty / tlen
            side = -1.0 if idx % 2 == 0 else 1.0
            nx, ny = -ty * side, tx * side

            thorn_len = (7.2 * (1.0 - 0.30 * u) * grow_s) * SS
            base_half = 2.1 * SS * grow_s
            # 刺尖略向生长前方弯钩, 像真正的蔷薇刺
            tip = (x + nx * thorn_len + tx * thorn_len * 0.42,
                   y + ny * thorn_len + ty * thorn_len * 0.42)
            b1 = (x - tx * base_half, y - ty * base_half)
            b2 = (x + tx * base_half * 0.85, y + ty * base_half * 0.85)
            d.polygon([b1, b2, tip], fill=self.dark + (int(190 * a),))
            d.polygon([b1, (x + tx * base_half * 0.4, y + ty * base_half * 0.4), tip],
                      fill=self.hi + (int(215 * a),))

        # 4) 两处纤细卷须 (增强哥特藤蔓精致感)
        for u_curl, side in ((0.22, 1.0), (0.64, -1.0)):
            if prog < u_curl + 0.08:
                continue
            c_prog = ease_out(clamp01((prog - u_curl) / 0.24))
            ci = min(len(pts) - 1, int(u_curl * N))
            cx0, cy0, _ = pts[ci]
            c_pts = []
            steps = int(26 * c_prog)
            for k in range(steps + 1):
                ku = k / 26.0
                ang = ku * math.pi * 2.1 * side - math.pi * 0.3 * side
                rad = (9.5 * (1.0 - 0.72 * ku)) * SS
                px = cx0 + ku * 14 * SS + math.cos(ang) * rad * 0.65 - (rad * 0.4)
                py = cy0 + side * (ku * 8 * SS + abs(math.sin(ang * 0.5)) * rad * 0.75)
                c_pts.append((px, py))
            for k in range(len(c_pts) - 1):
                d.line([c_pts[k], c_pts[k + 1]],
                       fill=self.col + (int(185 * a * (1.0 - 0.4 * k / 26.0)),),
                       width=max(1, int(round(1.5 * SS * (1.0 - 0.55 * k / 26.0)))))

        region = reg2.resize((rw, rh), Image.Resampling.LANCZOS)
        composite_alpha(canvas, region, self.rx0, self.ry0, 1.0)


class VineChars(Layer):
    z = 20   # 字背后的藤 (z=20), 字在 z=50, 字前面的藤单独一层 z=60

    def __init__(self, lyric_line, color, hi, t0, grow, t_wither, wdur,
                 base_w=4.0, loops=1.25):
        self.col, self.hi = color, hi
        self.t0, self.grow = t0, grow
        self.t_wither, self.wdur = t_wither, wdur
        self.base_w, self.loops = base_w, loops
        P = []
        prev_end = None
        for s, g, x, y in lyric_line.chars:
            arr = np.array(s)[..., 3]
            ys, xs = np.where(arr > 25)
            if len(xs) == 0:
                continue
            cx = x + (xs.min() + xs.max()) / 2
            cy = y + (ys.min() + ys.max()) / 2
            iw, ih = xs.max() - xs.min(), ys.max() - ys.min()
            rx = iw / 2 + 7
            y_from = cy + ih * 0.42
            y_to = cy - ih * 0.50
            n = max(44, int(iw * 1.05))
            start_pt = (cx - rx * 0.92, y_from)
            if prev_end is not None:
                mx = (prev_end[0] + start_pt[0]) / 2
                my = (prev_end[1] + start_pt[1]) / 2 + 7
                for k in range(1, 9):
                    tt = k / 9
                    qx = (1 - tt)**2 * prev_end[0] + 2 * (1 - tt) * tt * mx + tt**2 * start_pt[0]
                    qy = (1 - tt)**2 * prev_end[1] + 2 * (1 - tt) * tt * my + tt**2 * start_pt[1]
                    P.append((qx, qy, True))
            for k in range(n + 1):
                u = k / n
                psi = math.pi / 2 + 2 * math.pi * self.loops * u
                px = cx + rx * 0.92 * math.sin(psi)
                py = y_from + (y_to - y_from) * u + math.sin(psi) * ih * 0.08
                P.append((px, py, math.cos(psi) > 0.03))
            prev_end = P[-1][:2]
        self.P = P
        self.thorns = [i for i in range(24, len(P) - 4, 22) if P[i][2]]

    def _alpha(self, t):
        if t < self.t0 or t > self.t_wither + self.wdur:
            return 0.0
        if t > self.t_wither:
            return 1.0 - (t - self.t_wither) / self.wdur
        return 1.0

    def draw(self, canvas, t, want_front=False):
        a = self._alpha(t)
        if a <= 0:
            return
        prog = ease_out(clamp01((t - self.t0) / self.grow))
        head = min(len(self.P) - 1, int(len(self.P) * prog))
        if head < 4:
            return
        col = self.col if want_front else tuple(int(c * 0.60) for c in self.col)
        runs, cur = [], []
        for i in range(head + 1):
            if self.P[i][2] == want_front:
                cur.append(i)
            else:
                if len(cur) > 1:
                    runs.append(cur)
                cur = []
        if len(cur) > 1:
            runs.append(cur)
        d = ImageDraw.Draw(canvas)
        for run in runs:
            for j in range(len(run) - 1):
                i = run[j]
                x1, y1, _ = self.P[i]
                x2, y2, _ = self.P[i + 1]
                tap = 0.6 + 0.4 * math.sin(math.pi * min(1.0, i / head))**0.5
                w = max(1, int(self.base_w * tap * 1.6))
                d.line([x1, y1, x2, y2],
                       fill=col + (int((215 if want_front else 175) * a),), width=w)
            if want_front and len(run) > 10:
                d.line([(self.P[i][0], self.P[i][1] - 1.6) for i in run],
                       fill=self.hi + (int(85 * a),), width=1)
        for i in self.thorns:
            if not want_front or i > head:
                break
            x, y, _ = self.P[i]
            s = 10.5 * (1 - 0.3 * i / len(self.P))
            d.polygon([(x - 2.7, y), (x + 2.7, y), (x + 1.2, y + s)],
                      fill=col + (int(230 * a),))


class VineCharsFront(Layer):
    """VineChars 的字前层包装 (z > LyricLine.z 50)。"""
    z = 60

    def __init__(self, vine: VineChars):
        self._v = vine

    def draw(self, canvas, t):
        self._v.draw(canvas, t, want_front=True)
