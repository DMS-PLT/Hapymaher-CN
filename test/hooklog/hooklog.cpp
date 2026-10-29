// hooklog.dll —— 只读探头：记录 CMVS 引擎向 GDI 请求字形/字体的细节
//
// 拦截三个导入函数（通过改写游戏的导入表，不碰游戏文件）：
//   CreateFontA        记录引擎创建了什么字体
//   GetGlyphOutlineA   记录引擎要了哪个字形的轮廓（关键：字符码！）
//   GetTextMetricsA    记录当前字体的度量（含字体名）
//
// 日志写到游戏 exe 同目录的 hooklog.txt。
// 必须编译成 32 位（游戏是 32 位进程）。

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <string.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

typedef HFONT(WINAPI* PFN_CreateFontA)(int, int, int, int, int, DWORD, DWORD, DWORD, DWORD,
                                       DWORD, DWORD, DWORD, DWORD, LPCSTR);
typedef DWORD(WINAPI* PFN_GetGlyphOutlineA)(HDC, UINT, UINT, LPGLYPHMETRICS, DWORD, LPVOID, const MAT2*);
typedef BOOL(WINAPI* PFN_GetTextMetricsA)(HDC, LPTEXTMETRICA);

static PFN_CreateFontA      real_CreateFontA;
static PFN_GetGlyphOutlineA real_GetGlyphOutlineA;
static PFN_GetTextMetricsA  real_GetTextMetricsA;

static FILE*             g_log;
static CRITICAL_SECTION  g_cs;
static volatile LONG     g_bytes;           // 已写入字节数，超上限就停
static const long        LOG_LIMIT = 32L * 1024 * 1024;
static char              g_face[64] = "";   // 上次记录的字体名，变化时才记

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
    if ((g_bytes & 0xFFF) < 512) fflush(g_log);   // 约每 4KB 刷一次
    LeaveCriticalSection(&g_cs);
}

static HFONT WINAPI my_CreateFontA(int cHeight, int cWidth, int cEscapement, int cOrientation,
                                   int cWeight, DWORD bItalic, DWORD bUnderline, DWORD bStrikeOut,
                                   DWORD iCharSet, DWORD iOutPrecision, DWORD iClipPrecision,
                                   DWORD iQuality, DWORD iPitchAndFamily, LPCSTR pszFaceName)
{
    logf("font\th=%d\tw=%d\tcharset=%lu\tquality=%lu\tweight=%d\tface=%s\n",
         cHeight, cWidth, iCharSet, iQuality, cWeight,
         (pszFaceName && *pszFaceName) ? pszFaceName : "(default)");
    return real_CreateFontA(cHeight, cWidth, cEscapement, cOrientation, cWeight, bItalic,
                            bUnderline, bStrikeOut, iCharSet, iOutPrecision, iClipPrecision,
                            iQuality, iPitchAndFamily, pszFaceName);
}

static DWORD WINAPI my_GetGlyphOutlineA(HDC hdc, UINT uChar, UINT uFormat, LPGLYPHMETRICS lpgm,
                                        DWORD cbBuffer, LPVOID lpvBuffer, const MAT2* lpmat2)
{
    DWORD ret = real_GetGlyphOutlineA(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);
    // uChar 是引擎传进来的字符码；同时记录字形尺寸，方便看排版
    unsigned w = (ret != GDI_ERROR && lpgm) ? lpgm->gmBlackBoxX : 0;
    unsigned h = (ret != GDI_ERROR && lpgm) ? lpgm->gmBlackBoxY : 0;
    logf("glyph\t0x%04X\tfmt=%u\t%d\t%d\t%d\n", uChar, uFormat, (int)ret, w, h);
    return ret;
}

static BOOL WINAPI my_GetTextMetricsA(HDC hdc, LPTEXTMETRICA lptm)
{
    BOOL ret = real_GetTextMetricsA(hdc, lptm);
    if (ret && lptm) {
        // TEXTMETRICA 结构里没有字体名字段（只有 W 版有），得单独问 DC
        char face[LF_FACESIZE] = "";
        GetTextFaceA(hdc, LF_FACESIZE, face);
        if (lstrcmpA(g_face, face) != 0) {
            lstrcpynA(g_face, face, sizeof(g_face));
            logf("metrics\theight=%ld\tascent=%ld\tdescent=%ld\tavechar=%ld\tface=%s\n",
                 lptm->tmHeight, lptm->tmAscent, lptm->tmDescent, lptm->tmAveCharWidth, face);
        }
    }
    return ret;
}

// 改写导入表：把 exe 对某个导入函数的引用指向我们
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
        const char* name = (const char*)(base + imp->Name);
        if (_stricmp(name, dll) != 0) continue;
        if (!imp->OriginalFirstThunk) continue;   // 没有 ILT 就没法按名字找

        // 名字要从 ILT（OriginalFirstThunk）读；IAT（FirstThunk）里已经是解析后的地址了
        PIMAGE_THUNK_DATA ilt = (PIMAGE_THUNK_DATA)(base + imp->OriginalFirstThunk);
        PIMAGE_THUNK_DATA iat = (PIMAGE_THUNK_DATA)(base + imp->FirstThunk);

        for (; ilt->u1.AddressOfData; ++ilt, ++iat) {
            if (ilt->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            PIMAGE_IMPORT_BY_NAME ibn = (PIMAGE_IMPORT_BY_NAME)(base + ilt->u1.AddressOfData);
            if (strcmp((const char*)ibn->Name, func) != 0) continue;

            DWORD old;
            if (VirtualProtect(&iat->u1.Function, sizeof(ULONG_PTR), PAGE_READWRITE, &old)) {
                if (oldfn) *oldfn = (void*)iat->u1.Function;
                iat->u1.Function = (ULONG_PTR)newfn;
                VirtualProtect(&iat->u1.Function, sizeof(ULONG_PTR), old, &old);
                logf("hook\t%s\t%s\tpatched\n", dll, func);
            }
        }
    }
}

static void open_log()
{
    char path[MAX_PATH];
    GetModuleFileNameA(NULL, path, MAX_PATH);
    char* p = strrchr(path, '\\');
    if (p) *(p + 1) = 0;
    strcat_s(path, MAX_PATH, "hooklog.txt");
    fopen_s(&g_log, path, "w");
    if (g_log) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(g_log, "# hooklog 启动 %04d-%02d-%02d %02d:%02d:%02d\n",
                st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        fflush(g_log);
    }
}

// 给所有已加载模块打补丁 —— 游戏可能通过自己的辅助 DLL 调用 GDI
static void patch_all_modules()
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    if (snap == INVALID_HANDLE_VALUE) return;

    MODULEENTRY32W me = { sizeof(me) };
    if (Module32FirstW(snap, &me)) {
        do {
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "CreateFontA",
                      (void*)my_CreateFontA, (void**)&real_CreateFontA);
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "GetGlyphOutlineA",
                      (void*)my_GetGlyphOutlineA, (void**)&real_GetGlyphOutlineA);
            patch_iat((HMODULE)me.modBaseAddr, "GDI32.dll", "GetTextMetricsA",
                      (void*)my_GetTextMetricsA, (void**)&real_GetTextMetricsA);
        } while (Module32NextW(snap, &me));
    }
    CloseHandle(snap);
}

BOOL WINAPI DllMain(HMODULE hSelf, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hSelf);
        InitializeCriticalSection(&g_cs);
        open_log();

        patch_all_modules();

        HMODULE gdi = GetModuleHandleA("GDI32.dll");
        // 万一某个没打上（比如是按序号导入或被动态调用），直接取地址兜底
        if (!real_CreateFontA)      real_CreateFontA      = (PFN_CreateFontA)GetProcAddress(gdi, "CreateFontA");
        if (!real_GetGlyphOutlineA) real_GetGlyphOutlineA = (PFN_GetGlyphOutlineA)GetProcAddress(gdi, "GetGlyphOutlineA");
        if (!real_GetTextMetricsA)  real_GetTextMetricsA  = (PFN_GetTextMetricsA)GetProcAddress(gdi, "GetTextMetricsA");
        logf("info\tmodules patched, gdi32=0x%p, CreateFontA=0x%p\n", (void*)gdi, (void*)real_CreateFontA);
    }
    else if (reason == DLL_PROCESS_DETACH) {
        if (g_log) { fflush(g_log); fclose(g_log); g_log = nullptr; }
    }
    return TRUE;
}
