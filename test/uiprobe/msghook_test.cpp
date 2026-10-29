// msghook_test.exe —— 离线自检：cnpatch.dll 的 MessageBoxA hook 到底有没有生效
//
// 为什么要这个：报错框很难手动触发（要么切声卡设备，要么把 .cpz 弄坏），
// 而且真触发了也得靠肉眼看。这里把「触发」和「判断」都变成程序：
//
//   1. 把 cnpatch.dll 载进本进程（patch_all_modules 会连本进程的 IAT 一起挂）
//   2. 用**和游戏一模一样的姿势**调 MessageBoxA：SJIS 字节 + 日文原文
//   3. 另一个线程盯着有没有弹出标题为「包文件异常」的窗口
//      找到了 = 命中译文表 + 转成了 W 版 ✓，顺手读一下正文字，然后关掉
//
// 判据是窗口标题和正文文字，不用人看，退出码 0/1 就能进 CI。
//
// 编译：
//     cl /nologo /O2 /MT /EHsc /W3 /utf-8 msghook_test.cpp /Fe:msghook_test.exe
//     （32 位）
// 跑之前 cnpatch.dll 和 cnpatch_ui.txt 得在 test\hooklog\ 里。

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <process.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 和 cnpatch.dll 同目录
static const wchar_t* kDll =
    L"C:\\Users\\DMS\\Desktop\\Hapymaher\\test\\hooklog\\cnpatch.dll";
// 真实的游戏 exe —— 只当**资源库**打开（LOAD_LIBRARY_AS_DATAFILE），不执行它
static const wchar_t* kExe =
    L"C:\\Users\\DMS\\Desktop\\Hapymaher\\ハピメア フルHD版\\cmvs32.exe";

// 报错框正文里日语原文（游戏的原样），比对目标是我们译文表里的中文
static const wchar_t* kJpBody    = L"パックファイルが破損しているので終了します。";
static const wchar_t* kJpCaption = L"パックファイル異常";
static const wchar_t* kZhBody    = L"包文件已损坏，即将退出。";
static const wchar_t* kZhCaption = L"包文件异常";

static volatile LONG g_result;      // 0=跑着 1=标题对了 -1=超时
static wchar_t       g_seen_cap[256];
static wchar_t       g_seen_body[512];

// 宽字符 → SJIS 字节。游戏交给 MessageBoxA 的就是这个形态。
static LPCSTR sjis(const wchar_t* w)
{
    static char buf[4][1024];
    static int i = 0;
    char* b = buf[i++ & 3];
    if (WideCharToMultiByte(932, 0, w, -1, b, 1024, NULL, NULL) <= 0) b[0] = 0;
    return b;
}

static void out(const wchar_t* fmt, ...)
{
    wchar_t w[1024];
    va_list ap;
    va_start(ap, fmt);
    _vsnwprintf_s(w, _countof(w), _TRUNCATE, fmt, ap);
    va_end(ap);
    char u8[3072];
    if (WideCharToMultiByte(CP_UTF8, 0, w, -1, u8, sizeof(u8), NULL, NULL) > 0)
        fputs(u8, stdout);
    fflush(stdout);
}

static BOOL CALLBACK pick(HWND h, LPARAM)
{
    wchar_t cls[64];
    GetClassNameW(h, cls, 64);
    if (wcscmp(cls, L"#32770") == 0) {
        GetWindowTextW(h, g_seen_cap, 256);
        // 正文可能在若干个 Static 里（带图标时还会多一个），取文字最长那个
        g_seen_body[0] = 0;
        for (HWND st = NULL; (st = FindWindowExW(h, st, L"Static", NULL)) != NULL; ) {
            wchar_t t[512];
            if (GetWindowTextW(st, t, 512) > 0 && wcslen(t) > wcslen(g_seen_body))
                wcscpy_s(g_seen_body, 512, t);
        }
        InterlockedExchange(&g_result, 1);
        PostMessageW(h, WM_CLOSE, 0, 0);
        return FALSE;
    }
    return TRUE;
}

static unsigned __stdcall watcher(void*)
{
    for (int i = 0; i < 200 && !g_result; ++i) {     // 最多等 10 秒
        EnumWindows(pick, 0);
        Sleep(50);
    }
    if (!g_result) InterlockedExchange(&g_result, -1);
    return 0;
}

// ─────────── 第二关：真实对话框的字体有没有被换成中文 ───────────

static BOOL CALLBACK dump_child(HWND c, LPARAM)
{
    wchar_t cls[64] = L"", txt[256] = L"";
    LOGFONTW lf; memset(&lf, 0, sizeof(lf));
    GetClassNameW(c, cls, 64);
    GetWindowTextW(c, txt, 256);
    HFONT f = (HFONT)SendMessageW(c, WM_GETFONT, 0, 0);
    if (f) GetObjectW(f, sizeof(lf), &lf);
    out(L"      %-8ls 字=%-22ls 字体=%-16ls 高=%ld\n",
        cls, txt, lf.lfFaceName[0] ? lf.lfFaceName : L"(无)", lf.lfHeight);
    return TRUE;
}

static INT_PTR CALLBACK probe_proc(HWND h, UINT m, WPARAM, LPARAM)
{
    static const UINT kDump = WM_APP + 1;
    if (m == WM_INITDIALOG) {
        // 不能在这儿查字体 —— cnpatch 的包壳是在我们的 proc **返回之后**
        // 才调 ui_translate_dialog（要先让游戏把运行时文字填完）。
        // post 给自己，等下一轮消息再查，那时字体已经换好了。
        PostMessageW(h, kDump, 0, 0);
        return TRUE;
    }
    if (m == kDump) {
        wchar_t cap[256] = L"";
        LOGFONTW lf; memset(&lf, 0, sizeof(lf));
        GetWindowTextW(h, cap, 256);
        HFONT f = (HFONT)SendMessageW(h, WM_GETFONT, 0, 0);
        if (f) GetObjectW(f, sizeof(lf), &lf);
        out(L"    对话框标题 = %ls\n", cap);
        out(L"    %-8ls 字=%-22ls 字体=%-16ls 高=%ld\n",
            L"(自己)", cap, lf.lfFaceName[0] ? lf.lfFaceName : L"(无)", lf.lfHeight);
        RECT wr, cr;
        GetWindowRect(h, &wr);
        GetClientRect(h, &cr);
        out(L"    GWL_STYLE = 0x%08lX  (WS_CAPTION=0x00C00000, DS_MODALFRAME=0x80)\n",
            (unsigned long)GetWindowLongW(h, GWL_STYLE));
        out(L"    窗口 %ldx%ld  客户区 %ldx%ld  => 非客户区高 %ld\n",
            wr.right - wr.left, wr.bottom - wr.top, cr.right, cr.bottom,
            (wr.bottom - wr.top) - cr.bottom);

        // 标题栏是不是跟着**对话框字体**走？设一个巨大的字体，看非客户区高度变不变。
        // 变了 = 标题用对话框字体画 => 换掉对话框字体就能修那行标题。
        HFONT big = CreateFontW(-40, 0, 0, 0, 400, 0, 0, 0, 134, 0, 0, 0, 0, L"SimHei");
        SendMessageW(h, WM_SETFONT, (WPARAM)big, TRUE);
        GetWindowRect(h, &wr); GetClientRect(h, &cr);
        out(L"    [对照] 换成 40 像素高的字体后，非客户区高 %ld\n",
            (wr.bottom - wr.top) - cr.bottom);

        EnumChildWindows(h, dump_child, 0);
        EndDialog(h, 0);
        return TRUE;
    }
    return FALSE;
}

static int dialog_phase()
{
    // 只映射资源，不跑 exe
    HMODULE res = LoadLibraryExW(kExe, NULL, LOAD_LIBRARY_AS_DATAFILE);
    if (!res) {
        out(L"[FAIL] 打不开 %ls 的资源（GetLastError=%lu）\n", kExe, GetLastError());
        return 1;
    }
    out(L"[*] 从 cmvs32.exe 打开真实 DIALOG 132（メッセージダイアログ）\n");
    fflush(NULL);
    INT_PTR r = DialogBoxParamA((HINSTANCE)res, MAKEINTRESOURCEA(132),
                                NULL, probe_proc, 0);
    if (r == -1) {
        out(L"[FAIL] DialogBoxParamA 失败（GetLastError=%lu）\n", GetLastError());
        FreeLibrary(res);
        return 1;
    }
    FreeLibrary(res);
    return 0;
}

int main()
{
    SetConsoleOutputCP(CP_UTF8);

    // 别去改引擎 —— 本进程里根本没有 cmvs32.exe
    _putenv_s("CMVS_PATCH", "0");

    HMODULE dll = LoadLibraryW(kDll);
    if (!dll) {
        out(L"[FAIL] 载入 %s 失败（GetLastError=%lu）\n", kDll, GetLastError());
        return 1;
    }
    out(L"[*] 已载入 cnpatch.dll\n");

    // ⚠ 屏障：MSVC /O2 会把 IAT 槽的**值**缓存在寄存器里跨过 LoadLibrary
    //   （当初调 glyph hook 就是这么被坑的，volatile 都不够，得有个它猜不透的调用）。
    fflush(NULL);

    // 走 IAT 调 MessageBoxA，不要用 GetProcAddress —— 那拿的是 user32 里的真身，
    // 会绕过我们刚写进 IAT 的 hook。
    static int (WINAPI *volatile mb)(HWND, LPCSTR, LPCSTR, UINT);
    mb = MessageBoxA;

    HANDLE th = (HANDLE)_beginthreadex(NULL, 0, watcher, NULL, 0, NULL);
    out(L"[*] 调用 MessageBoxA（SJIS 字节 + 日文原文）…\n");
    int ret = mb(NULL, sjis(kJpBody), sjis(kJpCaption), MB_OK | MB_SETFOREGROUND);
    out(L"[*] MessageBoxA 返回 %d\n", ret);

    WaitForSingleObject(th, 12000);
    CloseHandle(th);

    int rc = 1;
    if (g_result == 1) {
        int cap = wcscmp(g_seen_cap, kZhCaption) == 0;
        int body = wcscmp(g_seen_body, kZhBody) == 0;
        out(L"    弹出窗口标题 = %ls\n", g_seen_cap);
        out(L"    弹出窗口正文 = %ls\n", g_seen_body);
        out(L"[%ls] 标题译对\n", cap ? L"OK" : L"!!");
        out(L"[%ls] 正文译对\n", body ? L"OK" : L"!!");
        rc = (cap && body) ? 0 : 1;
    } else {
        out(L"[FAIL] 10 秒内没等到对话框。当前所有 #32770 窗口：\n");
        EnumWindows(pick, 0);          // pick 里会填 g_seen_*
        out(L"    标题=%ls\n", g_seen_cap);
        if (g_seen_cap[0] == 0) out(L"    （一个都没有）\n");
    }

    out(L"\n%s\n", rc == 0 ? L"结果：MessageBoxA hook 生效 ✅"
                           : L"结果：没通过 ❌");
    if (rc != 0) return rc;

    out(L"\n────────── 第二关：真实对话框的字体 ──────────\n");
    int rc2 = dialog_phase();
    out(L"\n%s\n", rc2 == 0 ? L"结果：见上面各控件的字体（应全是 SimHei，不再是 ＭＳ Ｐゴシック）"
                           : L"结果：对话框这一关没通过 ❌");
    return rc2;
}
