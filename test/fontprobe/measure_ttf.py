# 私有加载一个 ttf，量它在引擎同一参数下的 GDI 度量
# 用法: python test/fontprobe/measure_ttf.py <ttf路径> <字体名>
import ctypes, sys
from ctypes import wintypes

gdi = ctypes.WinDLL('gdi32', use_last_error=True)
HDC, HANDLE = wintypes.HANDLE, wintypes.HANDLE
LPCSTR = wintypes.LPCSTR

class TEXTMETRICA(ctypes.Structure):
    _fields_ = [('tmHeight', wintypes.LONG), ('tmAscent', wintypes.LONG),
                ('tmDescent', wintypes.LONG), ('tmInternalLeading', wintypes.LONG),
                ('tmExternalLeading', wintypes.LONG), ('tmAveCharWidth', wintypes.LONG),
                ('tmMaxCharWidth', wintypes.LONG), ('tmWeight', wintypes.LONG),
                ('tmOverhang', wintypes.LONG), ('tmDigitizedAspectX', wintypes.LONG),
                ('tmDigitizedAspectY', wintypes.LONG), ('tmFirstChar', wintypes.WCHAR),
                ('tmLastChar', wintypes.WCHAR), ('tmDefaultChar', wintypes.WCHAR),
                ('tmBreakChar', wintypes.WCHAR), ('tmItalic', wintypes.BYTE),
                ('tmUnderlined', wintypes.BYTE), ('tmStruckOut', wintypes.BYTE),
                ('tmPitchAndFamily', wintypes.BYTE), ('tmCharSet', wintypes.BYTE)]

class GLYPHMETRICS(ctypes.Structure):
    _fields_ = [('gmBlackBoxX', wintypes.UINT), ('gmBlackBoxY', wintypes.UINT),
                ('gmptGlyphOriginX', wintypes.LONG), ('gmptGlyphOriginY', wintypes.LONG),
                ('gmCellIncX', ctypes.c_short), ('gmCellIncY', ctypes.c_short)]

class MAT2(ctypes.Structure):      # FIXED(16.16) 每个 4 字节，共 16 字节
    _fields_ = [('eM11', ctypes.c_int32), ('eM12', ctypes.c_int32),
                ('eM21', ctypes.c_int32), ('eM22', ctypes.c_int32)]

gdi.CreateCompatibleDC.argtypes = [HDC]; gdi.CreateCompatibleDC.restype = HDC
gdi.CreateFontA.argtypes = [ctypes.c_int]*5 + [wintypes.DWORD]*8 + [LPCSTR]
gdi.CreateFontA.restype = HANDLE
gdi.SelectObject.argtypes = [HDC, HANDLE]; gdi.SelectObject.restype = HANDLE
gdi.GetTextMetricsA.argtypes = [HDC, ctypes.POINTER(TEXTMETRICA)]
gdi.GetTextMetricsA.restype = wintypes.BOOL
gdi.GetTextFaceA.argtypes = [HDC, ctypes.c_int, ctypes.c_char_p]
gdi.GetTextFaceA.restype = ctypes.c_int
gdi.GetGlyphOutlineA.argtypes = [HDC, wintypes.UINT, wintypes.UINT,
                                 ctypes.POINTER(GLYPHMETRICS), wintypes.DWORD,
                                 wintypes.LPVOID, ctypes.POINTER(MAT2)]
gdi.GetGlyphOutlineA.restype = wintypes.DWORD
gdi.AddFontResourceExW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
gdi.AddFontResourceExW.restype = ctypes.c_int

path, face = sys.argv[1], sys.argv[2]
print('AddFontResourceEx ->', gdi.AddFontResourceExW(path, 0x10, None))  # FR_PRIVATE

hdc = gdi.CreateCompatibleDC(None)
hfont = gdi.CreateFontA(-40, 0, 0, 0, 400, 0, 0, 0, 134, 0, 0, 2, 0x30, face.encode('gbk'))
print('CreateFontA ->', hex(hfont) if hfont else 'NULL')
gdi.SelectObject(hdc, hfont)

tm = TEXTMETRICA()
gdi.GetTextMetricsA(hdc, ctypes.byref(tm))
print(f'tmHeight={tm.tmHeight} ascent={tm.tmAscent} descent={tm.tmDescent} '
      f'ave={tm.tmAveCharWidth} max={tm.tmMaxCharWidth} pitch=0x{tm.tmPitchAndFamily:02X} charset={tm.tmCharSet}')

buf = ctypes.create_string_buffer(64)
gdi.GetTextFaceA(hdc, 64, buf)
print('实际选中:', buf.value.decode('gbk', errors='replace'))

mat = MAT2(0x00010000,0,0,0x00010000)
for label, code in [('全角 那(C4C7)', 0xC4C7), ('半角 A', 0x41), ('音符 (A140)', 0xA140)]:
    gm = GLYPHMETRICS()
    r = gdi.GetGlyphOutlineA(hdc, code, 0, ctypes.byref(gm), 0, None, ctypes.byref(mat))
    ok = 'GDI_ERROR' if r == 0xFFFFFFFF else f'bytes={r}'
    print(f'  {label}: {ok} cellIncX={gm.gmCellIncX} box={gm.gmBlackBoxX}x{gm.gmBlackBoxY}')
