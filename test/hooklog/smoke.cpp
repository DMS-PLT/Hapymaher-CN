// smoke.exe —— 自检用：创建一次字体、取一次度量，验证注入链是否工作
#include <windows.h>
#include <stdio.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

int main(void)
{
    HWND h = GetDesktopWindow();
    HDC dc = GetDC(h);
    HGDIOBJ f = CreateFontA(-20, 0, 0, 0, 400, 0, 0, 0, 128, 0, 0, 0, 0, "MS Gothic");
    SelectObject(dc, f);
    TEXTMETRICA tm;
    GetTextMetricsA(dc, &tm);
    printf("smoke: font height=%ld face-check done\n", tm.tmHeight);
    ReleaseDC(h, dc);
    return 0;
}
