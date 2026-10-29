@echo off
rem build glyph_hook_test.exe (32-bit, matches the game process)
setlocal
set "VS=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat"
cd /d "%~dp0"
call "%VS%" -arch=x86 -host_arch=x64 >nul
if errorlevel 1 exit /b 1
if not exist obj mkdir obj
cl /nologo /O2 /MT /W3 /utf-8 glyph_hook_test.cpp /Fe:glyph_hook_test.exe /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
echo [OK] glyph_hook_test.exe
