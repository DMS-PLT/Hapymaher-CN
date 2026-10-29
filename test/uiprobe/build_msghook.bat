@echo off
rem build msghook_test.exe (32-bit, offline self-test for the MessageBoxA hook)
setlocal
set "VS=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat"
cd /d "%~dp0"
call "%VS%" -arch=x86 -host_arch=x64 >nul
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /W3 /utf-8 msghook_test.cpp /Fe:msghook_test.exe /Fo:obj\\ user32.lib gdi32.lib /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
echo [OK] msghook_test.exe
