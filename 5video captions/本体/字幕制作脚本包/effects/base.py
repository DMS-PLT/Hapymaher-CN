# -*- coding: utf-8 -*-
"""图层基类 + 2x 超采样哥特珠光渐变字形缓存 + 原片水波烟散滤镜。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def ease_out(u: float) -> float:
    u = clamp01(u)
    return 1.0 - (1.0 - u) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return 3 * u * u - 2 * u * u * u


class Layer:
    z = 0
    def draw(self, canvas: Image.Image, t: float):
        pass


def composite_alpha(dst: Image.Image, src: Image.Image, x: float, y: float, alpha: float = 1.0):
    if alpha <= 0.003:
        return
    ix, iy = int(round(x)), int(round(y))
    if ix >= dst.width or iy >= dst.height or ix + src.width <= 0 or iy + src.height <= 0:
        return
    if alpha < 0.996:
        arr = np.array(src, copy=True)
        arr[..., 3] = (arr[..., 3].astype(np.float32) * alpha).astype(np.uint8)
        src = Image.fromarray(arr)
    dst.alpha_composite(src, dest=(ix, iy))


_SPRITE_CACHE = {}
_HALO_CACHE = {}


def char_sprites(
    ch: str,
    font,
    fill_top=(255, 253, 252),
    fill_bot=None,
    glow_col=(158, 30, 64),
    glow_r: float = 9.0,
    outline: float = 2.4,
    outline_col=(28, 12, 20),
    shadow_col=(10, 4, 10),
    shadow_alpha: float = 0.68,
    synth_bold: int = 0,
):
    """2x 超采样抗过曝字形精灵 (带本体 OP 名牌同款珍珠白->淡蔷薇纵向光泽渐变):
    返回 (glyph_im, glow_im), 二者同尺寸对齐。
    """
    if fill_bot is None:
        fill_bot = fill_top
    key = (font.path, font.size, ch, fill_top, fill_bot, glow_col, glow_r,
           outline, outline_col, shadow_col, shadow_alpha, synth_bold)
    hit = _SPRITE_CACHE.get(key)
    if hit is not None:
        return hit

    SS = 2
    from PIL import ImageFont
    f2 = ImageFont.truetype(font.path, font.size * SS)
    pad = int(math.ceil((glow_r + outline + 8) * SS))
    bbox = f2.getbbox(ch)
    bw = max(4, (bbox[2] - bbox[0]) if bbox else font.size * SS)
    bh = max(4, (bbox[3] - bbox[1]) if bbox else font.size * SS)
    W2 = bw + pad * 2
    H2 = bh + pad * 2
    ox = pad - (bbox[0] if bbox else 0)
    oy = pad - (bbox[1] if bbox else 0)

    # 1) 外发光 + 抗亮底柔影层
    glow_2x = Image.new("RGBA", (W2, H2), (*glow_col, 0))
    dg = ImageDraw.Draw(glow_2x)
    sw_out = int(round((outline + 1.2) * SS)) + synth_bold
    dg.text((ox, oy), ch, font=f2, fill=(*glow_col, 240),
            stroke_width=sw_out, stroke_fill=(*glow_col, 220))
    glow_2x = glow_2x.filter(ImageFilter.GaussianBlur(glow_r * SS * 0.62))
    # 增强辉光浓郁度
    g_arr = np.array(glow_2x, dtype=np.float32)
    g_arr[..., 3] = np.clip(g_arr[..., 3] * 1.38, 0.0, 255.0)
    glow_2x = Image.fromarray(g_arr.astype(np.uint8))

    if shadow_alpha > 0.01:
        sh_2x = Image.new("RGBA", (W2, H2), (*shadow_col, 0))
        ds = ImageDraw.Draw(sh_2x)
        ds.text((ox + int(1.8 * SS), oy + int(2.2 * SS)), ch, font=f2,
                fill=(*shadow_col, int(255 * shadow_alpha)),
                stroke_width=sw_out, stroke_fill=(*shadow_col, int(255 * shadow_alpha)))
        sh_2x = sh_2x.filter(ImageFilter.GaussianBlur(2.6 * SS))
        sh_2x.alpha_composite(glow_2x)
        glow_2x = sh_2x

    # 2) 主字形: 描边底层 + 纵向珠光渐变字芯
    stroke_2x = Image.new("RGBA", (W2, H2), (*outline_col, 0))
    d_st = ImageDraw.Draw(stroke_2x)
    sw_main = int(round(outline * SS)) + synth_bold
    d_st.text((ox, oy), ch, font=f2, fill=(*outline_col, 255),
              stroke_width=sw_main, stroke_fill=(*outline_col, 255))

    mask_2x = Image.new("L", (W2, H2), 0)
    d_mk = ImageDraw.Draw(mask_2x)
    d_mk.text((ox, oy), ch, font=f2, fill=255,
              stroke_width=synth_bold, stroke_fill=255)

    mk_np = np.array(mask_2x, dtype=np.float32) / 255.0
    yy = np.linspace(0.0, 1.0, H2, dtype=np.float32)[:, None]
    # 仅在字形实际高度区间内做细腻纵向过渡
    y_min = max(0, pad)
    y_max = min(H2 - 1, pad + bh)
    t_grad = np.clip((np.arange(H2, dtype=np.float32)[:, None] - y_min) / max(1.0, y_max - y_min), 0.0, 1.0)
    c_top = np.array(fill_top, dtype=np.float32)[None, None, :]
    c_bot = np.array(fill_bot, dtype=np.float32)[None, None, :]
    rgb_grad = c_top * (1.0 - t_grad[..., None]) + c_bot * t_grad[..., None]

    core_np = np.zeros((H2, W2, 4), dtype=np.uint8)
    core_np[..., :3] = np.clip(rgb_grad, 0.0, 255.0).astype(np.uint8)
    core_np[..., 3] = np.clip(mk_np * 255.0, 0.0, 255.0).astype(np.uint8)
    stroke_2x.alpha_composite(Image.fromarray(core_np))

    W1, H1 = max(2, W2 // SS), max(2, H2 // SS)
    glyph_1x = stroke_2x.resize((W1, H1), Image.Resampling.LANCZOS)
    glow_1x = glow_2x.resize((W1, H1), Image.Resampling.LANCZOS)
    res = (glyph_1x, glow_1x)
    _SPRITE_CACHE[key] = res
    return res


def char_halo(ch: str, font, halo_col=(255, 118, 152), blur_r: float = 8.5, synth_bold: int = 0):
    """卡拉OK在唱呼吸光晕缓存。"""
    key = (font.path, font.size, ch, halo_col, blur_r, synth_bold)
    hit = _HALO_CACHE.get(key)
    if hit is not None:
        return hit

    SS = 2
    from PIL import ImageFont
    f2 = ImageFont.truetype(font.path, font.size * SS)
    pad = int(math.ceil((blur_r + 11.4) * SS))
    bbox = f2.getbbox(ch)
    bw = max(4, (bbox[2] - bbox[0]) if bbox else font.size * SS)
    bh = max(4, (bbox[3] - bbox[1]) if bbox else font.size * SS)
    W2, H2 = bw + pad * 2, bh + pad * 2
    ox = pad - (bbox[0] if bbox else 0)
    oy = pad - (bbox[1] if bbox else 0)

    im = Image.new("RGBA", (W2, H2), (*halo_col, 0))
    d = ImageDraw.Draw(im)
    d.text((ox, oy), ch, font=f2, fill=(*halo_col, 255),
           stroke_width=int(2.2 * SS) + synth_bold, stroke_fill=(*halo_col, 235))
    im = im.filter(ImageFilter.GaussianBlur(blur_r * SS * 0.65))
    arr = np.array(im, dtype=np.float32)
    arr[..., 3] = np.clip(arr[..., 3] * 1.45, 0.0, 255.0)
    im = Image.fromarray(arr.astype(np.uint8)).resize((max(2, W2 // SS), max(2, H2 // SS)), Image.Resampling.LANCZOS)
    _HALO_CACHE[key] = im
    return im


def apply_water_smoke(strip_im: Image.Image, progress: float, phase_seed: float = 0.0) -> Image.Image:
    """复刻本体 OP 原生字幕标志性的『横向正弦水波纹扭曲 + 青烟蒸发』退场滤镜!
    progress: 0.0 (刚开始退场) -> 1.0 (完全消散)
    仅对整句紧凑包围盒做向量化行偏移与柔化, 单次耗时 < 0.5ms。
    """
    u = clamp01(progress)
    if u <= 0.005:
        return strip_im

    arr = np.array(strip_im, dtype=np.float32)
    h, w, _ = arr.shape
    # 双频正弦水波横向剪切偏移 (振幅随 u 平滑放大至 ~11px)
    amp1 = 8.5 * (u ** 1.35)
    amp2 = 3.6 * (u ** 1.6)
    ys = np.arange(h, dtype=np.float32)
    shifts = (
        amp1 * np.sin(ys * 0.21 - u * 7.5 + phase_seed)
        + amp2 * np.cos(ys * 0.43 + u * 10.5 + phase_seed * 1.7)
    )

    xs = np.arange(w, dtype=np.float32)[None, :]
    src_x = xs - shifts[:, None]
    x0 = np.floor(src_x).astype(np.int32)
    fx = (src_x - x0)[..., None]

    valid0 = (x0 >= 0) & (x0 < w)
    valid1 = ((x0 + 1) >= 0) & ((x0 + 1) < w)
    x0_c = np.clip(x0, 0, w - 1)
    x1_c = np.clip(x0 + 1, 0, w - 1)

    row_idx = np.arange(h, dtype=np.int32)[:, None]
    p0 = arr[row_idx, x0_c] * valid0[..., None]
    p1 = arr[row_idx, x1_c] * valid1[..., None]
    warped = p0 * (1.0 - fx) + p1 * fx

    # 尾段叠一缕轻烟柔化与透明度衰减
    alpha_mul = (1.0 - ease_in_out(u)) ** 1.15
    warped[..., 3] *= alpha_mul
    out = Image.fromarray(np.clip(warped, 0.0, 255.0).astype(np.uint8))
    if u > 0.18:
        out = out.filter(ImageFilter.GaussianBlur(2.4 * ((u - 0.18) / 0.82)))
    return out
