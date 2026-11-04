# -*- coding: utf-8 -*-
"""单条字幕行 —— 2x 超采样楷书字形 + 柔和暗衬底, 整行淡入淡出 (不含 op 那套特技)。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config as C

_CACHE = {}


def _clamp01(x):
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def _ease_out(u):
    u = _clamp01(u)
    return 1.0 - (1.0 - u) ** 3


def composite_alpha(dst, src, x, y, alpha=1.0):
    if alpha <= 0.004:
        return
    ix, iy = int(round(x)), int(round(y))
    if ix >= dst.width or iy >= dst.height or ix + src.width <= 0 or iy + src.height <= 0:
        return
    if alpha < 0.996:
        arr = np.array(src, copy=True)
        arr[..., 3] = (arr[..., 3].astype(np.float32) * alpha).astype(np.uint8)
        src = Image.fromarray(arr)
    dst.alpha_composite(src, dest=(ix, iy))


def _fit_size(text, size, max_w, spacing, floor=34):
    """超出版面时逐级缩字, 保证永不越界。"""
    while size > floor:
        f = ImageFont.truetype(C.FONT_PATH, size)
        w = sum(f.getlength(ch) for ch in text) + spacing * max(0, len(text) - 1)
        if w <= max_w:
            return size
        size -= 1
    return size


def build_sprite(text, size, spacing, fill_top, fill_bot):
    """返回 (sprite, text_dx, text_dy, text_w): sprite 内文字左上角偏移与文字宽度。"""
    key = (text, size, spacing, fill_top, fill_bot)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    SS = 2
    f2 = ImageFont.truetype(C.FONT_PATH, size * SS)
    ascent, descent = f2.getmetrics()
    advs = [f2.getlength(ch) for ch in text]
    total2 = sum(advs) + spacing * SS * max(0, len(text) - 1)

    pad2 = 40
    Wm2 = int(math.ceil(total2)) + pad2 * 2
    Hm2 = ascent + descent + pad2 * 2
    base2 = pad2 + ascent

    def _text(layer, dx=0, dy=0, fill=None, stroke_w=0, stroke_fill=None):
        d = ImageDraw.Draw(layer)
        x = pad2 + dx
        for i, ch in enumerate(text):
            d.text((x, base2 + dy), ch, font=f2, anchor="ls",
                   fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)
            x += advs[i] + spacing * SS

    # 1) 亮底上的暗色柔光 (白云/白花镜头下保住白字轮廓)
    halo = Image.new("RGBA", (Wm2, Hm2), (*C.OUTLINE_COL, 0))
    _text(halo, fill=(*C.OUTLINE_COL, 255),
          stroke_w=int(round((C.OUTLINE_W + 5.0) * SS)), stroke_fill=(*C.OUTLINE_COL, 255))
    halo = halo.filter(ImageFilter.GaussianBlur(9 * SS))
    ha = np.array(halo, dtype=np.float32)
    ha[..., 3] = np.clip(ha[..., 3] * C.HALO_ALPHA, 0, 255)
    halo = Image.fromarray(ha.astype(np.uint8))

    # 2) 投影
    shadow = Image.new("RGBA", (Wm2, Hm2), (*C.OUTLINE_COL, 0))
    _text(shadow, dx=2 * SS, dy=3 * SS, fill=(*C.OUTLINE_COL, int(255 * C.SHADOW_ALPHA)),
          stroke_w=int(round(C.OUTLINE_W * SS)), stroke_fill=(*C.OUTLINE_COL, int(255 * C.SHADOW_ALPHA)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3 * SS))

    # 3) 描边底 + 珠光白字芯 (纵向微渐变)
    outline = Image.new("RGBA", (Wm2, Hm2), (*C.OUTLINE_COL, 0))
    _text(outline, fill=(*C.OUTLINE_COL, 255),
          stroke_w=int(round(C.OUTLINE_W * SS)), stroke_fill=(*C.OUTLINE_COL, 255))

    mask = Image.new("L", (Wm2, Hm2), 0)
    _text(mask, fill=255)
    mk = np.array(mask, dtype=np.float32) / 255.0
    y0, y1 = pad2, pad2 + ascent + descent
    tt = np.clip((np.arange(Hm2, dtype=np.float32) - y0) / max(1.0, (y1 - y0)), 0.0, 1.0)[:, None]
    grad = (np.array(fill_top, dtype=np.float32) * (1 - tt[..., None])
            + np.array(fill_bot, dtype=np.float32) * tt[..., None])
    core = np.zeros((Hm2, Wm2, 4), dtype=np.uint8)
    core[..., :3] = np.clip(grad, 0, 255).astype(np.uint8)
    core[..., 3] = (mk * 255.0).astype(np.uint8)
    outline.alpha_composite(Image.fromarray(core))

    stack = Image.new("RGBA", (Wm2, Hm2), (0, 0, 0, 0))
    stack.alpha_composite(halo)
    stack.alpha_composite(shadow)
    stack.alpha_composite(outline)

    W1, H1 = max(2, Wm2 // SS), max(2, Hm2 // SS)
    glyph = stack.resize((W1, H1), Image.Resampling.LANCZOS)

    # 4) 暗红柔光衬底: 只贴身裹住文字本体 (扣掉字形精灵自带的留白), 不做大黑块
    pad1 = pad2 // SS
    B = C.PLATE_BLUR
    M = max(C.PLATE_PAD_X, C.PLATE_PAD_Y) + B
    sprite = Image.new("RGBA", (W1 + M * 2, H1 + M * 2), (0, 0, 0, 0))
    plate = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        [M + pad1 - C.PLATE_PAD_X, M + pad1 - C.PLATE_PAD_Y,
         M + W1 - pad1 + C.PLATE_PAD_X, M + H1 - pad1 + C.PLATE_PAD_Y],
        radius=C.PLATE_RADIUS, fill=(*C.PLATE_COL, C.PLATE_ALPHA),
    )
    plate = plate.filter(ImageFilter.GaussianBlur(B))
    sprite.alpha_composite(plate)
    sprite.alpha_composite(glyph, dest=(M, M))

    res = (sprite, M + pad2 // SS, M + pad2 // SS, total2 / SS)
    _CACHE[key] = res
    return res


class SubLine:
    """一条双语字幕中的单语行。"""

    def __init__(self, text, size, spacing, anchor_x, y_top, align, start, end,
                 fill_top, fill_bot, max_w):
        self.start = start
        self.end = end
        if not text:
            self.active = False
            return
        self.active = True
        size = _fit_size(text, size, max_w, spacing)
        sprite, dx, dy, tw = build_sprite(text, size, spacing, fill_top, fill_bot)
        self.sprite = sprite
        if align == "left":
            self.x = anchor_x - dx
        else:
            self.x = anchor_x - tw - dx
        self.y = y_top - dy

    def draw(self, canvas, t):
        if not self.active or t < self.start or t > self.end:
            return
        u_in = _ease_out(_clamp01((t - self.start) / C.FADE_IN))
        u_out = _clamp01((t - (self.end - C.FADE_OUT)) / C.FADE_OUT)
        a = u_in * (1.0 - u_out)
        if a <= 0.004:
            return
        dy = C.RISE * (1.0 - u_in) - 3.0 * u_out
        composite_alpha(canvas, self.sprite, self.x, self.y + dy, a)


def build_layers(lines):
    """按 config 版式把每句歌词排成「日文右上 + 中文左下」两个图层。"""
    layers = []
    jp_max = C.W - C.JP_RIGHT - 90
    cn_max = C.W - C.CN_LEFT - 120
    for L in lines:
        layers.append(SubLine(
            L.jp, _fit_size(L.jp, C.FONT_SIZE_JP, C.JP_SPACING, jp_max), C.JP_SPACING,
            anchor_x=C.W - C.JP_RIGHT, y_top=C.JP_TOP, align="right",
            start=L.start, end=L.end,
            fill_top=C.JP_FILL_TOP, fill_bot=C.JP_FILL_BOT, max_w=jp_max,
        ))
        if L.cn:
            cn_size = _fit_size(L.cn, C.FONT_SIZE_CN, C.CN_SPACING, cn_max)
            layers.append(SubLine(
                L.cn, cn_size, C.CN_SPACING,
                anchor_x=C.CN_LEFT, y_top=C.H - C.CN_BOTTOM - cn_size, align="left",
                start=L.start, end=L.end,
                fill_top=C.CN_FILL_TOP, fill_bot=C.CN_FILL_BOT, max_w=cn_max,
            ))
    return layers
