# -*- coding: utf-8 -*-
"""特效图层基类与公用工具。

每个特效层只需实现 draw(canvas, t): 往 canvas(RGBA Image) 上按时间 t(秒) 叠加。
主循环按 Layer.z 排序后依次 draw, 新增效果 = 新写一个 Layer 子类并挂进 gen.py。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def ease_out(t: float) -> float:
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def apply_alpha(sprite: Image.Image, a: float) -> Image.Image:
    """整体乘一个 alpha 系数 (0..1), 返回新图。"""
    a = clamp01(a)
    if a >= 0.999:
        return sprite
    arr = np.array(sprite)
    arr[..., 3] = (arr[..., 3].astype(np.float32) * a).astype(np.uint8)
    return Image.fromarray(arr)


def composite_alpha(canvas: Image.Image, sprite: Image.Image, x: float, y: float, a: float = 1.0):
    """带透明度安全裁剪地将 sprite 合成到 canvas (支持坐标落在画布边缘外)。"""
    if a <= 0.004:
        return
    sp = apply_alpha(sprite, a)
    ix, iy = int(round(x)), int(round(y))
    cw, ch = canvas.size
    sw, sh = sp.size
    if ix >= cw or iy >= ch or ix + sw <= 0 or iy + sh <= 0:
        return
    if ix >= 0 and iy >= 0 and ix + sw <= cw and iy + sh <= ch:
        canvas.alpha_composite(sp, (ix, iy))
        return
    cx0, cy0 = max(0, ix), max(0, iy)
    cx1, cy1 = min(cw, ix + sw), min(ch, iy + sh)
    cropped = sp.crop((cx0 - ix, cy0 - iy, cx1 - ix, cy1 - iy))
    canvas.alpha_composite(cropped, (cx0, cy0))


class Layer:
    """特效层基类。z 越小越先画 (越靠底)。"""
    z = 0

    def draw(self, canvas: Image.Image, t: float):
        raise NotImplementedError


# -------- 2x 超采样字形精灵缓存 (抗过曝柔影 + 氛围辉光 + 细腻描边) --------
_sprite_cache = {}
_font_2x_cache = {}


def _get_2x_font(font: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
    key = (getattr(font, "path", None), font.size, getattr(font, "index", 0))
    if key not in _font_2x_cache:
        if key[0]:
            _font_2x_cache[key] = ImageFont.truetype(key[0], font.size * 2, index=key[2])
        else:
            _font_2x_cache[key] = font
    return _font_2x_cache[key]


def char_sprites(ch, font: ImageFont.FreeTypeFont, fill, glow_col,
                 glow_r=10, outline=2.5, outline_col=(34, 16, 24),
                 shadow_col=(14, 6, 12), shadow_alpha=0.58, synth_bold=0):
    """返回 (主字精灵, 阴影+辉光背板精灵)。2x 超采样抗锯齿，同参数只算一次。"""
    key = (ch, getattr(font, "path", id(font)), font.size, fill, glow_col,
           glow_r, outline, outline_col, shadow_col, shadow_alpha, synth_bold)
    if key in _sprite_cache:
        return _sprite_cache[key]

    pad = int(math.ceil(glow_r + outline + 8))
    w = max(4, int(math.ceil(font.getlength(ch))) + pad * 2)
    h = font.size + pad * 2

    SS = 2
    f2 = _get_2x_font(font)
    w2, h2, pad2 = w * SS, h * SS, pad * SS
    out_w2 = max(1, int(round(outline * SS)) + synth_bold)

    # 1) 描边+填充主字 (2x 渲染后 LANCZOS 缩回, 边缘丝滑且可微调字重)
    img2 = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(img2)
    d2.text((pad2, pad2), ch, font=f2, fill=outline_col + (255,),
            stroke_width=out_w2, stroke_fill=outline_col + (255,))
    if synth_bold > 0:
        d2.text((pad2, pad2), ch, font=f2, fill=fill + (255,),
                stroke_width=synth_bold, stroke_fill=fill + (255,))
    else:
        d2.text((pad2, pad2), ch, font=f2, fill=fill + (255,))
    img = img2.resize((w, h), Image.Resampling.LANCZOS)

    # 2) 背板 = 抗高光暗柔影 (偏移 +2,+3) + 彩色氛围外辉光
    back = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow_alpha > 0:
        sh_src = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh_src.paste(img, (2, 3))
        sh_blur = sh_src.filter(ImageFilter.GaussianBlur(5.0))
        sa = np.array(sh_blur)
        stint = np.zeros_like(sa)
        stint[..., 0], stint[..., 1], stint[..., 2] = shadow_col
        stint[..., 3] = np.clip(sa[..., 3].astype(np.float32) * shadow_alpha, 0, 255).astype(np.uint8)
        back.alpha_composite(Image.fromarray(stint))

    if glow_r > 0:
        glow = img.filter(ImageFilter.GaussianBlur(glow_r))
        ga = np.array(glow)
        gtint = np.zeros_like(ga)
        gtint[..., 0], gtint[..., 1], gtint[..., 2] = glow_col
        # 适度提亮辉光 alpha 让暗红/紫炎光晕更有存在感
        gtint[..., 3] = np.clip(ga[..., 3].astype(np.float32) * 1.28, 0, 255).astype(np.uint8)
        back.alpha_composite(Image.fromarray(gtint))

    res = (img, back)
    _sprite_cache[key] = res
    return res


_halo_cache = {}


def char_halo(ch, font: ImageFont.FreeTypeFont, halo_col=(255, 120, 148),
              blur_r=8.5, synth_bold=0) -> Image.Image:
    """在唱音节的柔和发光光晕精灵 (与 char_sprites 同尺寸同中心, 直接同坐标叠加)。"""
    key = (ch, getattr(font, "path", id(font)), font.size, halo_col, blur_r, synth_bold)
    if key in _halo_cache:
        return _halo_cache[key]
    s, _ = char_sprites(ch, font, (255, 255, 255), halo_col, synth_bold=synth_bold)
    blurred = s.filter(ImageFilter.GaussianBlur(blur_r))
    ba = np.array(blurred)
    out = np.zeros_like(ba)
    out[..., 0], out[..., 1], out[..., 2] = halo_col
    out[..., 3] = np.clip(ba[..., 3].astype(np.float32) * 1.35, 0, 255).astype(np.uint8)
    res = Image.fromarray(out)
    _halo_cache[key] = res
    return res
