// glyph_hook_test.exe —— 离线验证 ♪ 哨兵 hook（不需要开游戏）
//
// 思路：这个 exe 自己静态导入 GetGlyphOutlineA，所以 cnpatch.dll 的 IAT 改写
// 会打到它的头上。于是可以：
//   1) 装 DLL 之前，量哨兵(0xA140) 的字形
//   2) LoadLibrary 装 DLL
//   3) 再量一次哨兵 —— 如果 hook 生效，它应该变得和真 ♪ 一模一样
//
// 关键点：GetGlyphOutlineA 不按 Unicode 解释 uChar，它按当前代码页（GBK）解释。
// 所以「♪ 长什么样」这个基准值只能用 GetGlyphOutlineW 量 —— 这正是 hook 内部
// 偷偷做的事。拿 A 版传 0x266A 量出来的不是 ♪，是 GBK 字节 0x26 0x6A。
//
// 字体参数完全照抄引擎（CreateFontA(-40, charset=134, "ＭＳ ゴシック", q=2, family=0x30)）。
// 必须编译成 32 位，和游戏一致。
//
// 用法：set CMVS_PATCH=0 && glyph_hook_test.exe [cnpatch.dll 的完整路径]

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

#pragma comment(lib, "gdi32.lib")

// 引擎请求的字体名原始字节（Shift-JIS「ＭＳ ゴシック」）
static const char kEngineFace[] = "\x82\x6C\x82\x72\x20\x83\x53\x83\x56\x83\x62\x83\x4E";

static const UINT kNoteSentinel     = 0xA140;
static const UINT kNoteSentinelSwap = 0x40A1;
static const UINT kNoteChar         = 0x266A;   // ♪

// ♪ 的字形由哪个字体提供 —— 必须和 cnpatch.cpp 里 g_notefont 的默认值一致，
// 否则基准量错了会误报。两边都认 CMVS_NOTEFONT，改的时候一起改。
static char g_notefont[64] = "NSimSun";

struct M { int adv; int black_x; };   // adv=-1 表示没有字形

// 自己记一份调用流水，用来和 cnpatch.log 对齐：
// 两边一比就知道哪几次真的进了 hook、哪几次绕过去了。
static FILE* g_trace;
static LONG  g_seq;

static void trace(HDC dc, UINT uChar)
{
    if (!g_trace) return;
    LONG n = InterlockedIncrement(&g_seq);
    fprintf(g_trace, "trace\t%d 0x%04X hdc=%p\n", (int)n, uChar, (void*)dc);
    fflush(g_trace);
}

// 不透明屏障：只用来压住编译器把 IAT 里的函数指针缓存进寄存器。
// 没有它，/O2 会让「装完 DLL 之后再调」仍然走旧指针（见 cnpatch 文档 §8.4）。
static void barrier(void)
{
    if (g_trace) fflush(g_trace);
}

static M probeA(HDC dc, UINT uChar)
{
    trace(dc, uChar);
    MAT2 mat = { {0,1},{0,0},{0,0},{0,1} };
    GLYPHMETRICS gm; ZeroMemory(&gm, sizeof(gm));
    DWORD n = GetGlyphOutlineA(dc, uChar, GGO_METRICS, &gm, 0, NULL, &mat);
    if (n == GDI_ERROR) return { -1, -1 };
    return { (int)gm.gmCellIncX, (int)gm.gmBlackBoxX };
}

static M probeW(HDC dc, UINT cp)
{
    MAT2 mat = { {0,1},{0,0},{0,0},{0,1} };
    GLYPHMETRICS gm; ZeroMemory(&gm, sizeof(gm));
    DWORD n = GetGlyphOutlineW(dc, cp, GGO_METRICS, &gm, 0, NULL, &mat);
    if (n == GDI_ERROR) return { -1, -1 };
    return { (int)gm.gmCellIncX, (int)gm.gmBlackBoxX };
}

// 字体名是按系统码页(936)编的字节串，转宽字符才能好好打出来。
// （混用 printf 和 wprintf 在同一路输出上会互相打架，所以统一用 printf + %ls）
static void to_wide(const char* ansi, wchar_t* out, int cch)
{
    out[0] = 0;
    if (!MultiByteToWideChar(936, 0, ansi, -1, out, cch)) out[0] = 0;
}

static void show(const char* label, M m)
{
    if (m.adv < 0) printf("    %-22s : 无字形\n", label);
    else           printf("    %-22s : 步进=%4d  黑框宽=%d\n", label, m.adv, m.black_x);
}

// 哨兵和反序哨兵要从 volatile 里读，不能写成字面常量。
//
// 坑：`probeA(dc, kNoteSentinel)` 在装 DLL 前后各调一次，两次实参完全相同，
// /O2 会把第二次认成「重复的纯调用」给合并掉 —— 于是「装完 DLL 再量」量到的
// 还是装之前的结果，hook 明明生效了，自检却报失败。用 volatile 断掉这个假设。
static volatile UINT g_sentinel_v     = 0xA140;
static volatile UINT g_sentinel_swap_v = 0x40A1;

// 对照组：一批不该被 hook 碰到的码位。装 DLL 前后必须一模一样。
// 不预设它们的数值 —— 不同 charset 下同一个 uChar 本来就含义不同，
// 断言「变了没有」比断言「等于多少」更准。
static const UINT kControls[] = {
    0x0041,   // 'A'
    0x007E,   // '~'
    0x8140,   // 全角空格（SJIS）/ GBK 的空格区
    0xA1A1,   // GBK 全角空格
    0xC4C7,   // GBK「那」
    0xB0A1,   // GBK「啊」
    0x8141,   // 边界
    0xFE9F,   // 尾字节 0x9F 的汉字（补丁 1 放宽判定就是为了它）
    0xA140 ^ 0x0100,  // 哨兵换一个字节 —— 必须不被认成哨兵
};

// 按字体名直接建 DC。用来造 ♪ 的基准 —— 补丁特意给 ♪ 另找了一个有该字形的字体
// （正文用的黑体没有 ♪），所以基准不能再拿引擎那个 DC 量。
static HDC make_named_dc(const char* face, int charset, int height)
{
    HFONT font = CreateFontA(height, 0, 0, 0, 400, FALSE, FALSE, FALSE,
                             charset, 0, 0, 2, 0x30, face);
    HDC dc = CreateCompatibleDC(NULL);
    SelectObject(dc, font);
    return dc;
}

static int run_case(const char* label, int charset, int height, const wchar_t* dll_path)
{
    HFONT font = CreateFontA(height, 0, 0, 0, 400, FALSE, FALSE, FALSE,
                             charset, 0, 0, 2 /*PROOF*/, 0x30, kEngineFace);
    HDC dc = CreateCompatibleDC(NULL);
    SelectObject(dc, font);

    char face[64] = { 0 };
    GetTextFaceA(dc, 64, face);
    printf("  实际选中字体(B) :");
    for (int i = 0; face[i]; ++i) printf(" %02X", (unsigned char)face[i]);
    printf("\n");

    printf("  DC           : %p\n", (void*)dc);

    // 引擎这个 DC 自己给出的 ♪（可能是豆腐块 —— 黑体就没有这个字形）
    M note_eng = probeW(dc, kNoteChar);

    // 真正的基准：用确定有 ♪ 的字体量一份。补丁内部就是这么干的。
    HDC bdc = make_named_dc(g_notefont, DEFAULT_CHARSET, height);
    M note = probeW(bdc, kNoteChar);
    char bface[LF_FACESIZE] = { 0 };
    GetTextFaceA(bdc, LF_FACESIZE, bface);
    printf("  ♪ 基准(%s) : 步进=%d 黑框宽=%d  [实际选中 ", g_notefont, note.adv, note.black_x);
    for (int i = 0; bface[i]; ++i) printf("%02X ", (unsigned char)bface[i]);
    printf("]\n");
    printf("  引擎 DC 自己的 ♪  : 步进=%d 黑框宽=%d%s\n", note_eng.adv, note_eng.black_x,
           (note_eng.black_x == note.black_x && note_eng.adv == note.adv)
               ? "（和基准一样）" : "（和基准不同 —— 所以才要另找字体）");

    M before[sizeof(kControls)/sizeof(kControls[0])];
    for (int i = 0; i < (int)(sizeof(kControls)/sizeof(kControls[0])); ++i)
        before[i] = probeA(dc, kControls[i]);
    M before_sent = probeA(dc, g_sentinel_v);

    printf("\n  [装 DLL 之前]\n");
    show("♪ U+266A（引擎 DC，W 版）", note_eng);
    show("哨兵 0xA140（A 版）", before_sent);

    HMODULE dll = LoadLibraryW(dll_path);
    if (!dll) {
        printf("\n  *** 装载 %ls 失败 err=%lu ***\n\n", dll_path, GetLastError());
        return 0;
    }
    printf("\n  [已装载 cnpatch.dll]\n");

    // 注意：这三次调用必须真的排在 LoadLibrary 之后。
    // 它们的实参全是编译期常量，没有数据依赖，/O2 会把它们**提到 LoadLibrary 前面**去，
    // 结果就是「装完 DLL 再量」量到的还是装之前的值 —— 自检就成了假阴性。
    // 所以这里人为挂一个对 dll 的依赖，压住重排。（踩过一次）
    M after = { -99, -99 }, swap = { -99, -99 }, note_again = { -99, -99 };
    if (dll) {
        // 两个路标：只在装完 DLL 之后打，值在全程序里独一无二。
        // 日志里看得到它们，就说明这一段确实走了 hook。
        probeA(dc, 0x3039);                  // 路标 A
        after      = probeA(dc, g_sentinel_v);
        probeA(dc, 0x303A);                  // 路标 B
        swap       = probeA(dc, g_sentinel_swap_v);
        note_again = probeW(dc, kNoteChar);   // 同一个 DC 再量一次 ♪，看它自己稳不稳
    }

    show("哨兵 0xA140（A 版）", after);
    show("反序 0x40A1（A 版）", swap);
    show("♪ U+266A（W 版，再量）", note_again);

    int changed = 0;
    printf("\n  [对照组：不该被动的码位]\n");
    for (int i = 0; i < (int)(sizeof(kControls)/sizeof(kControls[0])); ++i) {
        M now = probeA(dc, kControls[i]);
        int same = (now.adv == before[i].adv && now.black_x == before[i].black_x);
        if (!same) ++changed;
        printf("    0x%04X : 前 %4d/%2d  后 %4d/%2d   %s\n",
               kControls[i], before[i].adv, before[i].black_x,
               now.adv, now.black_x, same ? "未变" : "*** 变了 ***");
    }

    // 换字体（补丁 [4]）自检：装完 DLL 后再建一个字体，看 GDI 实际选中谁。
    // 期望：charset=134 + 引擎字体名 原本会替换成新宋体（D0 C2 CB CE CC E5），
    //       被 hook 改过之后应该变成黑体（BA DA CC E5）。
    //       度量必须和新宋体一致（tmMaxCharWidth 都是 40），否则排版会算错。
    wchar_t face_after[64] = { 0 };
    char    face_raw[LF_FACESIZE] = { 0 };
    TEXTMETRICA tm_after; ZeroMemory(&tm_after, sizeof(tm_after));
    M note_after = { -99, -99 };
    M sent_on_black = { -99, -99 };
    if (dll) {
        barrier();
        HFONT f2 = CreateFontA(height, 0, 0, 0, 400, FALSE, FALSE, FALSE,
                               charset, 0, 0, 2, 0x30, kEngineFace);
        HDC dc2 = CreateCompatibleDC(NULL);
        SelectObject(dc2, f2);
        GetTextFaceA(dc2, LF_FACESIZE, face_raw);
        to_wide(face_raw, face_after, 64);
        GetTextMetricsA(dc2, &tm_after);
        // 这个 DC 用的就是换过之后的字体（黑体）。它在游戏里正是画正文的那一个。
        note_after = probeW(dc2, kNoteChar);            // 黑体自己的 ♪ —— 会是豆腐块
        if (charset == 134) {
            barrier();
            sent_on_black = probeA(dc2, g_sentinel_v);  // 哨兵走 hook 取到的 ♪
        }
        DeleteDC(dc2);
        DeleteObject(f2);
    }

    int ok_hook   = (after.adv == note.adv && after.adv > 0);
    int ok_box    = (after.black_x == note.black_x);
    int ok_swap   = (swap.adv == note.adv && swap.adv > 0);
    int ok_ctl    = (changed == 0);
    int ok_before = (before_sent.adv != note.adv || before_sent.black_x != note.black_x);


    printf("\n  [换字体：装 DLL 后新建的 charset=%d 字体]\n", charset);
    printf("    实际选中   : %ls\n", face_after);
    // 名字也打一份原始字节：控制台码页不对时 %ls 会打空，字节不会骗人。
    // 新宋体 = D0 C2 CB CE CC E5，黑体 = BA DA CC E5，MS Gothic = 4D 53 20...
    printf("    名字原始字节: ");
    for (int i = 0; face_raw[i]; ++i) printf("%02X ", (unsigned char)face_raw[i]);
    printf("\n");
    printf("    tmHeight=%ld  tmAveCharWidth=%ld  tmMaxCharWidth=%ld\n",
           tm_after.tmHeight, tm_after.tmAveCharWidth, tm_after.tmMaxCharWidth);
    printf("    ♪ 步进     : %d\n", note_after.adv);
    // 只有 charset==134 那一处会被换字体；128 那档本来就该保持 MS Gothic，
    // 它的 tmMaxCharWidth 就是 79，不能拿 40 去要求它。
    int ok_maxw = (charset != 134) ? 1 : (tm_after.tmMaxCharWidth == 40);
    printf("    tmMaxCharWidth %s : %s\n",
           charset != 134 ? "（本档不换字体，不作要求）" : "仍是 40（排版宽度不变）",
           ok_maxw ? "OK" : "*** 变了 ***");

    // 复现游戏里的真实场景：正文用黑体，黑体没有 ♪。
    // 哨兵在**这个** DC 上必须仍然拿到真 ♪（走私有字体），不能拿到黑体的豆腐块。
    int ok_black = 1;
    if (charset == 134) {
        ok_black = (sent_on_black.adv == note.adv && sent_on_black.black_x == note.black_x);
        printf("\n    [黑体 DC 上问哨兵 —— 复现游戏里的情况]\n");
        printf("      黑体自己的 ♪     : 步进=%d 黑框宽=%d%s\n",
               note_after.adv, note_after.black_x,
               (note_after.adv == note.adv && note_after.black_x == note.black_x)
                   ? "（黑体居然有 ♪）" : "（不是真 ♪ —— 黑体没这个字形）");
        printf("      哨兵经 hook 取到 : 步进=%d 黑框宽=%d  期望 %d/%d  -> %s\n",
               sent_on_black.adv, sent_on_black.black_x, note.adv, note.black_x,
               ok_black ? "通过" : "*** 失败，会显示成豆腐块 ***");
    }

    printf("\n  [判定]\n");
    printf("    哨兵还原成 ♪      : %s（哨兵 %d/%d vs ♪ %d/%d）\n",
           ok_hook ? "通过" : "失败", after.adv, after.black_x, note.adv, note.black_x);
    printf("    黑框尺寸也一致     : %s\n", ok_box ? "通过" : "失败");
    printf("    反序字节序也认     : %s（%d vs %d）\n",
           ok_swap ? "通过" : "失败", swap.adv, note.adv);
    printf("    对照组全部未变     : %s（变了 %d 个）\n",
           ok_ctl ? "通过" : "失败", changed);
    printf("    装 DLL 前哨兵≠♪    : %s\n",
           ok_before ? "是（本用例能证明 hook 确实改了结果）"
                     : "否（哨兵本来就长得和 ♪ 一样，本用例证明不了 hook，但也没反证）");
    printf("\n");

    int all = ok_hook && ok_box && ok_swap && ok_ctl && ok_maxw && ok_black;
    DeleteDC(dc);
    DeleteObject(font);
    return all;
}

int main(int argc, char** argv)
{
    printf("♪ 哨兵 hook 离线自检\n\n");
    fopen_s(&g_trace, "probe_trace.txt", "w");

    {
        char v[64];
        if (GetEnvironmentVariableA("CMVS_NOTEFONT", v, sizeof(v)) > 0)
            lstrcpynA(g_notefont, v, sizeof(g_notefont));
    }

    const wchar_t* dll = L"C:\\Users\\DMS\\Desktop\\Hapymaher\\test\\hooklog\\cnpatch.dll";
    wchar_t wbuf[MAX_PATH];
    if (argc > 1 && MultiByteToWideChar(CP_ACP, 0, argv[1], -1, wbuf, MAX_PATH) > 0)
        dll = wbuf;

    int ok = 1;
    printf("================================================\n");
    printf("引擎参数：charset=134（补丁后）\n");
    ok &= run_case("charset=134", 134, -40, dll);

    printf("================================================\n");
    printf("引擎参数：charset=128（原版）\n");
    ok &= run_case("charset=128", 128, -40, dll);

    printf("================================================\n");
    printf("总判定：%s\n", ok ? "全部通过" : "*** 有失败项 ***");
    printf("日志见本目录 cnpatch.log（本程序的调用流水见 probe_trace.txt）\n");
    if (g_trace) fclose(g_trace);
    return ok ? 0 : 1;
}
