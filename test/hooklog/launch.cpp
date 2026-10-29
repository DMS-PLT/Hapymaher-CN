// launch.exe —— 用"挂起启动 + 注入 DLL"的方式运行游戏，不改游戏任何文件
//
// 用法：launch.exe [<游戏exe路径>|fd] [游戏参数...]
//   cnpatch.dll 必须和 launch.exe 放在同一目录
//   不给参数时启动**自己所在目录**的 cmvs32.exe（发布包里就是这样放的）
//   第一个参数写 fd 时同样走上面这条（FD 包放在 FD 的游戏目录里，各自独立）
//
// 编译出两个版本：
//   launch.exe      —— 控制台版，开发调试用（会打印过程、等游戏退出）
//   launch_gui.exe  —— 发布版，无控制台、失败弹窗、注入完就退出（-DLAUNCH_GUI）

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include <shellapi.h>

// 默认目标：启动器自己所在目录的 cmvs32.exe。
// 发布包里启动器和游戏 exe 放在同一层，这样本体/FD 两个包可以共用同一份代码，
// 不用在程序里写死任何路径。
static bool resolve_default_target(wchar_t* out, size_t cap)
{
    wchar_t self[MAX_PATH];
    if (!GetModuleFileNameW(NULL, self, MAX_PATH)) return false;
    wchar_t* slash = wcsrchr(self, L'\\');
    if (!slash) return false;
    *(slash + 1) = 0;
    _snwprintf_s(out, cap, _TRUNCATE, L"%scmvs32.exe", self);
    return true;
}

static void die(const wchar_t* msg)
{
#ifdef LAUNCH_GUI
    MessageBoxW(NULL, msg, L"ハピメア汉化补丁", MB_ICONERROR | MB_OK);
#else
    fwprintf(stderr, L"[错误] %s (GetLastError=%lu)\n", msg, GetLastError());
#endif
    exit(1);
}

#ifdef LAUNCH_GUI
#define SAY(...) ((void)0)
#else
#define SAY wprintf
#endif

// ⚠ 不设这个的话，下面 wprintf 里的中文会**整个消失**（只剩 `[*] `）：
//   CRT 默认是 "C" locale，宽字符转多字节转不出来，MSVC 直接把这段丢掉，
//   不报错也不提示。控制台按 chcp 936 跑，所以让 CRT 也按系统码页来。
static int real_main(int argc, wchar_t** argv)
{
#ifndef LAUNCH_GUI
    setlocale(LC_ALL, "");
#endif

    // 第一个参数可以是完整路径（调试用）；`fd` 或者不给参数都启动同目录的 cmvs32.exe
    wchar_t targetbuf[MAX_PATH];
    const wchar_t* target = (argc >= 2 && argv[1] && argv[1][0] && wcscmp(argv[1], L"fd") != 0)
                          ? argv[1] : targetbuf;
    if (target == targetbuf && !resolve_default_target(targetbuf, _countof(targetbuf)))
        die(L"无法定位自身路径");

    // 1. 找出要注入的 DLL（和本程序同目录）
    //    默认 cnpatch.dll（汉化补丁）；想跑别的探头时用 CMVS_DLL 指定文件名
    wchar_t dllname[64] = L"cnpatch.dll";
    {
        wchar_t env[64];
        DWORD n = GetEnvironmentVariableW(L"CMVS_DLL", env, 64);
        if (n > 0 && n < 64) wcscpy_s(dllname, env);
    }

    wchar_t dll[MAX_PATH];
    GetModuleFileNameW(NULL, dll, MAX_PATH);
    wchar_t* slash = wcsrchr(dll, L'\\');
    if (!slash) die(L"无法定位自身路径");
    *(slash + 1) = 0;
    wcscat_s(dll, MAX_PATH, dllname);
    if (GetFileAttributesW(dll) == INVALID_FILE_ATTRIBUTES)
        die(L"找不到要注入的 DLL（要和 launch.exe 放在一起，或设 CMVS_DLL 指定）");

    // 2. 拼命令行
    wchar_t cmd[MAX_PATH * 2];
    _snwprintf_s(cmd, _countof(cmd), _TRUNCATE, L"\"%s\"", target);
    for (int i = 2; i < argc; ++i) {
        size_t len = wcslen(cmd);
        _snwprintf_s(cmd + len, _countof(cmd) - len, _TRUNCATE, L" %s", argv[i]);
    }

    SAY(L"[*] 启动: %s\n", cmd);
    SAY(L"[*] 注入: %s\n", dll);

    // 游戏目录 —— 必须设成工作目录，否则游戏找不到自己的数据
    wchar_t workdir[MAX_PATH];
    wcsncpy_s(workdir, target, MAX_PATH);
    wchar_t* ws = wcsrchr(workdir, L'\\');
    if (ws) *ws = 0;

    // 3. 挂起方式启动
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, workdir, &si, &pi))
        die(L"启动游戏失败");

    // 4. 在目标进程里申请内存写入 DLL 路径，再开线程调 LoadLibraryW
    size_t bytes = (wcslen(dll) + 1) * sizeof(wchar_t);
    void* remote = VirtualAllocEx(pi.hProcess, NULL, bytes, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote) die(L"目标进程内存分配失败");

    if (!WriteProcessMemory(pi.hProcess, remote, dll, bytes, NULL))
        die(L"写入 DLL 路径失败");

    HMODULE k32 = GetModuleHandleW(L"kernel32.dll");
    LPTHREAD_START_ROUTINE loadlib =
        (LPTHREAD_START_ROUTINE)GetProcAddress(k32, "LoadLibraryW");
    HANDLE th = CreateRemoteThread(pi.hProcess, NULL, 0, loadlib, remote, 0, NULL);
    if (!th) {
        TerminateProcess(pi.hProcess, 1);
        die(L"注入线程创建失败（可能被安全软件拦截）");
    }

    WaitForSingleObject(th, 15000);        // 等 DLL 加载完再放行
    DWORD mod = 0;
    GetExitCodeThread(th, &mod);
    CloseHandle(th);
    VirtualFreeEx(pi.hProcess, remote, 0, MEM_RELEASE);

    if (mod == 0) {
        TerminateProcess(pi.hProcess, 1);
        die(L"DLL 未能加载（返回 0），检查位数是否匹配（游戏 32 位，DLL 必须 32 位）");
    }
    SAY(L"[OK] 已注入，继续运行游戏\n");

    // 5. 放行
    ResumeThread(pi.hThread);

#ifdef LAUNCH_GUI
    // 发布版：注入完就退出，不在后台留一个启动器进程
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
#else
    WaitForSingleObject(pi.hProcess, INFINITE);

    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    SAY(L"[*] 游戏退出，返回码 %lu\n", code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
#endif
}

#ifdef LAUNCH_GUI
int WINAPI wWinMain(HINSTANCE, HINSTANCE, LPWSTR, int)
{
    int argc = 0;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    int r = real_main(argc ? argc : 0, argv);
    if (argv) LocalFree(argv);
    return r;
}
#else
int wmain(int argc, wchar_t** argv) { return real_main(argc, argv); }
#endif
