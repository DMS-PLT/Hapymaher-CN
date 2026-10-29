// fontmetrics.exe —— 量各字体在同一字号下的 GDI 度量
//
// 引擎只用 GetTextMetricsA 决定排版（exe 没导入任何 TextOut/DrawText），
// 所以换字体后折行对不对，完全看这里的数字对不对。
// 目标是把 SimHei / SimSun / 雅黑 的度量和引擎原本的 ＭＳ ゴシック 摆在一起比。
//
// 全局变量 40 是引擎实际用的字号（lfHeight = -40，从探头日志得到）。

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

#pragma comment(lib, "gdi32.lib")

// 引擎请求的字体名原始字节（Shift-JIS「ＭＳ ゴシック」），从 cnpatch.log 抠出来的
static const char kEngineFace[] = "\x82\x6C\x82\x72\x20\x83\x53\x83\x56\x83\x62\x83\x4E";

static const int kHeight = -40;

struct Sample {
    const char* label;
    const char* face;
    int         charset;
};

static const Sample kSamples[] = {
    { "引擎原样 ＭＳゴシック charset=128(SJIS)", kEngineFace, 128 },
    { "引擎字体     ＭＳゴシック charset=134(GB2312)", kEngineFace, 134 },
    { "SimHei   黑体            charset=134", "SimHei", 134 },
    { "SimSun   宋体            charset=134", "SimSun", 134 },
    { "NSimSun 新宋体           charset=134", "NSimSun", 134 },
    { "FangSong 仿宋            charset=134", "FangSong", 134 },
    { "KaiTi    楷体            charset=134", "KaiTi", 134 },
    { "YouYuan  幼圆            charset=134", "YouYuan", 134 },
    { "LiSu     隶书            charset=134", "LiSu", 134 },
    { "STKaiti  华文楷体        charset=134", "STKaiti", 134 },
    { "STSong   华文宋体        charset=134", "STSong", 134 },
    { "STHeiti  华文黑体        charset=134", "STHeiti", 134 },
    { "微软雅黑 Microsoft YaHei  charset=134", "Microsoft YaHei", 134 },
    { "等线     DengXian         charset=134", "DengXian", 134 },
};

// 取一个字形，返回它的水平步进（gmCellIncX）。全角汉字「那」的 GBK 码是 0xC4C7。
static int glyph_advance(HDC dc, UINT ch)
{
    MAT2 mat = { {0,1},{0,0},{0,0},{0,1} };
    GLYPHMETRICS gm;
    ZeroMemory(&gm, sizeof(gm));
    DWORD n = GetGlyphOutlineA(dc, ch, GGO_METRICS, &gm, 0, NULL, &mat);
    if (n == GDI_ERROR) return -1;
    return (int)gm.gmCellIncX;
}

static void measure(const Sample& s, int height)
{
    // 参数必须和引擎一致：从反汇编看，引擎传的是
    //   iQuality = 2 (PROOF)、iPitchAndFamily = 0x30、其余 0
    // 之前这里传 0，导致 GDI 选中的是 MS PGothic 而不是引擎实际用的 MS Gothic，
    // 量出来的数字也就不是引擎看到的那一份。
    HFONT font = CreateFontA(height, 0, 0, 0, 400, FALSE, FALSE, FALSE,
                             s.charset, 0, 0, 2 /*PROOF*/, 0x30, s.face);
    HDC dc = CreateCompatibleDC(NULL);
    HGDIOBJ old = SelectObject(dc, font);

    char actual[LF_FACESIZE] = { 0 };
    GetTextFaceA(dc, LF_FACESIZE, actual);

    TEXTMETRICA tm;
    ZeroMemory(&tm, sizeof(tm));
    GetTextMetricsA(dc, &tm);

    int advCJK  = glyph_advance(dc, 0xC4C7);   // 「那」
    int advHalf = glyph_advance(dc, 0x0041);   // 「A」

    printf("%s\n", s.label);
    printf("    实际选中字体 : %s\n", actual);
    printf("    tmHeight=%ld  tmAscent=%ld  tmDescent=%ld  tmExternalLeading=%ld\n",
           tm.tmHeight, tm.tmAscent, tm.tmDescent, tm.tmExternalLeading);
    printf("    tmAveCharWidth=%ld  tmMaxCharWidth=%ld  tmWeight=%ld  tmOverhang=%ld\n",
           tm.tmAveCharWidth, tm.tmMaxCharWidth, tm.tmWeight, tm.tmOverhang);
    printf("    tmPitchAndFamily=0x%02X   %s   charset=%d\n",
           tm.tmPitchAndFamily,
           (tm.tmPitchAndFamily & TMPF_FIXED_PITCH) ? "比例字体(非等宽)" : "等宽字体",
           (int)tm.tmCharSet);
    printf("    字形步进: 全角「那」=%d px, 半角「A」=%d px\n", advCJK, advHalf);
    if (tm.tmHeight > 0)
        printf("    >> 若每行按 tmHeight 估算可容纳: 1000px / %ld = %ld 字\n",
               tm.tmHeight, 1000 / tm.tmHeight);
    if (advCJK > 0)
        printf("    >> 若每行按全角步进估算:       1000px / %d = %d 字\n",
               advCJK, 1000 / advCJK);
    printf("\n");

    SelectObject(dc, old);
    DeleteDC(dc);
    DeleteObject(font);
}

int main(void)
{
    // h=-40 是引擎画正文用的；h=0 是它另外建过的一种，可能是用来量尺寸的
    static const int heights[] = { -40, 0 };
    for (int i = 0; i < 2; ++i) {
        printf("################  lfHeight = %d  ################\n\n", heights[i]);
        for (int j = 0; j < (int)(sizeof(kSamples) / sizeof(kSamples[0])); ++j)
            measure(kSamples[j], heights[i]);
    }
    return 0;
}
