# -*- coding: utf-8 -*-
"""图层基类 + 2x 超采样昼夜双极字形缓存 + 解析无截断柔光云 + 蔷薇清风波纹退场滤镜。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


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


class _UnderlayAdapter(Layer):
    """将演出层的背景衬底元素置于 z=22 (文字 z=30 正后方)。"""
    z = 22

    def __init__(self, owner):
        self.owner = owner

    def draw(self, canvas: Image.Image, t: float):
        self.owner.draw_under(canvas, t)


def with_underlay(stage_layer):
    return [_UnderlayAdapter(stage_layer), stage_layer]


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


def soft_cloud(w: int, h: int, rgb=(96, 22, 46), alpha: int = 52) -> Image.Image:
    """边界严格归零的超椭圆解析柔光云衬底 (绝无任何白底高斯截断框痕!)。"""
    pad = 44
    W, H = max(16, int(w) + pad * 2), max(16, int(h) + pad * 2)
    yy = np.linspace(-1.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :]
    r2 = (np.abs(xx) ** 2.4) + (np.abs(yy) ** 2.0)
    falloff = np.clip(1.0 - r2, 0.0, 1.0) ** 2.2
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[..., 0] = rgb[0]
    arr[..., 1] = rgb[1]
    arr[..., 2] = rgb[2]
    arr[..., 3] = np.clip(falloff * alpha, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(arr)


_SPRITE_CACHE = {}
_HALO_CACHE = {}


def char_sprites(
    ch: str,
    font,
    fill_top=(255, 253, 252),
    fill_bot=None,
    glow_col=(168, 28, 62),
    glow_r: float = 9.0,
    outline: float = 2.4,
    outline_col=(28, 10, 18),
    shadow_col=(10, 3, 8),
    shadow_alpha: float = 0.70,
    synth_bold: int = 0,
):
    """2x 超采样昼夜双极哥特字形精灵缓存, 返回对齐尺寸的 (glyph_im, glow_im)。"""
    if fill_bot is None:
        fill_bot = fill_top
    key = (font.path, font.size, ch, fill_top, fill_bot, glow_col, glow_r,
           outline, outline_col, shadow_col, shadow_alpha, synth_bold)
    hit = _SPRITE_CACHE.get(key)
    if hit is not None:
        return hit

    SS = 2
    f2 = ImageFont.truetype(font.path, font.size * SS)
    pad = int(math.ceil((glow_r + outline + 8) * SS))
    bbox = f2.getbbox(ch)
    bw = max(4, (bbox[2] - bbox[0]) if bbox else font.size * SS)
    bh = max(4, (bbox[3] - bbox[1]) if bbox else font.size * SS)
    W2, H2 = bw + pad * 2, bh + pad * 2
    ox = pad - (bbox[0] if bbox else 0)
    oy = pad - (bbox[1] if bbox else 0)

    # 1) 外发光 + 柔影层 (以同色透明初始化杜绝非预乘 RGBA 暗边脏染!)
    glow_2x = Image.new("RGBA", (W2, H2), (*glow_col, 0))
    dg = ImageDraw.Draw(glow_2x)
    sw_out = int(round((outline + 1.1) * SS)) + synth_bold
    dg.text((ox, oy), ch, font=f2, fill=(*glow_col, 235),
            stroke_width=sw_out, stroke_fill=(*glow_col, 215))
    glow_2x = glow_2x.filter(ImageFilter.GaussianBlur(glow_r * SS * 0.62))
    g_arr = np.array(glow_2x, dtype=np.float32)
    g_arr[..., 3] = np.clip(g_arr[..., 3] * 1.32, 0.0, 255.0)
    glow_2x = Image.fromarray(g_arr.astype(np.uint8))

    if shadow_alpha > 0.01:
        sh_2x = Image.new("RGBA", (W2, H2), (*shadow_col, 0))
        ds = ImageDraw.Draw(sh_2x)
        ds.text((ox + int(1.6 * SS), oy + int(2.0 * SS)), ch, font=f2,
                fill=(*shadow_col, int(255 * shadow_alpha)),
                stroke_width=sw_out, stroke_fill=(*shadow_col, int(255 * shadow_alpha)))
        sh_2x = sh_2x.filter(ImageFilter.GaussianBlur(2.5 * SS))
        sh_2x.alpha_composite(glow_2x)
        glow_2x = sh_2x

    # 2) 主字形: 描边 + 纵向光泽渐变字芯
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


def char_halo(ch: str, font, halo_col=(255, 112, 148), blur_r: float = 8.5, synth_bold: int = 0):
    key = (font.path, font.size, ch, halo_col, blur_r, synth_bold)
    hit = _HALO_CACHE.get(key)
    if hit is not None:
        return hit

    SS = 2
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
    arr[..., 3] = np.clip(arr[..., 3] * 1.42, 0.0, 255.0)
    im = Image.fromarray(arr.astype(np.uint8)).resize((max(2, W2 // SS), max(2, H2 // SS)), Image.Resampling.LANCZOS)
    _HALO_CACHE[key] = im
    return im


def apply_rose_breeze(strip_im: Image.Image, progress: float, phase_seed: float = 0.0, dir_x: float = 1.0) -> Image.Image:
    """FD 专属『红茶涟漪 + 清风拂散』句尾退场滤镜 (丝滑横向轻涟漪与羽化散逸)。"""
    u = clamp01(progress)
    if u <= 0.005:
        return strip_im

    arr = np.array(strip_im, dtype=np.float32)
    h, w, _ = arr.shape
    amp1 = 7.2 * (u ** 1.35)
    amp2 = 3.0 * (u ** 1.6)
    ys = np.arange(h, dtype=np.float32)
    shifts = (
        dir_x * 9.0 * (u ** 1.5)
        + amp1 * np.sin(ys * 0.19 - u * 6.8 + phase_seed)
        + amp2 * np.cos(ys * 0.41 + u * 9.4 + phase_seed * 1.6)
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

    alpha_mul = (1.0 - ease_in_out(u)) ** 1.15
    warped[..., 3] *= alpha_mul
    out = Image.fromarray(np.clip(warped, 0.0, 255.0).astype(np.uint8))
    if u > 0.16:
        out = out.filter(ImageFilter.GaussianBlur(2.2 * ((u - 0.16) / 0.84)))
    return out
