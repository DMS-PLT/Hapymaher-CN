// cnpatch.dll —— 汉化加载补丁（全程只在内存里改，不动游戏任何文件）
//
// 做两件事：
//
//   [1] 代码补丁：引擎里有三处独立的「Shift-JIS 首字节」判定，判据是
//       0x81 <= b <= 0x9F 或 0xE0 <= b <= 0xFC。中文用 GBK，首字节能到 0xFE，
//       超出这个范围就会被当成单字节拆开 —— 其中第三处管的是文本标记扫描
//       （找 \n 之类），漏掉它会导致尾字节 0x5C 的汉字被当成反斜杠，正文凭空断行。
//       所以三处全部把上界 0x9F 放宽到 0xFE，与已验证过的 AI 补丁语义一致。
//
//   [2] 字体：引擎用 CreateFontA 建字体，charset 由 exe 里的 FONT_SHIFT_JIS
//       决定（0x80 Shift-JIS / 0x00 ANSI）。ANSI 会让 GDI 回退到 Courier New
//       （没有汉字），所以必须在 API 层强制 charset = 134(GB2312)，同时把字体名
//       换成中文字体。
//
//   [3] ♪（音符）：GBK 装不下这个字符 —— 而且不是「变成问号」，是让
//       PS3_TextEditor 整个脚本构建失败（RxCvt::ToMBCS Error!）。所以译文里
//       用「哨兵」占位：字节对 0xA1 0x40（CP936 解到 U+E4C6，GBK 用户区，
//       正常中文永远产不出它；107,142 条实测 0 次 PUA）。
//       这里 hook GetGlyphOutlineA，认到哨兵就转调 GetGlyphOutlineW 取真正的
//       ♪（U+266A）字形。宽度由返回的 GLYPHMETRICS 决定，排版不受影响。
//
//   [4] 正文字体换成黑体。补丁 [2] 只改 charset，字体名还是「ＭＳ ゴシック」，
//       GDI 于是自动替换成「新宋体」。这里在 CreateFontA 处把**那一个调用点**
//       （charset == 134 的）的字体名换成黑体。
//       为什么安全：实测黑体(charset 134) 与新宋体(charset 134) 度量逐项相同 ——
//       tmHeight 40、tmAveCharWidth 20、tmMaxCharWidth 40、汉字步进 40、
//       ASCII 20、全角空格 40。引擎按 GetTextMetricsA 算的排版宽度不会变。
//       （别把 4 个调用点全换 —— 见 CMVS_FONTHOOK，那是坑。）
//
//   [5] 窗口标题。start.ps3 里那串标题是 SJIS，游戏原样交给 SetWindowTextA，
//       Windows 按系统码页(GBK)解释 → 乱码。构建时已把它改成等长的 GBK（见
//       test/cntest/build_encrypted.py 的 TITLES）；这里补的是另一段：引擎拼标题时
//       还在中间插了一个 SJIS 的全角空格 0x81 0x40，同样被误读成一个乱码字。
//       就地换成 GBK 的 0xA1 0xA1，等长。这是 §3.3 那个坑的第二次现身。
//
// 行为可调（环境变量，都在启动前设）：
//   CMVS_PATCH      设 0 则跳过所有代码补丁（对照用）
//   CMVS_FONTHOOK   默认关。设 1 才启用 CreateFontA 全量 hook（换字体用）。
//                   注意：开了它会把 4 个 CreateFontA 调用点全改掉，排版宽度会算错，
//                   是我们排查过的坑，除非专门做字体实验别开。
//   CMVS_FONT       字体名，两种字体模式共用，默认 SimHei
//   CMVS_FACESWAP   默认开。设 0 则不做 [4] 的正文换字体（回到 GDI 自动替换的新宋体）
//   CMVS_NOTE       设 0 则不做 ♪ 哨兵映射（对照用）
//   CMVS_TITLE      设 0 则不改窗口标题里的 SJIS 全角空格（对照用）
//   CMVS_NOTEFONT   ♪ 的字形从哪个字体取，默认 NSimSun（新宋体）。**必须是有 ♪ 的字体**
//                   （GB18030 那几档：新宋体 / 宋体 / MS Gothic）。正文用的黑体没有。
//   CMVS_UIFONT     默认开。给对话框里的控件也换上 CMVS_FONT 那个中文字体（见 ui_fix_font）。
//                   设 0 则保持模板自带的 ＭＳ ゴシック。字体名跟 CMVS_FONT 走。
//   CMVS_NOLOG      设 1 则不写日志
//
// 日志写在游戏 exe 同目录的 cnpatch.log。
// 必须编译成 32 位（游戏是 32 位进程）。

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

// ─────────────────────────── 配置 ───────────────────────────

struct CodePatch {
    DWORD va;        // 虚拟地址
    BYTE  from;      // 期望的原字节（不符就报错，绝不盲写）
    BYTE  to;
    const char* what;
};

// 首选基址 0x400000 下的 VA。实际地址会按 exe 真实基址重定位。
//
// 这里一共 9 处，不是 3 处。
//
// 每处都是同一段判定的不同内联副本，形状固定：
//     cmp  X, 0x81
//     jb   L1
//     cmp  X, 0x9F      ← 改这里
//     jbe  L2           ; 双字节
// L1: lea  t, [X+0x20]
//     cmp  t, 0x1C      ; 移位技巧判 0xE0-0xFC
//     ja   L3
// L2: ...               ; 走双字节
// L3: ...               ; 走单字节
//
// 早先只找到 3 处（都是 cmp al 形式），漏掉了 cmp cl/dl/bl 形式的另外 6 处。
// 漏掉的里面有一个是排版用的「这个字占几格」计算：GBK 汉字的字节（C4 CA D2 B8…
// 全落在 0xA0-0xDF，那是 SJIS 半角片假名的区间，被原判定排除 → 引擎把汉字当成
// 半角单字节 → 每行只按一半宽度算 → 文字框缩窄到一半，正文溢出。
// 注意：这里填的是**立即数字节的地址**，不是 cmp 指令的地址。
// `3C 9F` 是两字节指令，立即数在 +1；`80 F9 9F` 是三字节，立即数在 +2。
static const CodePatch kPatches[] = {
    { 0x418659, 0x9F, 0xFE, "dbcs_418657"  },
    { 0x41A099, 0x9F, 0xFE, "dbcs_41A097"  },
    { 0x41A3AB, 0x9F, 0xFE, "is_sjis_lead" },   // 独立函数 0x41A3A0，57 处调用
    { 0x41A3E9, 0x9F, 0xFE, "dbcs_41A3D0"  },
    { 0x41A436, 0x9F, 0xFE, "dbcs_strcmp"  },   // 0x41A421
    { 0x41A4A6, 0x9F, 0xFE, "dbcs_41A490"  },
    { 0x41A519, 0x9F, 0xFE, "dbcs_41A500"  },
    { 0x41A62B, 0x9F, 0xFE, "dbcs_find"    },   // 0x41A610，文本标记扫描
    { 0x41A709, 0x9F, 0xFE, "dbcs_41A6D0"  },

    // CreateFontA 第 1 个调用点（0x461DCB）的 charset 参数：0x80(SJIS) → 0x86(GB2312)。
    // 指令是 0x461DA9 的 `push 0x80`，立即数在 0x461DAA。
    //
    // 只改这一处，另外 3 个 CreateFontA 调用点保持 0x80 —— 这是照抄已验证过的
    // AI 补丁（它的 exe 里就是同一个字节 0x80→0x86）。原因是我们发现：
    // charset 134 的字体 tmMaxCharWidth=40，而 charset 128 的 MS Gothic 是 79。
    // 引擎的排版拿其中某一份去算，把 4 个全改会让排版宽度算错一半。
    { 0x461DAA, 0x80, 0x86, "charset_GB2312" },
};

// ─────────────── 补丁 1b：字体名默认值（字符串） ───────────────
//
// 「系统设置 → 字体设置」那个输入框显示的是**引擎配置项的默认值**，
// 来自 exe 里这份 SJIS 的「ＭＳ ゴシック」（13 字节 + NUL，紧跟着 "FONT" 键名，
// 所以整块槽位只有 16 字节）。
// 注意地址是 VA 0x4D1C08 —— 文件偏移是 0xD0008，位于 .rdata 节
// （.rdata: VA=0xC8000 / raw=0xC6400，RVA = 0xC8000 + (0xD0008 - 0xC6400) = 0xD1C08）。
// 别再把文件偏移当 RVA 用，第一次就这么写错、被原字节校验挡下来了。
//
// 关键实测结论：**改 cmvs.cfg 的 FONT= 没用** —— 游戏不看文件里的值决定显示什么，
// 反而在退出时把内存里的值写回 cfg，把我们改的值覆盖掉（2026-10-29 实测）。
// 双字节判定已改成 GBK，这串 SJIS 字节于是被按 GBK 画成「俵俽 僑僔僢僋」六个生僻字。
//
// 改成 GBK 的「黑体」：显示正确，而且与补丁 [4] 实际渲染的字体一致。
// 只能写在槽位内（不能变长），否则会踩到后面的键名表。
struct StrPatch {
    DWORD va;
    const BYTE* expect;      // 期望的原字节
    size_t      expect_len;  // 字节数，不含结尾 NUL
    const BYTE* repl;        // 替换字节（GBK）
    size_t      repl_len;
    size_t      slot;        // 整个槽位的可写长度（含结尾 NUL 与对齐填充）
    const char* what;
};

static const BYTE kFaceMSSJIS[] =          // ＭＳ ゴシック
    { 0x82, 0x6C, 0x82, 0x72, 0x20, 0x83, 0x53, 0x83, 0x56, 0x83, 0x62, 0x83, 0x4E };
static const BYTE kFaceHeitiGBK[] =        // 黑体
    { 0xBA, 0xDA, 0xCC, 0xE5 };

static const StrPatch kStrPatches[] = {
    { 0x4D1C08, kFaceMSSJIS, sizeof(kFaceMSSJIS),
      kFaceHeitiGBK, sizeof(kFaceHeitiGBK), 16, "font_default" },
};

// 期望值全是 0x9F → 0xFE。改后判定范围变成 0x81-0xFE（正好是 GBK 首字节范围）。
// 对原本的 SJIS 文本无影响：SJIS 首字节本来就 ≤0xFC，且 0xFD/0xFE 是非法字节。

static const UINT kGB2312_CHARSET = 134;

// ────────────────── 补丁 3：♪ 的哨兵映射 ──────────────────
//
// 译文里的 ♪ 在构建时被写成这个字节对（见 test/cntest/build_test.py 的 clean()）。
// 0xA1 0x40 落在 GBK 用户区（CP936 把它解到 U+E4C6），任何输入法、任何译者都不会
// 产出它 —— 全 107,142 条语料实测 0 次 PUA，零撞车。
//
// 引擎把双字节码拼成一个 WORD 传给 GetGlyphOutlineA，两种字节序都收下：
//   uChar = 0xA140（首字节在高位）或 0x40A1（首字节在低位）
// 其中 0x40A1 对应首字节 0x40，本来就不是合法的 GBK 首字节，所以不会误伤真字符。
static const UINT kNoteSentinel     = 0xA140;
static const UINT kNoteSentinelSwap = 0x40A1;
static const UINT kNoteChar         = 0x266A;   // ♪

// ─────────────────────────── 全局 ───────────────────────────

typedef HFONT(WINAPI* PFN_CreateFontA)(int, int, int, int, int, DWORD, DWORD, DWORD,
                                       DWORD, DWORD, DWORD, DWORD, DWORD, LPCSTR);
typedef HFONT(WINAPI* PFN_CreateFontIndirectA)(const LOGFONTA*);
typedef DWORD(WINAPI* PFN_GetGlyphOutlineA)(HDC, UINT, UINT, LPGLYPHMETRICS, DWORD, LPVOID, const MAT2*);
typedef DWORD(WINAPI* PFN_GetGlyphOutlineW)(HDC, UINT, UINT, LPGLYPHMETRICS, DWORD, LPVOID, const MAT2*);
typedef BOOL(WINAPI* PFN_SetWindowTextA)(HWND, LPCSTR);
typedef BOOL(WINAPI* PFN_SetWindowTextW)(HWND, LPCWSTR);
typedef BOOL(WINAPI* PFN_SetDlgItemTextA)(HWND, int, LPCSTR);
typedef BOOL(WINAPI* PFN_SetDlgItemTextW)(HWND, int, LPCWSTR);
typedef LRESULT(WINAPI* PFN_SendMessageA)(HWND, UINT, WPARAM, LPARAM);
typedef LRESULT(WINAPI* PFN_SendMessageW)(HWND, UINT, WPARAM, LPARAM);
typedef INT_PTR(WINAPI* PFN_DialogBoxParamA)(HINSTANCE, LPCSTR, HWND, DLGPROC, LPARAM);
typedef INT_PTR(WINAPI* PFN_DialogBoxParamW)(HINSTANCE, LPCWSTR, HWND, DLGPROC, LPARAM);
typedef HWND(WINAPI* PFN_CreateWindowExA)(DWORD, LPCSTR, LPCSTR, DWORD, int, int, int, int,
                                          HWND, HMENU, HINSTANCE, LPVOID);
typedef HMENU(WINAPI* PFN_LoadMenuA)(HINSTANCE, LPCSTR);
typedef BOOL(WINAPI* PFN_SetMenuItemInfoA)(HMENU, UINT, BOOL, LPCMENUITEMINFOA);
typedef BOOL(WINAPI* PFN_SetMenuItemInfoW)(HMENU, UINT, BOOL, LPCMENUITEMINFOW);
typedef int(WINAPI* PFN_MessageBoxA)(HWND, LPCSTR, LPCSTR, UINT);
typedef int(WINAPI* PFN_MessageBoxW)(HWND, LPCWSTR, LPCWSTR, UINT);

// 文件打开探针（只记录，不改行为）。用来查「引擎到底向系统要了哪个路径」。
typedef HANDLE(WINAPI* PFN_CreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                        DWORD, DWORD, HANDLE);
typedef HANDLE(WINAPI* PFN_CreateFileW)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                        DWORD, DWORD, HANDLE);
typedef BOOL(WINAPI* PFN_ReadFile)(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);

static PFN_CreateFontA         real_CreateFontA;
static PFN_CreateFontIndirectA real_CreateFontIndirectA;
static PFN_GetGlyphOutlineA    real_GetGlyphOutlineA;
static PFN_GetGlyphOutlineW    real_GetGlyphOutlineW;
static PFN_SetWindowTextA      real_SetWindowTextA;
static PFN_SetWindowTextW      real_SetWindowTextW;
static PFN_SetDlgItemTextA     real_SetDlgItemTextA;
static PFN_SetDlgItemTextW     real_SetDlgItemTextW;
static PFN_SendMessageA        real_SendMessageA;
static PFN_SendMessageW        real_SendMessageW;
static PFN_DialogBoxParamA     real_DialogBoxParamA;
static PFN_DialogBoxParamW     real_DialogBoxParamW;
static PFN_CreateWindowExA     real_CreateWindowExA;
static PFN_LoadMenuA           real_LoadMenuA;
static PFN_SetMenuItemInfoA    real_SetMenuItemInfoA;
static PFN_SetMenuItemInfoW    real_SetMenuItemInfoW;
static PFN_MessageBoxA         real_MessageBoxA;
static PFN_MessageBoxW         real_MessageBoxW;
static PFN_CreateFileA         real_CreateFileA;
static PFN_CreateFileW         real_CreateFileW;
static PFN_ReadFile            real_ReadFile;

// 字体选择列表：引擎用 EnumFontFamiliesExA 枚举系统字体，我们包一层回调过滤。
typedef int(WINAPI* PFN_EnumFontFamiliesExA)(HDC, LPLOGFONTA, FONTENUMPROCA, LPARAM, DWORD);
static PFN_EnumFontFamiliesExA real_EnumFontFamiliesExA;

static FILE*            g_log;
static CRITICAL_SECTION g_cs;
static volatile LONG    g_bytes;
static const long       LOG_LIMIT = 4L * 1024 * 1024;

static char g_font[LF_FACESIZE] = "SimHei";
static BOOL g_enable_patch = TRUE;
// 默认关闭。字符集现在靠 kPatches 里那一字节的调用点补丁解决，
// 全量 hook CreateFontA 会把 4 个调用点一起改掉，排版宽度会算错。
// 想实验换字体时再设 CMVS_FONTHOOK=1 打开。
static BOOL g_enable_font  = FALSE;
// 正文换字体（补丁 [4]，只动 charset==134 那一个调用点）。默认开。
static BOOL g_enable_face  = TRUE;
// ♪ 哨兵映射。默认开：只影响哨兵那一个码位，对其它码位是纯转发，没有副作用。
static BOOL g_enable_note  = TRUE;
// 窗口标题里的 SJIS 全角空格（0x81 0x40）→ GBK（0xA1 0xA1）。默认开，见 §3.6。
static BOOL g_enable_title = TRUE;
// ♪ 的字形从哪个字体取。见 note_dc() 的说明。
// 默认新宋体：它是 GB18030 字体，♪ 齐全，笔画和黑体配起来舒服。
// 想换别的（MS Gothic / 宋体 …）用 CMVS_NOTEFONT。
static char g_notefont[LF_FACESIZE] = "NSimSun";

// 对话框控件也换成中文字体。默认开，见 ui_fix_font()。
// 为什么必须换：模板自带的字体是 **ＭＳ Ｐゴシック**（日文），
// 简体字里像「复」这种**不在 JIS 里的字**，GDI 会做字体链接去别的字体借字形 ——
// 结果同一个词「复原功能」里，「原/功/能」来自 MS Gothic，「复」来自借来的字体，
// 笔画粗细和字面大小都对不上，看着就是「有个字长歪了」。
// 换成中文字体后整条都来自同一份字档，问题消失。
static BOOL      g_enable_uifont = TRUE;
static wchar_t   g_uifont[LF_FACESIZE] = L"SimHei";

// 建过的字体缓存。键是**源字体的 LOGFONT**（高度/粗细/斜体/字名），
// 命中就复用 —— 不然每个控件都建一个 HFONT，还会连锁触发
// 「我们的字体又被当成源字体」的无限套娃。
struct UiFontEntry { LOGFONTW src; HFONT h; };
static UiFontEntry g_uifonts[16];
static int         g_uifonts_n;
static volatile LONG g_uifont_calls;

// ♪ 专用的私有 DC / 字体。懒创建（不在 DllMain 里建，避免占着加载器锁）。
static HDC       g_note_dc;
static HFONT     g_note_font;
static LOGFONTA  g_note_src_lf;     // 上次建私有字体时，源 DC 的 LOGFONT（用来判断要不要重建）
static volatile LONG g_font_calls;
static volatile LONG g_glyph_calls;
static volatile LONG g_note_hits;
static volatile LONG g_title_calls;

static void logf(const char* fmt, ...)
{
    if (!g_log) return;
    if (InterlockedCompareExchange(&g_bytes, 0, 0) > LOG_LIMIT) return;

    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    int n = _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    if (n <= 0) return;

    EnterCriticalSection(&g_cs);
    fwrite(buf, 1, n, g_log);
    InterlockedExchangeAdd(&g_bytes, n);
    // 平时按缓冲区刷；崩了由 veh_crash 显式 flush，不会丢最后的线索
    if ((g_bytes & 0xFFF) < 512) fflush(g_log);
    LeaveCriticalSection(&g_cs);
}

// ─────────────────────── 补丁 1：代码字节 ───────────────────────

// 返回失败条数。失败说明 exe 与预期版本不符，绝不能继续。
static int apply_code_patches()
{
    HMODULE exe = GetModuleHandleW(NULL);
    BYTE* base = (BYTE*)exe;

    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) { logf("patch\tDOS 头无效\n"); return 1; }
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) { logf("patch\tNT 头无效\n"); return 1; }

    // 按 exe 自己的 ImageBase 重定位，别假设就是 0x400000
    DWORD_PTR imageBase = nt->OptionalHeader.ImageBase;
    DWORD_PTR delta = (DWORD_PTR)base - imageBase;
    logf("patch\texe 基址 0x%p（声明 0x%p，偏移 %+Id）\n",
         (void*)base, (void*)imageBase, (ptrdiff_t)delta);

    int bad = 0;
    for (const CodePatch& p : kPatches) {
        BYTE* addr = base + (p.va - (DWORD)imageBase) ;
        DWORD old;
        if (!VirtualProtect(addr, 1, PAGE_EXECUTE_READWRITE, &old)) {
            logf("patch\t%-14s 0x%X 无法改写内存（err=%lu）\n", p.what, p.va, GetLastError());
            ++bad;
            continue;
        }
        BYTE cur = *addr;
        if (cur == p.to) {
            logf("patch\t%-14s 0x%X 已是 0x%02X，跳过\n", p.what, p.va, cur);
        } else if (cur == p.from) {
            *addr = p.to;
            logf("patch\t%-14s 0x%X 0x%02X -> 0x%02X  OK\n", p.what, p.va, p.from, p.to);
        } else {
            logf("patch\t%-14s 0x%X 原字节是 0x%02X，期望 0x%02X —— 版本不符，未改动\n",
                 p.what, p.va, cur, p.from);
            ++bad;
        }
        VirtualProtect(addr, 1, old, &old);
        FlushInstructionCache(GetCurrentProcess(), addr, 1);
    }
    return bad;
}

// 返回失败条数。和代码补丁一样带原字节校验：exe 版本不符就报错、不动手。
static int apply_string_patches()
{
    HMODULE exe = GetModuleHandleW(NULL);
    BYTE* base = (BYTE*)exe;
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) { logf("strpatch\tDOS 头无效\n"); return 1; }
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)(base + dos->e_lfanew);
    DWORD_PTR imageBase = nt->OptionalHeader.ImageBase;

    int bad = 0;
    for (const StrPatch& p : kStrPatches) {
        BYTE* addr = base + (p.va - (DWORD)imageBase);

        if (p.repl_len + 1 > p.slot) {
            logf("strpatch\t%-14s 替换串放不进槽位（%zu > %zu），未改动\n",
                 p.what, p.repl_len + 1, p.slot);
            ++bad;
            continue;
        }
        if (memcmp(addr, p.repl, p.repl_len) == 0 && addr[p.repl_len] == 0) {
            logf("strpatch\t%-14s 0x%X 已是目标串，跳过\n", p.what, (unsigned)p.va);
            continue;
        }
        if (memcmp(addr, p.expect, p.expect_len) != 0) {
            logf("strpatch\t%-14s 0x%X 原字节不符（期望 %zu 字节 SJIS）—— 版本不符，未改动\n",
                 p.what, (unsigned)p.va, p.expect_len);
            ++bad;
            continue;
        }

        DWORD old;
        if (!VirtualProtect(addr, p.slot, PAGE_READWRITE, &old)) {
            logf("strpatch\t%-14s 0x%X 无法改写内存（err=%lu）\n", p.what, (unsigned)p.va, GetLastError());
            ++bad;
            continue;
        }
        memset(addr, 0, p.slot);
        memcpy(addr, p.repl, p.repl_len);
        VirtualProtect(addr, p.slot, old, &old);
        logf("strpatch\t%-14s 0x%X SJIS -> GBK 黑体  OK\n", p.what, (unsigned)p.va);
    }
    return bad;
}

// ─────────────── 探头：窗口标题（只记录，不改） ───────────────
//
// 窗口标题乱码是「SJIS 字节被 Windows 按系统码页(GBK)解释」造成的，改 start.ps3 里的
// 字节可以修 —— 但标题可能由多段拼成（实测改完 start.ps3 后仍剩一段乱码），
// 所以这里把游戏实际交给 USER32 的原始字节抓下来，别再靠猜。
static void log_bytes(const char* tag, HWND hwnd, LPCSTR s)
{
    if (!s) { logf("title\t%s hwnd=%p (null)\n", tag, (void*)hwnd); return; }

    char hex[3 * 64 + 1];
    int n = 0;
    for (int i = 0; s[i] && i < 64; ++i)
        n += sprintf_s(hex + n, sizeof(hex) - n, "%02X ", (unsigned char)s[i]);
    if (n > 0) hex[n - 1] = 0; else hex[0] = 0;

    // 借用系统的转换做展示：同一串按 GBK 和按 SJIS 各解一遍，
    // 一眼就能看出它原本是哪一种编码
    char gbk[192] = { 0 }, sjis[192] = { 0 };
    {
        int wlen = MultiByteToWideChar(936, 0, s, -1, NULL, 0);
        if (wlen > 0 && wlen < 96) {
            wchar_t w[96];
            MultiByteToWideChar(936, 0, s, -1, w, 96);
            WideCharToMultiByte(CP_UTF8, 0, w, -1, gbk, sizeof(gbk), NULL, NULL);
        }
    }
    {
        int wlen = MultiByteToWideChar(932, 0, s, -1, NULL, 0);
        if (wlen > 0 && wlen < 96) {
            wchar_t w[96];
            MultiByteToWideChar(932, 0, s, -1, w, 96);
            WideCharToMultiByte(CP_UTF8, 0, w, -1, sjis, sizeof(sjis), NULL, NULL);
        }
    }
    logf("title\t%s hwnd=%p\n\t\t字节= %s\n\t\t当GBK=%s\n\t\t当SJIS=%s\n",
         tag, (void*)hwnd, hex, gbk, sjis);
}

// 标题里混着一个 SJIS 的全角空格（0x81 0x40）—— 引擎拼标题时加的
// （`标题` + `　` + `章节名`，日志实测；那两字节既不在 start.ps3 里，也不是 exe 里的
// 字符串常量，是运行时拼进去的，来源没找到，但不影响修）。
// Windows 按 GBK 解它就成一个乱码字。就地换成 GBK 的全角空格 0xA1 0xA1，等长替换。
//
// 这是 §3.3 那个坑的第二次现身：SJIS 的 　 是 81 40，GBK 的是 A1 A1。
//
// 用调用方的局部栈缓冲：real_* 都是同步调用，返回前用完即弃，不用加锁。
static LPCSTR fix_fullwidth_space(LPCSTR s, char* buf, size_t cap)
{
    if (!s) return s;
    size_t len = strlen(s);
    if (len + 1 > cap) return s;              // 太长就原样放行

    bool hit = false;
    for (size_t i = 0; i + 1 < len; ++i)
        if ((BYTE)s[i] == 0x81 && (BYTE)s[i + 1] == 0x40) { hit = true; break; }
    if (!hit) return s;

    memcpy(buf, s, len + 1);
    for (size_t i = 0; i + 1 < len; ++i)
        if ((BYTE)buf[i] == 0x81 && (BYTE)buf[i + 1] == 0x40) {
            buf[i] = (char)0xA1; buf[i + 1] = (char)0xA1;
        }
    return buf;
}

static HWND WINAPI my_CreateWindowExA(DWORD exStyle, LPCSTR cls, LPCSTR name, DWORD style,
                                      int x, int y, int w, int h,
                                      HWND parent, HMENU menu, HINSTANCE inst, LPVOID param)
{
    LONG n = InterlockedIncrement(&g_title_calls);
    if (n <= 32) log_bytes("CreateWindowExA", NULL, name);
    // 窗口名同样过一遍（窗口标题的另一种给法）
    char buf[1024];
    LPCSTR use = g_enable_title ? fix_fullwidth_space(name, buf, sizeof(buf)) : name;
    return real_CreateWindowExA(exStyle, cls, use, style, x, y, w, h,
                                parent, menu, inst, param);
}

// ────────────── 补丁 6：启动设置界面的汉化 ──────────────
//
// 界面文字全在 exe 的 PE 资源里，而且是 **DLGTEMPLATEEX**（扩展模板），
// 所以模板里的字符串一定是 UTF-16。游戏却用 DialogBoxParamA 去建对话框 ——
// 系统把 Unicode 模板转成系统码页(GBK)时，**半角片假名(FF61-FF9F)不在 GBK 里**，
// 就丢成了 '?'（截图里那行 `??????比固定??????の補間設定` 就是这么来的；
// 译文原文是 `ｱｽﾍﾟｸﾄ比固定ﾌﾙｽｸﾘｰﾝの補間設定`，半角写法的 アスペクト/フルスクリーン）。
//
// 做法：
//   [用 W 版建] hook DialogBoxParamA → 转调 DialogBoxParamW。模板本来就是 Unicode，
//       于是不再经过 GBK，半角片假名也不会丢。
//   [包一层]   自己写 DlgProc，先交给游戏原版处理，再按表把控件文字换成中文。
//       挂在 WM_INITDIALOG / WM_COMMAND 之后（后者是因为有些文字是运行时才填的，
//       比如单选钮上的分辨率）。
//   [修编码]   hook SetWindowTextA / SetDlgItemTextA / SendMessageA(WM_SETTEXT)：
//       游戏传进来的这些是 **SJIS 字节**（日志实测，例如标题 `起動時の設定`），
//       按 CP932 解出来查表 → 命中就用译文、调 W 版设置。
//
// 译文放**外部文件**，改词不用重编 DLL：日志同目录的 `cnpatch_ui.txt`（UTF-8，
// 一行「原文<TAB>译文」，`#` 开头是注释）。找不到这个文件就整块不生效。
//
// ⚠ 别去翻单选钮上的分辨率文字（`1024 x 576` 那些）：游戏可能拿它当数据用。
//   目前只处理「原文能在表里查到」的控件文字。

static const int UI_MAX = 512;

struct UiEntry { wchar_t* jp; wchar_t* zh; };

static UiEntry    g_ui[UI_MAX];
static int        g_ui_count;

// 片段替换（表里以 ~ 开头的行）：整条文字里任意位置命中就换。
// 用于「整条会变但里面有一块固定日文」的情况 —— 典型就是分辨率单选钮上的
// `1920 x 1080[推奨]`：分辨率跟着 cmvs.cfg 走，写死整条不牢靠，只换 `[推奨]` 才稳。
static UiEntry    g_uisub[UI_MAX];
static int        g_uisub_count;
static BOOL       g_enable_ui = TRUE;
static wchar_t    g_ui_path[MAX_PATH];
static volatile LONG g_dlg_calls;
static volatile LONG g_ui_hits;

// 表里查一下。输入是宽字符（对话框模板本来就是 Unicode），返回译文或 NULL。
static const wchar_t* ui_lookup(const wchar_t* s)
{
    if (!s || !*s) return NULL;
    for (int i = 0; i < g_ui_count; ++i)
        if (wcscmp(g_ui[i].jp, s) == 0) return g_ui[i].zh;
    return NULL;
}

// 用 SJIS 解一遍再查表：游戏交给 *_A 的字节是 SJIS。
// 命中才返回译文；**没命中一律原样放行** —— 主窗口标题是「GBK + 一个 SJIS 全角空格」
// 的混编串，不能一刀切按 SJIS 解，那样会把 GBK 那段毁掉。
static const wchar_t* ui_sub(const wchar_t* s, wchar_t* out, size_t cch);

// 查表：先整条、再片段。命中返回译文/替换后的串，没命中返回 NULL（调用方原样放行）。
static const wchar_t* ui_resolve_w(const wchar_t* s, wchar_t* obuf, size_t occh)
{
    if (!s || !*s) return NULL;
    const wchar_t* zh = ui_lookup(s);
    return zh ? zh : ui_sub(s, obuf, occh);
}

// 同上，但输入是游戏交来的 ANSI 字节 —— 那些是 **SJIS**，先按 CP932 解出来再查。
// 没命中一律原样放行：主窗口标题是「GBK + 一个 SJIS 全角空格」的混编串，
// 一刀切按 SJIS 解会把 GBK 那段毁掉。
static const wchar_t* ui_resolve_ansi(LPCSTR s, wchar_t* wbuf, size_t wcch,
                                      wchar_t* obuf, size_t occh)
{
    if (!s || !*s) return NULL;
    if (MultiByteToWideChar(932, 0, s, -1, wbuf, (int)wcch) <= 0) return NULL;
    return ui_resolve_w(wbuf, obuf, occh);
}

// 片段替换：命中就返回替换后的串（写进 out），没命中返回 NULL。
static const wchar_t* ui_sub(const wchar_t* s, wchar_t* out, size_t cch)
{
    if (!s || !*s || !g_uisub_count) return NULL;
    if (wcsncpy_s(out, cch, s, _TRUNCATE) != 0) return NULL;

    bool hit = false;
    for (int i = 0; i < g_uisub_count; ++i) {
        const size_t n = wcslen(g_uisub[i].jp);
        const size_t m = wcslen(g_uisub[i].zh);
        if (!n) continue;
        wchar_t* p;
        while ((p = wcsstr(out, g_uisub[i].jp)) != NULL) {
            if (wcslen(out) - n + m + 1 > cch) break;
            memmove(p + m, p + n, (wcslen(p + n) + 1) * sizeof(wchar_t));
            memcpy(p, g_uisub[i].zh, m * sizeof(wchar_t));
            hit = true;
        }
    }
    return hit ? out : NULL;
}

// ── 私有加载随包字体 ──
//
// 玩家系统不一定装了这些字体。用 FR_PRIVATE 从 DLL 同目录加载，只对当前进程可见，
// 不污染系统字体目录；加载后 EnumFontFamiliesExA 就能枚举到，「字体选择」里才会出现。
// 找不到文件不算错（可选字体），记一行日志跳过。
static void load_bundled_fonts(HMODULE self)
{
    wchar_t dir[MAX_PATH];
    DWORD n = GetModuleFileNameW(self, dir, MAX_PATH);
    if (!n || n >= MAX_PATH) return;
    wchar_t* p = wcsrchr(dir, L'\\');
    if (!p) return;
    *(p + 1) = 0;

    static const wchar_t* const kFiles[] = { L"TW-Kai-98_1.ttf" };  // 全字库正楷体
    for (const wchar_t* f : kFiles) {
        wchar_t path[MAX_PATH];
        lstrcpynW(path, dir, MAX_PATH);
        wcsncat_s(path, MAX_PATH, f, _TRUNCATE);

        int added = AddFontResourceExW(path, FR_PRIVATE, 0);
        if (added > 0)
            logf("font\tself\t随包字体 %ls 已私有加载（%d 个 face）\n", f, added);
        else
            logf("font\tself\t随包字体 %ls 没找到或加载失败（err=%lu），跳过\n", f, GetLastError());
    }
}

// ── 读译文表 ──
static void load_ui_table(HMODULE self)
{
    wchar_t path[MAX_PATH];
    DWORD n = GetModuleFileNameW(self, path, MAX_PATH);
    if (!n || n >= MAX_PATH) return;
    wchar_t* p = wcsrchr(path, L'\\');
    if (!p) return;
    *(p + 1) = 0;
    lstrcpynW(g_ui_path, path, MAX_PATH);
    wcsncat_s(g_ui_path, MAX_PATH, L"cnpatch_ui.txt", _TRUNCATE);

    HANDLE h = CreateFileW(g_ui_path, GENERIC_READ, FILE_SHARE_READ, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        logf("ui\t没有译文表 %ls —— 界面汉化整体不生效\n", g_ui_path);
        return;
    }
    DWORD size = GetFileSize(h, NULL);
    if (size == 0 || size > 1 << 20) { CloseHandle(h); return; }

    char* raw = (char*)HeapAlloc(GetProcessHeap(), 0, size + 1);
    DWORD got = 0;
    if (raw) ReadFile(h, raw, size, &got, NULL);
    CloseHandle(h);
    if (!raw) return;
    raw[got] = 0;

    int need = MultiByteToWideChar(CP_UTF8, 0, raw, -1, NULL, 0);
    wchar_t* text = need > 0 ? (wchar_t*)HeapAlloc(GetProcessHeap(), 0, need * 2) : NULL;
    if (text) MultiByteToWideChar(CP_UTF8, 0, raw, -1, text, need);
    HeapFree(GetProcessHeap(), 0, raw);
    if (!text) return;

    // 去掉 UTF-8 BOM 转出来的那个 U+FEFF
    wchar_t* s = text;
    if (*s == 0xFEFF) ++s;

    for (wchar_t* line = s; *line; ) {
        wchar_t* nl = wcschr(line, L'\n');
        if (nl) *nl = 0;
        wchar_t* r = line; while (*r == L' ' || *r == L'\t' || *r == L'\r') ++r;
        if (*r && *r != L'#' && g_ui_count < UI_MAX) {
            wchar_t* tab = wcschr(r, L'\t');
            if (tab) {
                *tab = 0;
                wchar_t* k = r;
                wchar_t* v = tab + 1;
                while (*v == L' ' || *v == L'\t') ++v;
                wchar_t* ke = k + wcslen(k);
                while (ke > k && (ke[-1] == L' ' || ke[-1] == L'\r')) *--ke = 0;
                wchar_t* ve = v + wcslen(v);
                while (ve > v && (ve[-1] == L' ' || ve[-1] == L'\r')) *--ve = 0;
                if (*k && *v) {
                    UiEntry* arr = g_ui;
                    int* cnt = &g_ui_count;
                    if (*k == L'~') { arr = g_uisub; cnt = &g_uisub_count; ++k; }  // 片段替换
                    if (*cnt < UI_MAX && *k) {
                        wchar_t* a = _wcsdup(k);
                        wchar_t* b = _wcsdup(v);
                        if (a && b) { arr[*cnt].jp = a; arr[*cnt].zh = b; ++*cnt; }
                        else { if (a) free(a); if (b) free(b); }
                    }
                }
            }
        }
        if (!nl) break;
        line = nl + 1;
    }
    HeapFree(GetProcessHeap(), 0, text);
    logf("ui\t译文表 %ls：整条 %d 条，片段 %d 条\n",
         g_ui_path, g_ui_count, g_uisub_count);
}

// ── 对话框字体：把模板自带的日文字体换成中文字体 ──
//
// 只换**字名**，高度/粗细/斜体照抄源字体的 —— 所以每个控件原来的字号保持不变，
// 控件位置是模板算好的像素值，不会因为换字体而挪动。
//
// 为什么要换见 g_enable_uifont 那儿的注释：不换的话，JIS 里没有的简体字
// （复、设、语…）会被 GDI 拿去别的字体借字形，同一个词里混两种字形。
//
// 返回 NULL ＝ 不用动（源字体已经是目标字体，或拿不到 LOGFONT）。
static HFONT ui_font_for(HFONT src, BOOL is_dialog)
{
    LOGFONTW lf;
    if (!src || !GetObjectW(src, sizeof(lf), &lf)) {
        // 对话框**窗口自己**经常走到这儿：标准模板(DLGTEMPLATE) 的对话框，
        // 模板字体只发给了子控件，窗口自己的 WM_GETFONT 返回 0（实测 DIALOG 132）。
        // 这种情况拿默认界面字体当底 —— 高度/粗细和模板字体一致（都是 9pt / -12），
        // 只改字名，所以标题栏高度不会变。
        //
        // 只对**对话框自己**这么兜底：子控件要是也没有字体，说明它本意就是跟随
        // 系统绘制，凭空塞一个字体进去反而改变外观。
        if (!is_dialog || !GetObjectW(GetStockObject(DEFAULT_GUI_FONT), sizeof(lf), &lf))
            return NULL;
    }
    if (_wcsicmp(lf.lfFaceName, g_uifont) == 0) return NULL;   // 已经是中文字体了

    for (int i = 0; i < g_uifonts_n; ++i) {
        const LOGFONTW& k = g_uifonts[i].src;
        if (k.lfHeight == lf.lfHeight && k.lfWeight == lf.lfWeight &&
            k.lfItalic == lf.lfItalic && wcscmp(k.lfFaceName, lf.lfFaceName) == 0)
            return g_uifonts[i].h;
    }

    LOGFONTW key = lf;                       // 缓存键 = 源字体
    lf.lfCharSet = 134;                      // GB2312 —— 和正文那一处一致
    wcscpy_s(lf.lfFaceName, LF_FACESIZE, g_uifont);
    HFONT h = CreateFontIndirectW(&lf);
    if (!h) return NULL;

    if (g_uifonts_n < (int)(sizeof(g_uifonts) / sizeof(g_uifonts[0]))) {
        g_uifonts[g_uifonts_n].src = key;
        g_uifonts[g_uifonts_n].h   = h;
        ++g_uifonts_n;
    }
    // 注意：这儿必须转成 ANSI 用 %s 打。日志是窄字符流，
    // 用 %ls 打「ＭＳ Ｐゴシック」这种非 ASCII 宽串，转不出来会**整行丢掉**
    // （不报错、不输出），查起来极其费劲。
    char srcface[64], dstface[64];
    WideCharToMultiByte(CP_ACP, 0, key.lfFaceName, -1, srcface, 64, NULL, NULL);
    WideCharToMultiByte(CP_ACP, 0, g_uifont, -1, dstface, 64, NULL, NULL);
    if (InterlockedIncrement(&g_uifont_calls) <= 24)
        logf("uifont\t源=%s 高=%ld 粗细=%ld -> %s\n",
             srcface, key.lfHeight, key.lfWeight, dstface);
    return h;
}

static void ui_fix_font(HWND w, BOOL is_dialog)
{
    if (!g_enable_uifont) return;
    HFONT src = (HFONT)SendMessageW(w, WM_GETFONT, 0, 0);
    HFONT zh = ui_font_for(src, is_dialog);
    if (zh) SendMessageW(w, WM_SETFONT, (WPARAM)zh, TRUE);   // TRUE = 立刻重画
}

// ── 对话框：枚举控件，按表换文字 ──
static BOOL CALLBACK ui_enum_child(HWND child, LPARAM)
{
    ui_fix_font(child, FALSE);

    wchar_t buf[512], out[512];
    if (GetWindowTextW(child, buf, 512) <= 0 || !buf[0]) return TRUE;
    const wchar_t* zh = ui_resolve_w(buf, out, 512);
    if (zh) {
        SetWindowTextW(child, zh);
        InterlockedIncrement(&g_ui_hits);
    }
    return TRUE;
}

static void ui_translate_dialog(HWND hwnd)
{
    if (!g_enable_ui) return;                 // 对照跑时要连日文字体一起保持原样
    ui_fix_font(hwnd, TRUE);
    if (!g_ui_count && !g_uisub_count) return;
    wchar_t buf[512], out[512];
    if (GetWindowTextW(hwnd, buf, 512) > 0 && buf[0]) {
        const wchar_t* zh = ui_resolve_w(buf, out, 512);
        if (zh) { SetWindowTextW(hwnd, zh); InterlockedIncrement(&g_ui_hits); }
    }
    EnumChildWindows(hwnd, ui_enum_child, 0);
}

struct DlgCtx { DLGPROC user; LPARAM param; };

static INT_PTR CALLBACK ui_dlg_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    DlgCtx* ctx;
    if (msg == WM_INITDIALOG) {
        ctx = (DlgCtx*)lp;
        SetWindowLongPtrW(hwnd, DWLP_USER, (LONG_PTR)ctx);
    } else {
        ctx = (DlgCtx*)GetWindowLongPtrW(hwnd, DWLP_USER);
    }

    INT_PTR r = (ctx && ctx->user) ? ctx->user(hwnd, msg, wp, lp) : FALSE;

    // 先让游戏自己把文字填完，再翻译 —— 有些文字是运行时才设的（分辨率单选钮）
    if (msg == WM_INITDIALOG || msg == WM_COMMAND)
        ui_translate_dialog(hwnd);
    return r;
}

static INT_PTR WINAPI my_DialogBoxParamA(HINSTANCE inst, LPCSTR tpl, HWND parent,
                                         DLGPROC proc, LPARAM param)
{
    LONG n = InterlockedIncrement(&g_dlg_calls);
    if (n <= 16) logf("dlg\tDialogBoxParamA 模板=%p\n", (const void*)tpl);

    // 模板不是资源名（IS_INTRESOURCE 为假 = 是内存里现搭的模板）就原样走 A 版：
    // 那种模板多半是按 ANSI 搭的，交给 W 版会被当 UTF-16 读，反而更糟
    if (!g_enable_ui || !real_DialogBoxParamW || !IS_INTRESOURCE(tpl)) {
        if (real_DialogBoxParamA)
            return real_DialogBoxParamA(inst, tpl, parent, proc, param);
        return -1;
    }

    // 资源名可能是序号（MAKEINTRESOURCE）也可以是字符串，字符串要转宽
    wchar_t namebuf[256];
    LPCWSTR wname = (LPCWSTR)tpl;          // 序号：值本身两边通用
    if (!IS_INTRESOURCE(tpl)) {
        if (MultiByteToWideChar(CP_ACP, 0, tpl, -1, namebuf, 256) <= 0)
            return real_DialogBoxParamA(inst, tpl, parent, proc, param);
        wname = namebuf;
    }

    DlgCtx ctx = { proc, param };
    return real_DialogBoxParamW(inst, wname, parent, ui_dlg_proc, (LPARAM)&ctx);
}

// ── 标题栏版本与汉化署名 ──
//
// 游戏名部分是 start.ps3 里的固定串（构建时 SJIS→GBK **等长**替换，17 / 15 字节），
// 塞不下版本号，所以在窗口标题落下去之前改。匹配到前缀就整体换掉，
// 后面「— 场景名 —」是引擎拼的，原样保留。
//
// 两个前缀在 GBK 下的字节不同（FD 版是「ハピメアFD」，本体是「ハピメア RE」），互不包含。
struct TitleRep { const char* from; const char* to; };

static const TitleRep kTitleReps[] = {
    // ハピメアFD RE.ver  ->  ハピメア FD RE.ver1.1 gemini-4-argon翻译
    { "\xA5\xCF\xA5\xD4\xA5\xE1\xA5\xA2" "\x46\x44\x20\x52\x45\x2E\x76\x65\x72",
      "\xA5\xCF\xA5\xD4\xA5\xE1\xA5\xA2\x20\x46\x44\x20\x52\x45\x2E\x76\x65\x72"
      "\x31\x2E\x31\x20\x67\x65\x6D\x69\x6E\x69\x2D\x34\x2D\x61\x72\x67\x6F\x6E\xB7\xAD\xD2\xEB" },
    // ハピメア RE.ver    ->  ハピメア RE.ver1.1 gemini-4-argon翻译
    { "\xA5\xCF\xA5\xD4\xA5\xE1\xA5\xA2" "\x20\x52\x45\x2E\x76\x65\x72",
      "\xA5\xCF\xA5\xD4\xA5\xE1\xA5\xA2\x20\x52\x45\x2E\x76\x65\x72"
      "\x31\x2E\x31\x20\x67\x65\x6D\x69\x6E\x69\x2D\x34\x2D\x61\x72\x67\x6F\x6E\xB7\xAD\xD2\xEB" },
};

static LPCSTR apply_title_brand(LPCSTR text, char* out, size_t cap)
{
    if (!text) return text;
    for (const TitleRep& r : kTitleReps) {
        const char* p = strstr(text, r.from);
        if (!p) continue;
        size_t pre = (size_t)(p - text);
        const char* rest = p + strlen(r.from);
        if (pre + strlen(r.to) + strlen(rest) + 1 > cap) continue;
        memcpy(out, text, pre);
        lstrcpyA(out + pre, r.to);
        lstrcatA(out, rest);
        return out;
    }
    return text;
}

static BOOL WINAPI my_SetWindowTextA(HWND hwnd, LPCSTR text)
{
    LONG n = InterlockedIncrement(&g_title_calls);
    if (n <= 32) log_bytes("SetWindowTextA", hwnd, text);

    // 先查表：游戏给的 SJIS 串（标题 `起動時の設定` 就是）能直接换成中文
    wchar_t wbuf[512], obuf[512];
    if (g_enable_ui) {
        const wchar_t* zh = ui_resolve_ansi(text, wbuf, 512, obuf, 512);
        if (zh) {
            InterlockedIncrement(&g_ui_hits);
            if (n <= 32) logf("title\t-> 查表命中，改成中文\n");
            return real_SetWindowTextW ? real_SetWindowTextW(hwnd, zh)
                                       : real_SetWindowTextA(hwnd, text);
        }
    }

    char buf[1024];
    LPCSTR use = g_enable_title ? fix_fullwidth_space(text, buf, sizeof(buf)) : text;
    if (use != text && n <= 32) logf("title\t-> 全角空格 0x81 0x40 换成 0xA1 0xA1\n");

    // 版本号 / 汉化署名（会变长，所以放在最后一步）
    char tbuf[1024];
    LPCSTR branded = apply_title_brand(use, tbuf, sizeof(tbuf));
    if (branded != use) {
        if (n <= 32) logf("title\t-> 加版本与署名\n");
        use = branded;
    }
    return real_SetWindowTextA(hwnd, use);
}

// ── 菜单 ──
//
// 菜单不走 DialogBoxParamA，得单独接：`LoadMenuA` 载入资源菜单（就是 MENU 130，
// 右键菜单），然后**递归**把每一层的文字按表换掉 —— 子菜单要用 GetSubMenu 走下去。
//
// 菜单项的原文实测：顶层 `LOAD(&L)`、`ﾃﾞｰﾀ復元(&F)`、`画面設定(&G)`…（见
// test/uiprobe/parse_menu.py）。`&` 是加速键标记，Windows 会把它吃掉、给后面的
// 字符加下划线，所以译文里**必须原样保留一个 `&`**。
static void ui_translate_menu(HMENU m)
{
    if (!m || !g_enable_ui) return;
    int n = GetMenuItemCount(m);
    if (n <= 0) return;

    for (int i = 0; i < n; ++i) {
        wchar_t buf[256], out[256];
        MENUITEMINFOW mii;
        ZeroMemory(&mii, sizeof(mii));
        mii.cbSize = sizeof(mii);
        mii.fMask  = MIIM_STRING;
        mii.dwTypeData = buf;
        mii.cch = 256;

        if (GetMenuItemInfoW(m, i, TRUE, &mii) && buf[0]) {
            const wchar_t* zh = ui_resolve_w(buf, out, 256);
            if (zh) {
                MENUITEMINFOW set;
                ZeroMemory(&set, sizeof(set));
                set.cbSize = sizeof(set);
                set.fMask  = MIIM_STRING;
                set.dwTypeData = (LPWSTR)zh;
                set.cch = (UINT)wcslen(zh);
                if (SetMenuItemInfoW(m, i, TRUE, &set))
                    InterlockedIncrement(&g_ui_hits);
            }
        }
        HMENU sub = GetSubMenu(m, i);
        if (sub) ui_translate_menu(sub);
    }
}

static HMENU WINAPI my_LoadMenuA(HINSTANCE inst, LPCSTR name)
{
    HMENU m = real_LoadMenuA ? real_LoadMenuA(inst, name) : NULL;
    if (m && g_enable_ui && IS_INTRESOURCE(name)) {
        logf("menu\tLoadMenuA 资源 %u -> 按表翻译\n", (unsigned)(UINT_PTR)name);
        ui_translate_menu(m);
    }
    return m;
}

// 存档槽位名、画面设置里的分辨率…这些是游戏**运行时**用 SetMenuItemInfoA 填的
// （SJIS 字节），表里查不到，所以这里**至少按 SJIS 解对**，别让它继续当 GBK 显示。
//
// ⚠ 两个坑叠在一起，都在这里踩过：
//   1. 两种「带字符串」的标志都要认：
//        MIIM_STRING (0x40)   —— 新写法
//        MIIM_TYPE   (0x10)   —— 老写法，这个游戏用的就是它
//   2. **`MF_STRING` 的值是 `0`**！所以绝不能写 `fType & MF_STRING`（恒为假），
//      那会把「带文字的 MIIM_TYPE 调用」全判成「没有文字」。日志里就长这样：
//        SetMenuItemInfoA 无文字（fMask=0x10 fType=0x0）   ← 其实它是带文字的
//      正确判法是「不是那几种非文字类型」。
static BOOL WINAPI my_SetMenuItemInfoA(HMENU menu, UINT item, BOOL bypos, LPCMENUITEMINFOA a)
{
    if (!g_enable_ui || !real_SetMenuItemInfoW || !a || !a->dwTypeData)
        return real_SetMenuItemInfoA(menu, item, bypos, a);

    const BOOL viaType = (a->fMask & MIIM_TYPE) &&
                         !(a->fType & (MF_BITMAP | MF_OWNERDRAW | MF_SEPARATOR));
    if (!(a->fMask & MIIM_STRING) && !viaType) {
        if (InterlockedIncrement(&g_dlg_calls) <= 16)
            logf("menu\tSetMenuItemInfoA 无文字（fMask=0x%X fType=0x%X）\n", a->fMask, a->fType);
        return real_SetMenuItemInfoA(menu, item, bypos, a);
    }

    // ⚠ 查表没命中就**原样放行**，绝不能「兜底按 SJIS 解」。
    //
    // 这里踩过一次：这些字符串是**混编**的 —— 存档槽位那条是
    //     000 : 2026-10-06 12:03:32 - D0F2D5C2 -
    // 前半截是游戏的 ASCII/SJIS，末尾的章节名却是**我们译文的 GBK**（D0F2D5C2 = 序章，
    // 从脚本里读出来的）。一刀切按 SJIS 解，就把本来正确的 GBK 那段毁成了半角片假名。
    //
    // 兜底只在**匹配**的意义上需要：`未定義` 那条游戏自己的字面量是 SJIS，得先按 SJIS
    // 解出来才查得到表。所以 —— 解码只用来查表，查不到就用原始字节交给 Windows。
    wchar_t wbuf[512], obuf[512];
    const wchar_t* zh = ui_resolve_ansi(a->dwTypeData, wbuf, 512, obuf, 512);
    if (!zh)
        return real_SetMenuItemInfoA(menu, item, bypos, a);

    MENUITEMINFOW w;
    ZeroMemory(&w, sizeof(w));
    w.cbSize        = sizeof(w);
    // 把老写法归一成新写法再交给 W 版：MIIM_TYPE 同时管「类型」和「文字」，
    // 拆成 MIIM_FTYPE + MIIM_STRING 语义等价
    w.fMask         = (a->fMask & ~MIIM_TYPE) | MIIM_STRING | (viaType ? MIIM_FTYPE : 0);
    w.fType         = a->fType;
    w.fState        = a->fState;
    w.wID           = a->wID;
    w.hSubMenu      = a->hSubMenu;
    w.hbmpChecked   = a->hbmpChecked;
    w.hbmpUnchecked = a->hbmpUnchecked;
    w.dwItemData    = a->dwItemData;
    w.dwTypeData    = (LPWSTR)zh;
    w.cch           = (UINT)wcslen(zh);
    InterlockedIncrement(&g_ui_hits);
    return real_SetMenuItemInfoW(menu, item, bypos, &w);
}

static BOOL WINAPI my_SetDlgItemTextA(HWND hwnd, int id, LPCSTR text)
{
    LONG n = InterlockedIncrement(&g_title_calls);
    if (n <= 48) log_bytes("SetDlgItemTextA", hwnd, text);

    wchar_t wbuf[512], obuf[512];
    if (g_enable_ui && real_SetDlgItemTextW) {
        const wchar_t* zh = ui_resolve_ansi(text, wbuf, 512, obuf, 512);
        if (zh) {
            InterlockedIncrement(&g_ui_hits);
            return real_SetDlgItemTextW(hwnd, id, zh);
        }
    }
    return real_SetDlgItemTextA(hwnd, id, text);
}

static LRESULT WINAPI my_SendMessageA(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    if (g_enable_ui && msg == WM_SETTEXT && lp && real_SendMessageW) {
        LONG n = InterlockedIncrement(&g_title_calls);
        if (n <= 48) log_bytes("SendMessageA(WM_SETTEXT)", hwnd, (LPCSTR)lp);
        wchar_t wbuf[512], obuf[512];
        const wchar_t* zh = ui_resolve_ansi((LPCSTR)lp, wbuf, 512, obuf, 512);
        if (zh) {
            InterlockedIncrement(&g_ui_hits);
            return real_SendMessageW(hwnd, WM_SETTEXT, wp, (LPARAM)zh);
        }
    }
    return real_SendMessageA(hwnd, msg, wp, lp);
}

// MessageBoxA 是**另一条路**：exe 里有 21 个调用点，报错框走这条，
// 不走 DialogBoxParamA（那些 `パックファイルが破損しているので終了します。`
// 之类的 SJIS 字面量就是从这儿弹出来的）。正文和标题是分开的两个参数，
// 各自查表、命中才换；两个都没命中就原样走 A 版。
static int WINAPI my_MessageBoxA(HWND hwnd, LPCSTR text, LPCSTR caption, UINT type)
{
    if (g_enable_ui && real_MessageBoxW) {
        wchar_t tw[512], to[512], cw[512], co[512];
        const wchar_t* zt = ui_resolve_ansi(text, tw, 512, to, 512);
        const wchar_t* zc = ui_resolve_ansi(caption, cw, 512, co, 512);
        if (zt || zc) {
            // 只命中一边时，另一边必须把**原文**带过去 —— 传 NULL 会把原文吞掉
            if (!zt && text && MultiByteToWideChar(932, 0, text, -1, tw, 512) > 0) {
                log_bytes("MessageBoxA 正文", hwnd, text);
                zt = tw;
            }
            if (!zc && caption && MultiByteToWideChar(932, 0, caption, -1, cw, 512) > 0)
                zc = cw;
            InterlockedIncrement(&g_ui_hits);
            return real_MessageBoxW(hwnd, zt, zc, type);
        }
    }
    return real_MessageBoxA(hwnd, text, caption, type);
}

// ─────────── 探针：文件打开路径（只记录，不改行为） ───────────
//
// 用来查「引擎拿目录形式的封包路径时，到底想打开哪个文件」。
// 全量记录会淹掉日志（开机要开几千个文件），所以只记两类：
//   · 路径里带 chip / pack / image 的
//   · 打开失败的（失败才是关键线索）
static int file_wanted_a(const char* p)
{
    if (!p) return 0;
    for (const char* s = p; *s; ++s) {
        if (_strnicmp(s, "chip", 4) == 0) return 1;
        if (_strnicmp(s, "pack", 4) == 0) return 1;
        if (_strnicmp(s, "image", 5) == 0) return 1;
    }
    return 0;
}

static int file_wanted_w(const wchar_t* p)
{
    if (!p) return 0;
    for (const wchar_t* s = p; *s; ++s) {
        if (_wcsnicmp(s, L"chip", 4) == 0) return 1;
        if (_wcsnicmp(s, L"pack", 4) == 0) return 1;
        if (_wcsnicmp(s, L"image", 5) == 0) return 1;
    }
    return 0;
}

// 记住从 chip 路径开出来的句柄，ReadFile 时把实际读到的字节 dump 出来
static HANDLE          g_chip_files[16];
static volatile LONG   g_chip_files_n;

static void note_chip(HANDLE h, const char* name)
{
    if (h == INVALID_HANDLE_VALUE || !h || !name) return;
    if (!file_wanted_a(name)) return;
    LONG i = InterlockedIncrement(&g_chip_files_n) - 1;
    if (i < 16) g_chip_files[i] = h;
}

static int is_chip(HANDLE h)
{
    LONG n = g_chip_files_n;
    if (n > 16) n = 16;
    for (LONG i = 0; i < n; ++i)
        if (g_chip_files[i] == h) return 1;
    return 0;
}

static BOOL WINAPI my_ReadFile(HANDLE h, LPVOID buf, DWORD want, LPDWORD got, LPOVERLAPPED ov)
{
    BOOL r = real_ReadFile(h, buf, want, got, ov);
    if (is_chip(h)) {
        char hex[3 * 17] = { 0 };
        int n = 0;
        for (int i = 0; i < 16 && i < (int)want; ++i)
            n += sprintf_s(hex + n, sizeof(hex) - n, "%02X ", ((unsigned char*)buf)[i]);
        logf("read\tchip %p 请求=%lu 得到=%lu 前16字节=%s\n",
             (void*)h, want, (ov || !got) ? 0UL : *got, hex);
    }
    return r;
}

static HANDLE WINAPI my_CreateFileA(LPCSTR name, DWORD access, DWORD share,
                                    LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                    DWORD flags, HANDLE tpl)
{
    HANDLE h = real_CreateFileA(name, access, share, sa, disp, flags, tpl);
    DWORD err = GetLastError();
    note_chip(h, name);
    if (h == INVALID_HANDLE_VALUE || file_wanted_a(name)) {
        // 路径按「系统码页(GBK)」解出来给人看；引擎给的多半是 SJIS 字面量拼接的
        char u8[600] = { 0 };
        if (name) {
            int n = MultiByteToWideChar(936, 0, name, -1, NULL, 0);
            if (n > 0 && n < 200) {
                wchar_t w[200];
                MultiByteToWideChar(936, 0, name, -1, w, 200);
                WideCharToMultiByte(CP_UTF8, 0, w, -1, u8, sizeof(u8), NULL, NULL);
            }
        }
        logf("file\tA %s err=%lu  %s\n", h == INVALID_HANDLE_VALUE ? "FAIL" : "ok ",
             err, u8[0] ? u8 : (name ? name : "(null)"));
    }
    return h;
}

static HANDLE WINAPI my_CreateFileW(LPCWSTR name, DWORD access, DWORD share,
                                    LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                    DWORD flags, HANDLE tpl)
{
    HANDLE h = real_CreateFileW(name, access, share, sa, disp, flags, tpl);
    DWORD err = GetLastError();
    if (h == INVALID_HANDLE_VALUE || file_wanted_w(name)) {
        char u8[600] = { 0 };
        if (name) WideCharToMultiByte(CP_UTF8, 0, name, -1, u8, sizeof(u8), NULL, NULL);
        logf("file\tW %s err=%lu  %s\n", h == INVALID_HANDLE_VALUE ? "FAIL" : "ok ",
             err, u8[0] ? u8 : "(null)");
    }
    return h;
}

// ─────────────────────── 补丁 2：字体 ───────────────────────

// 决定这一次调用要不要换字体。返回动过手脚的 charset 和 face。
//
// 两种模式：
//   - 默认（安全）：只换 charset == 134 那一个调用点的**字体名**，charset 原样。
//     这一份就是正文用的（补丁 [2] 改的就是它的 charset），GDI 原本给它替换成
//     新宋体，现在换成 g_font。度量逐项相同，排版宽度不受影响。
//   - CMVS_FONTHOOK=1（实验）：4 个调用点全改，charset 也一律强制 134。
//     这会让另几个调用点的度量跟着变（MS Gothic 的 tmMaxCharWidth 是 79，不是 40），
//     排版宽度会算错 —— 是踩过的坑，别当默认用。
// 补丁 1b 把 exe 里的默认字体名改成了 GBK「黑体」。但正文的 charset 不稳定：
// 启动时走 134，只要在设置界面动过字体/粗体，之后正文重建就落到 charset 128 的
// 调用点上（2026-10-29 日志实测：切粗体 #7-#9，切回普通 #10-#12，全是 128）。
// 128 那套按 SJIS 解释 GBK 字节，正文立刻变成半角片假名乱码，退出重进才恢复。
//
// **发布版策略：玩家选什么字体都不影响实际渲染**（参照 Amatsutsumi 汉化组的做法）。
// 不能按「非 ASCII」筛：玩家能选到纯 ASCII 的英文字体（Arial 等），一选就回到
// charset 128 的乱码。
//
// **发布版策略（2026-10-29 定稿）**：给玩家几款经过验证的字体，其余一律回退黑体。
// 白名单里的字体必须同时满足：
//   1. 度量与黑体逐项相同（lfHeight=-40 下 tmHeight=40 / 全角步进 40 / 半角 20），
//      否则行高溢出、框宽算错 —— 见 test\hooklog\fontmetrics.exe 的实测表
//   2. 字形覆盖译文用字（3411 个字符），只缺 ♪ 没关系（♪ 由 note_dc 单独取）
// 实测通过：黑体 / 宋体 / 新宋体 / 仿宋 / 楷体 / 幼圆 / 隶书。
// 雅黑、等线、华文楷体/宋体的 tmHeight 是 52/41/44，会被回退成黑体。
//
// 不会误伤我们自己建的字体：
//   - ♪ 专用字体走 note_dc()，直接调 real_CreateFontIndirectA，绕过本 hook
//   - 对话框控件字体走 ui_font_for()，用 CreateFontIndirectW，也不经过这里
static const char* const kFontWhite[] = {
    "SimHei", "SimSun", "NSimSun", "FangSong", "KaiTi", "YouYuan", "LiSu",
    "TW-Kai",                               // 全字库正楷体（随包私有加载，见 load_bundled_fonts）
    "\xBA\xDA\xCC\xE5",                     // 黑体
    "\xCB\xCE\xCC\xE5",                     // 宋体
    "\xD0\xC2\xCB\xCE\xCC\xE5",             // 新宋体
    "\xB7\xC2\xCB\xCE",                     // 仿宋
    "\xBF\xAC\xCC\xE5",                     // 楷体
    "\xD3\xD7\xD4\xB2",                     // 幼圆
    "\xC1\xA5\xCA\xE9",                     // 隶书
};

static bool font_allowed(const char* face)
{
    if (!face || !*face) return false;
    for (const char* f : kFontWhite)
        if (_stricmp(face, f) == 0) return true;
    return false;
}

static void pick_font(DWORD& charset, LPCSTR& face, const char** why, int weight)
{
    (void)weight;   // 判据里用不到，留着参数是为了日志/以后排查方便
    if (g_enable_font) {
        charset = kGB2312_CHARSET;
        face    = g_font;
        *why    = "全量hook";
    } else if (!g_enable_face) {
        *why = "";
    } else if (face && font_allowed(face)) {
        // 白名单字体：保留玩家选的字体名，只保证 charset 是 GB2312
        charset = kGB2312_CHARSET;
        *why    = "白名单字体";
    } else {
        // 其余一切（雅黑、Arial、空名…）回退黑体：不会乱码，也不会量错
        charset = kGB2312_CHARSET;
        face    = g_font;
        *why    = "固定黑体";
    }
}

static HFONT WINAPI my_CreateFontA(int cHeight, int cWidth, int cEscapement, int cOrientation,
                                   int cWeight, DWORD bItalic, DWORD bUnderline, DWORD bStrikeOut,
                                   DWORD iCharSet, DWORD iOutPrecision, DWORD iClipPrecision,
                                   DWORD iQuality, DWORD iPitchAndFamily, LPCSTR pszFaceName)
{
    LONG n = InterlockedIncrement(&g_font_calls);

    DWORD charset = iCharSet;
    LPCSTR face   = pszFaceName;
    const char* why = "";
    pick_font(charset, face, &why, cWeight);

    // 前 16 次 + 所有粗体请求都记：粗体是唯一会重建正文字体的操作，
    // 排查「切粗体后对话框乱码」时需要看到那一次调用的 charset（见 2026-10-29 记录）
    if (n <= 16 || cWeight >= 600) {
        logf("font\t#%ld h=%d w=%d charset=%lu quality=%lu weight=%d face=%s  -> charset=%lu face=%s%s\n",
             n, cHeight, cWidth, iCharSet, iQuality, cWeight,
             (pszFaceName && *pszFaceName) ? pszFaceName : "(default)",
             charset, face, *why ? " [换]" : "");
    } else if (strcmp(why, "固定黑体") == 0) {
        // 设置里动过字体/粗体后，正文重建会落到 charset 128 的调用点；记下被纠正的情况
        logf("font\t#%ld charset=%lu -> 134 SimHei（固定黑体）\n", n, iCharSet);
    }
    return real_CreateFontA(cHeight, cWidth, cEscapement, cOrientation, cWeight, bItalic,
                            bUnderline, bStrikeOut, charset, iOutPrecision, iClipPrecision,
                            iQuality, iPitchAndFamily, face);
}

static HFONT WINAPI my_CreateFontIndirectA(const LOGFONTA* lplf)
{
    if (!lplf) return real_CreateFontIndirectA(lplf);

    LOGFONTA lf = *lplf;
    LONG n = InterlockedIncrement(&g_font_calls);

    DWORD charset = lf.lfCharSet;
    LPCSTR face   = lf.lfFaceName;
    const char* why = "";
    pick_font(charset, face, &why, lf.lfWeight);

    if (n <= 16 || lf.lfWeight >= 600) {
        logf("fontI\t#%ld h=%d charset=%lu weight=%d face=%s  -> charset=%lu face=%s%s\n",
             n, lf.lfHeight, lf.lfCharSet, lf.lfWeight, lf.lfFaceName, charset, face,
             *why ? " [换]" : "");
    } else if (strcmp(why, "固定黑体") == 0) {
        logf("fontI\t#%ld charset=%lu -> 134 SimHei（固定黑体）\n", n, lf.lfCharSet);
    }
    if (*why) {
        lf.lfCharSet = (BYTE)charset;
        lstrcpynA(lf.lfFaceName, face, LF_FACESIZE);
    }
    return real_CreateFontIndirectA(&lf);
}

// ── 字体选择列表：只放白名单字体 ──
//
// 引擎「字体选择」弹出的列表是 EnumFontFamiliesExA 枚举系统字体得到的
// （exe 的导入表里只有这一个字体枚举函数）。包一层回调，名单外的字体直接跳过。
//
// 只在「枚举全部字体」时过滤：如果调用方在 lfFaceName 里指定了具体字体名
// （引擎拿它做存在性检查的场景），原样放行，别影响别的逻辑。
struct EnumCtx {
    FONTENUMPROCA user;
    LPARAM        lp;
    // 同一字体在 DEFAULT_CHARSET 全量枚举下会按不同字符集/字体类型重复回调
    // （实测每个字体出现两次），这里记账去重：同一个名字只放行第一次。
    char          seen[16][LF_FACESIZE];
    int           n;
};

static int CALLBACK enum_filter_proc(const LOGFONTA* plf, const TEXTMETRICA* ptm, DWORD type, LPARAM lp)
{
    EnumCtx* c = (EnumCtx*)lp;
    if (!font_allowed(plf->lfFaceName)) return 1;   // 1 = 继续枚举，跳过这个字体

    for (int i = 0; i < c->n; ++i)
        if (_stricmp(c->seen[i], plf->lfFaceName) == 0) return 1;   // 已放过，跳过重复

    if (c->n < (int)(sizeof(c->seen) / sizeof(c->seen[0])))
        lstrcpynA(c->seen[c->n++], plf->lfFaceName, LF_FACESIZE);
    logf("enum\t放行 %s\n", plf->lfFaceName);
    return c->user(plf, ptm, type, c->lp);
}

static int WINAPI my_EnumFontFamiliesExA(HDC hdc, LPLOGFONTA plf, FONTENUMPROCA proc, LPARAM lp, DWORD flags)
{
    if (!real_EnumFontFamiliesExA) return 0;

    // 查特定字体（名字非空）：引擎用它校验配置里保存的字体是否存在。
    // 它固定带 lfCharSet=128(SJIS)，仿宋/楷体/隶书/幼圆在 SJIS 下查不到，
    // 校验失败就会回退黑体 —— 表现为「重进游戏字体变回黑体」。
    // 这里和全量枚举一样改用 DEFAULT_CHARSET 再查一次，名字仍原样保留。
    if (plf && plf->lfFaceName[0]) {
        if (g_enable_face && plf->lfCharSet == 128) {
            LOGFONTA q = *plf;
            q.lfCharSet = DEFAULT_CHARSET;
            q.lfPitchAndFamily = 0;
            logf("enum\t查字体 %s charset=%d -> 改用 DEFAULT_CHARSET\n",
                 plf->lfFaceName, plf->lfCharSet);
            return real_EnumFontFamiliesExA(hdc, &q, proc, lp, flags);
        }
        return real_EnumFontFamiliesExA(hdc, plf, proc, lp, flags);
    }

    // 引擎枚举时带了字符集过滤（实测 lfCharSet=128/SJIS）：系统只返回「支持该字符集」
    // 的字体，黑体/仿宋/楷体这类 GB2312 字体压根不会出现，白名单也就无从放行。
    // 这里改成 DEFAULT_CHARSET 枚举全量，剩下的交给 enum_filter_proc 按白名单筛。
    LOGFONTA q = plf ? *plf : LOGFONTA{};
    logf("enum\t请求 charset=%d pitch=0x%02X flags=0x%X -> 改用 DEFAULT_CHARSET 全量枚举\n",
         q.lfCharSet, q.lfPitchAndFamily, flags);
    q.lfCharSet = DEFAULT_CHARSET;
    q.lfPitchAndFamily = 0;

    EnumCtx ctx{};
    ctx.user = proc;
    ctx.lp   = lp;
    ctx.n    = 0;
    return real_EnumFontFamiliesExA(hdc, &q, enum_filter_proc, (LPARAM)&ctx, flags);
}

// ♪ 的字形从哪儿取。
//
// 不能拿引擎当前那个字体去取 —— 黑体(SimHei)没有 ♪（它是 GB2312 字符集字体，
// 而 ♪ 不在 GB2312 里）。缺字时 GDI **不返回 GDI_ERROR**，而是给一个 .notdef
// 方块，所以「取到了」并不等于「字形是对的」—— 这里踩过一次，游戏里显示成豆腐块。
//
// 所以另开一个私有 DC，用**确定有 ♪ 的字体**去取（CMVS_NOTEFONT 可换）：
//   - 新宋体 NSimSun（默认）：GB18030 字体，♪ 齐全，37 宽
//   - MS Gothic：引擎原本的字体，♪ 在 JIS X 0208 里，全角 40 宽
//   - 宋体 SimSun 也行
//   注意 GB2312 那一档（黑体、仿宋…）没有 ♪，别选它们。
// 字号跟源 DC 的 LOGFONT 对齐，所以 ♪ 的大小和周围文字一致。
static HDC note_dc(HDC src)
{
    LOGFONTA lf; ZeroMemory(&lf, sizeof(lf));
    HGDIOBJ cur = GetCurrentObject(src, OBJ_FONT);
    if (!cur || GetObjectA(cur, sizeof(lf), &lf) != sizeof(lf)) return NULL;

    // lfHeight == 0 表示「用默认大小」，拿不到真实点数，改用 DC 的实测高度
    if (lf.lfHeight == 0) {
        TEXTMETRICA tm; ZeroMemory(&tm, sizeof(tm));
        if (GetTextMetricsA(src, &tm) && tm.tmHeight > 0) lf.lfHeight = -tm.tmHeight;
    }

    EnterCriticalSection(&g_cs);
    if (!g_note_dc || memcmp(&lf, &g_note_src_lf, sizeof(lf)) != 0) {
        LOGFONTA nf = lf;
        nf.lfCharSet = DEFAULT_CHARSET;          // 别带 GB2312，否则选不中 MS Gothic
        nf.lfPitchAndFamily = 0;
        lstrcpynA(nf.lfFaceName, g_notefont, LF_FACESIZE);

        HFONT f = real_CreateFontIndirectA(&nf);
        if (f) {
            if (g_note_font) DeleteObject(g_note_font);
            g_note_font = f;
            if (!g_note_dc) g_note_dc = CreateCompatibleDC(NULL);
            if (g_note_dc) SelectObject(g_note_dc, g_note_font);
            g_note_src_lf = lf;
        }
    }
    HDC dc = g_note_dc;
    LeaveCriticalSection(&g_cs);
    return dc;
}

// 顺带记录游戏问过的字形码（前 256 个），是验证补丁 1 是否生效的探头。
// 遇到 ♪ 哨兵就换成真正的 ♪，其余一律原样转发。
static DWORD WINAPI my_GetGlyphOutlineA(HDC hdc, UINT uChar, UINT uFormat, LPGLYPHMETRICS lpgm,
                                        DWORD cbBuffer, LPVOID lpvBuffer, const MAT2* lpmat2)
{
    LONG n = InterlockedIncrement(&g_glyph_calls);
    if (n <= 256) {
        logf("glyph\t#%ld 0x%04X hdc=%p\n", n, uChar, (void*)hdc);
    }

    if (g_enable_note && real_GetGlyphOutlineW &&
        (uChar == kNoteSentinel || uChar == kNoteSentinelSwap)) {
        // 用引擎自己的 DC 去要 ♪ 的字形：字体、字号、变换矩阵全是它的，
        // 所以拿回来的 GLYPHMETRICS 和别的字同尺度，排版不用另做处理。
        SetLastError(0);
        HDC ndc = note_dc(hdc);          // 优先私有字体（确定有 ♪）
        DWORD got = ndc ? real_GetGlyphOutlineW(ndc, kNoteChar, uFormat, lpgm, cbBuffer,
                                                lpvBuffer, lpmat2)
                        : GDI_ERROR;
        const char* src = "私有";
        if (got == GDI_ERROR) {
            // 私有字体建不出来才退回引擎当前那一份（它可能碰巧也有 ♪）
            src = "引擎";
            got = real_GetGlyphOutlineW(hdc, kNoteChar, uFormat, lpgm, cbBuffer,
                                        lpvBuffer, lpmat2);
        }
        if (got != GDI_ERROR) {
            LONG k = InterlockedIncrement(&g_note_hits);
            if (k <= 16) {
                long adv  = (uFormat == GGO_METRICS && lpgm) ? (long)lpgm->gmCellIncX : -1L;
                long boxx = lpgm ? (long)lpgm->gmBlackBoxX : -1L;
                // 把 DC 的身份也记下来：排查「同一个码位换来换去数字不一样」时，
                // 得先确认两次问的是不是同一个 DC、同一个字体
                char face[LF_FACESIZE] = { 0 };
                TEXTMETRICA tm; ZeroMemory(&tm, sizeof(tm));
                GetTextFaceA(hdc, LF_FACESIZE, face);
                GetTextMetricsA(hdc, &tm);
                logf("note\t#%ld 哨兵 0x%04X -> ♪ 步进=%ld 黑框宽=%ld 格式=%u 缓冲=%lu"
                     "  [%s字体 %s] 引擎DC字体=%s(%02X..%02X) h=%ld cs=%d\n",
                     k, uChar, adv, boxx, uFormat, cbBuffer, src, g_notefont,
                     face, (unsigned char)face[0], (unsigned char)face[1],
                     tm.tmHeight, (int)tm.tmCharSet);
            }
            return got;
        }
        // 取不到就退回原路：宁可少一个音符，也不能返回垃圾让引擎画出乱码
        logf("note\t哨兵 0x%04X 取 ♪ 字形失败（err=%lu），改走原路\n", uChar, GetLastError());
    }

    return real_GetGlyphOutlineA(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);
}

// ─────────────────────── IAT 改写 ───────────────────────

static void patch_iat(HMODULE mod, const char* dll, const char* func, void* newfn, void** oldfn)
{
    BYTE* base = (BYTE*)mod;
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return;

    DWORD imp_rva = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress;
    if (!imp_rva) return;

    for (PIMAGE_IMPORT_DESCRIPTOR imp = (PIMAGE_IMPORT_DESCRIPTOR)(base + imp_rva); imp->Name; ++imp) {
        if (_stricmp((const char*)(base + imp->Name), dll) != 0) continue;
        if (!imp->OriginalFirstThunk) continue;

        // 名字读 ILT（OriginalFirstThunk），槽位写 IAT（FirstThunk）
        PIMAGE_THUNK_DATA ilt = (PIMAGE_THUNK_DATA)(base + imp->OriginalFirstThunk);
        PIMAGE_THUNK_DATA iat = (PIMAGE_THUNK_DATA)(base + imp->FirstThunk);

        for (; ilt->u1.AddressOfData; ++ilt, ++iat) {
            if (ilt->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            PIMAGE_IMPORT_BY_NAME ibn = (PIMAGE_IMPORT_BY_NAME)(base + ilt->u1.AddressOfData);
            if (strcmp((const char*)ibn->Name, func) != 0) continue;

            DWORD old;
            if (VirtualProtect(&iat->u1.Function, sizeof(ULONG_PTR), PAGE_READWRITE, &old)) {
                if (oldfn && !*oldfn) *oldfn = (void*)iat->u1.Function;
                iat->u1.Function = (ULONG_PTR)newfn;
                VirtualProtect(&iat->u1.Function, sizeof(ULONG_PTR), old, &old);
            }
        }
    }
}

static void patch_all_modules()
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    if (snap == INVALID_HANDLE_VALUE) return;

    MODULEENTRY32W me = { sizeof(me) };
    if (Module32FirstW(snap, &me)) {
        do {
            // CreateFontA 现在无条件挂：钩子里自己决定这次要不要换字体
            // （见 pick_font）。多数调用是纯转发。
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "CreateFontA",
                      (void*)my_CreateFontA, (void**)&real_CreateFontA);
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "CreateFontIndirectA",
                      (void*)my_CreateFontIndirectA, (void**)&real_CreateFontIndirectA);
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "GetGlyphOutlineA",
                      (void*)my_GetGlyphOutlineA, (void**)&real_GetGlyphOutlineA);
            // 字体选择列表只显示白名单字体
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "EnumFontFamiliesExA",
                      (void*)my_EnumFontFamiliesExA, (void**)&real_EnumFontFamiliesExA);
            // 窗口标题
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "SetWindowTextA",
                      (void*)my_SetWindowTextA, (void**)&real_SetWindowTextA);
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "CreateWindowExA",
                      (void*)my_CreateWindowExA, (void**)&real_CreateWindowExA);
            // 界面汉化
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "DialogBoxParamA",
                      (void*)my_DialogBoxParamA, (void**)&real_DialogBoxParamA);
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "SetDlgItemTextA",
                      (void*)my_SetDlgItemTextA, (void**)&real_SetDlgItemTextA);
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "SendMessageA",
                      (void*)my_SendMessageA, (void**)&real_SendMessageA);
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "MessageBoxA",
                      (void*)my_MessageBoxA, (void**)&real_MessageBoxA);

            // 文件打开探针（诊断用，见 my_CreateFileA 上方说明）
            patch_iat((HMODULE)me.modBaseAddr, "KERNEL32.dll", "CreateFileA",
                      (void*)my_CreateFileA, (void**)&real_CreateFileA);
            patch_iat((HMODULE)me.modBaseAddr, "KERNEL32.dll", "CreateFileW",
                      (void*)my_CreateFileW, (void**)&real_CreateFileW);
            patch_iat((HMODULE)me.modBaseAddr, "KERNEL32.dll", "ReadFile",
                      (void*)my_ReadFile, (void**)&real_ReadFile);
            // 菜单
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "LoadMenuA",
                      (void*)my_LoadMenuA, (void**)&real_LoadMenuA);
            patch_iat((HMODULE)me.modBaseAddr, "USER32.dll", "SetMenuItemInfoA",
                      (void*)my_SetMenuItemInfoA, (void**)&real_SetMenuItemInfoA);
        } while (Module32NextW(snap, &me));
    }
    CloseHandle(snap);
}

// ─────────────────────── 启动 ───────────────────────

static void load_settings()
{
    wchar_t w[LF_FACESIZE];
    DWORD n = GetEnvironmentVariableW(L"CMVS_FONT", w, LF_FACESIZE);
    if (n > 0 && n < LF_FACESIZE) {
        // CreateFontA 收的是 ANSI(GBK) 串，所以从宽字符转回 ACP
        if (WideCharToMultiByte(CP_ACP, 0, w, -1, g_font, sizeof(g_font), NULL, NULL) <= 0)
            lstrcpynA(g_font, "SimHei", sizeof(g_font));
    }

    char v[8];
    if (GetEnvironmentVariableA("CMVS_PATCH", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_patch = FALSE;
    if (GetEnvironmentVariableA("CMVS_FONTHOOK", v, sizeof(v)) > 0 && v[0] == '1')
        g_enable_font = TRUE;
    if (GetEnvironmentVariableA("CMVS_FACESWAP", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_face = FALSE;
    if (GetEnvironmentVariableA("CMVS_NOTE", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_note = FALSE;
    if (GetEnvironmentVariableA("CMVS_TITLE", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_title = FALSE;
    if (GetEnvironmentVariableA("CMVS_UI", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_ui = FALSE;
    if (GetEnvironmentVariableA("CMVS_UIFONT", v, sizeof(v)) > 0 && v[0] == '0')
        g_enable_uifont = FALSE;
    // 对话框字体名跟正文走（默认 SimHei）
    MultiByteToWideChar(CP_ACP, 0, g_font, -1, g_uifont, LF_FACESIZE);

    // ♪ 的字形从哪个字体取（默认 MS Gothic）。引擎正文换成黑体后黑体没有 ♪，
    // 必须另找一个有这个字的字体，见 note_dc()。
    wchar_t nw[LF_FACESIZE];
    DWORD nn = GetEnvironmentVariableW(L"CMVS_NOTEFONT", nw, LF_FACESIZE);
    if (nn > 0 && nn < LF_FACESIZE) {
        if (WideCharToMultiByte(CP_ACP, 0, nw, -1, g_notefont, sizeof(g_notefont), NULL, NULL) <= 0)
            lstrcpynA(g_notefont, "NSimSun", sizeof(g_notefont));
    }
}

static void open_log()
{
    char path[MAX_PATH];
    GetModuleFileNameA(NULL, path, MAX_PATH);
    char* p = strrchr(path, '\\');
    if (p) *(p + 1) = 0;
    strcat_s(path, MAX_PATH, "cnpatch.log");
    fopen_s(&g_log, path, "w");
    if (!g_log) return;

    SYSTEMTIME st;
    GetLocalTime(&st);
    fprintf(g_log, "# cnpatch 启动 %04d-%02d-%02d %02d:%02d:%02d\n",
            st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    fprintf(g_log, "# 字体=%s  代码补丁=%s  字体替换=%s\n",
            g_font, g_enable_patch ? "开" : "关", g_enable_font ? "开" : "关");
    fflush(g_log);
}

// 崩溃处理器：把出错地址和寄存器写进日志，别让缓冲区把线索一起带走。
// 返回 CONTINUE_SEARCH，进程照常崩 —— 这里只做记录，不改变行为。
static LONG WINAPI veh_crash(EXCEPTION_POINTERS* ep)
{
    if (!g_log || !ep || !ep->ExceptionRecord) return EXCEPTION_CONTINUE_SEARCH;
    const EXCEPTION_RECORD* r = ep->ExceptionRecord;
    const CONTEXT* c = ep->ContextRecord;
    logf("crash\tcode=%08lX addr=%p tid=%lu\n",
         r->ExceptionCode, r->ExceptionAddress, GetCurrentThreadId());
    if (c)
        logf("crash\teip=%08lX eax=%08lX ebx=%08lX ecx=%08lX edx=%08lX "
             "esi=%08lX edi=%08lX ebp=%08lX esp=%08lX\n",
             c->Eip, c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp, c->Esp);
    // 出错地址附近 32 字节机器码，反汇编时对齐用
    if (r->ExceptionAddress) {
        const unsigned char* p = (const unsigned char*)r->ExceptionAddress;
        char hex[3 * 48 + 1] = { 0 };
        int n = 0;
        for (int i = -16; i < 32; ++i)
            n += sprintf_s(hex + n, sizeof(hex) - n, "%02X ", p[i]);
        logf("crash\tbytes[eip-16..eip+32]: %s\n", hex);
    }
    fflush(g_log);
    return EXCEPTION_CONTINUE_SEARCH;
}

// 补丁打不上时的提示。单独开线程弹，避免在 DllMain 里占着加载器锁死等。
static DWORD WINAPI warn_thread(LPVOID)
{
    MessageBoxW(NULL,
                L"汉化补丁未能生效：游戏程序与预期版本不符。\n"
                L"游戏仍会正常启动，但文字可能显示异常。\n\n"
                L"详见游戏目录下的 cnpatch.log。",
                L"cnpatch", MB_ICONWARNING | MB_OK);
    return 0;
}

BOOL WINAPI DllMain(HMODULE hSelf, DWORD reason, LPVOID)
{
    // 退出时补一行汇总：开一下游戏就能从日志直接看出 ♪ 到底有没有被认出来，
    // 不用去数前面那 256 行 glyph 记录。
    if (reason == DLL_PROCESS_DETACH) {
        if (g_log) {
            logf("info\t退出：字形请求 %ld 次，♪ 哨兵命中 %ld 次\n", g_glyph_calls, g_note_hits);
            fflush(g_log);
            fclose(g_log);
            g_log = NULL;
        }
        return TRUE;
    }
    if (reason != DLL_PROCESS_ATTACH) return TRUE;

    DisableThreadLibraryCalls(hSelf);
    InitializeCriticalSection(&g_cs);
    load_settings();
    AddVectoredExceptionHandler(1, veh_crash);

    {
        char v[8];
        if (GetEnvironmentVariableA("CMVS_NOLOG", v, sizeof(v)) == 0 || v[0] != '1')
            open_log();
    }

    int bad = 0;
    if (g_enable_patch) {
        bad = apply_code_patches();
        bad += apply_string_patches();
    }

    if (g_enable_ui) load_ui_table(hSelf);
    load_bundled_fonts(hSelf);

    patch_all_modules();

    HMODULE gdi = GetModuleHandleA("GDI32.dll");
    if (!real_CreateFontA)         real_CreateFontA         = (PFN_CreateFontA)GetProcAddress(gdi, "CreateFontA");
    if (!real_CreateFontIndirectA) real_CreateFontIndirectA = (PFN_CreateFontIndirectA)GetProcAddress(gdi, "CreateFontIndirectA");
    if (!real_GetGlyphOutlineA)    real_GetGlyphOutlineA    = (PFN_GetGlyphOutlineA)GetProcAddress(gdi, "GetGlyphOutlineA");
    if (!real_EnumFontFamiliesExA) real_EnumFontFamiliesExA = (PFN_EnumFontFamiliesExA)GetProcAddress(gdi, "EnumFontFamiliesExA");
    // GetGlyphOutlineW 引擎没导入（它只用 A 版），IAT 里找不到，必须自己取地址
    real_GetGlyphOutlineW = (PFN_GetGlyphOutlineW)GetProcAddress(gdi, "GetGlyphOutlineW");

    HMODULE user = GetModuleHandleA("USER32.dll");
    if (user) {
        if (!real_SetWindowTextA)  real_SetWindowTextA  = (PFN_SetWindowTextA)GetProcAddress(user, "SetWindowTextA");
        if (!real_CreateWindowExA) real_CreateWindowExA = (PFN_CreateWindowExA)GetProcAddress(user, "CreateWindowExA");
        if (!real_DialogBoxParamA) real_DialogBoxParamA = (PFN_DialogBoxParamA)GetProcAddress(user, "DialogBoxParamA");
        if (!real_SetDlgItemTextA) real_SetDlgItemTextA = (PFN_SetDlgItemTextA)GetProcAddress(user, "SetDlgItemTextA");
        if (!real_SendMessageA)    real_SendMessageA    = (PFN_SendMessageA)GetProcAddress(user, "SendMessageA");
        if (!real_LoadMenuA)       real_LoadMenuA       = (PFN_LoadMenuA)GetProcAddress(user, "LoadMenuA");
        if (!real_SetMenuItemInfoA) real_SetMenuItemInfoA = (PFN_SetMenuItemInfoA)GetProcAddress(user, "SetMenuItemInfoA");
        if (!real_MessageBoxA)     real_MessageBoxA     = (PFN_MessageBoxA)GetProcAddress(user, "MessageBoxA");
        // W 版游戏没导入，IAT 里没有，得自己取地址
        real_SetWindowTextW  = (PFN_SetWindowTextW)GetProcAddress(user, "SetWindowTextW");
        real_SetDlgItemTextW = (PFN_SetDlgItemTextW)GetProcAddress(user, "SetDlgItemTextW");
        real_SendMessageW    = (PFN_SendMessageW)GetProcAddress(user, "SendMessageW");
        real_DialogBoxParamW = (PFN_DialogBoxParamW)GetProcAddress(user, "DialogBoxParamW");
        real_SetMenuItemInfoW = (PFN_SetMenuItemInfoW)GetProcAddress(user, "SetMenuItemInfoW");
        real_MessageBoxW     = (PFN_MessageBoxW)GetProcAddress(user, "MessageBoxW");
    }

    // 文件探针的实际函数地址（IAT 里可能没有这两个导入，得自己取）
    HMODULE k32 = GetModuleHandleA("KERNEL32.dll");
    if (k32) {
        if (!real_CreateFileA) real_CreateFileA = (PFN_CreateFileA)GetProcAddress(k32, "CreateFileA");
        if (!real_CreateFileW) real_CreateFileW = (PFN_CreateFileW)GetProcAddress(k32, "CreateFileW");
        if (!real_ReadFile)    real_ReadFile    = (PFN_ReadFile)GetProcAddress(k32, "ReadFile");
    }

    logf("info\tCreateFontA=%p CreateFontIndirectA=%p GetGlyphOutlineW=%p\n",
         (void*)real_CreateFontA, (void*)real_CreateFontIndirectA, (void*)real_GetGlyphOutlineW);
    logf("info\t♪ 哨兵映射 %s（哨兵 0x%04X -> U+%04X）字形取自字体 %s\n",
         g_enable_note ? "开" : "关", kNoteSentinel, kNoteChar, g_notefont);
    logf("info\t窗口标题：SJIS 全角空格 81 40 -> A1 A1 %s\n",
         g_enable_title ? "开" : "关（CMVS_TITLE=0）");
    logf("info\t字体 %s：%s\n", g_font,
         g_enable_font ? "全量 hook 模式（4 个调用点全改，排版会算错）"
                       : (g_enable_face ? "只换 charset==134 那一处（正文）"
                                        : "不换，用 GDI 自动替换"));

    if (bad) {
        // 补丁打不上说明 exe 跟预期不是一个版本，静默继续只会让人一头雾水
        logf("info\t有 %d 处补丁失败，未修改游戏\n", bad);
        if (g_log) fflush(g_log);
        // DllMain 里还占着加载器锁，弹窗可能死锁 —— 丢到另一个线程去弹
        CloseHandle(CreateThread(NULL, 0, warn_thread, NULL, 0, NULL));
    }
    return TRUE;
}
