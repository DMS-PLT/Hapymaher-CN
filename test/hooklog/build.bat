@echo off
rem build cnpatch.dll + hooklog.dll + launch.exe + smoke.exe + fontmetrics.exe (all 32-bit)
setlocal
set "VS=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat"
cd /d "%~dp0"
call "%VS%" -arch=x86 -host_arch=x64 >nul
if errorlevel 1 exit /b 1
cl /nologo /LD /O2 /MT /EHsc /W3 /utf-8 cnpatch.cpp /Fe:cnpatch.dll /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
cl /nologo /LD /O2 /MT /EHsc /W3 /utf-8 hooklog.cpp /Fe:hooklog.dll /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /W3 /utf-8 launch.cpp /Fe:launch.exe /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
rem 发布版：无控制台、失败弹窗、注入完就退出；本体/FD 各带自家图标
if not exist obj\gui md obj\gui
if not exist obj\gui_fd md obj\gui_fd
rc /nologo /fo obj\gui\icon_main.res icon_main.rc
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /W3 /utf-8 /DLAUNCH_GUI launch.cpp obj\gui\icon_main.res /Fe:launch_gui.exe /Fo:obj\gui\ /link /SUBSYSTEM:WINDOWS /INCREMENTAL:NO user32.lib shell32.lib
if errorlevel 1 exit /b 1
rc /nologo /fo obj\gui_fd\icon_fd.res icon_fd.rc
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /W3 /utf-8 /DLAUNCH_GUI launch.cpp obj\gui_fd\icon_fd.res /Fe:launch_gui_fd.exe /Fo:obj\gui_fd\ /link /SUBSYSTEM:WINDOWS /INCREMENTAL:NO user32.lib shell32.lib
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /W3 /utf-8 smoke.cpp /Fe:smoke.exe /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
cl /nologo /TP /O2 /MT /W3 /utf-8 fontmetrics.c /Fe:fontmetrics.exe /Fo:obj\ /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
echo [OK] cnpatch.dll + hooklog.dll + launch.exe + smoke.exe + fontmetrics.exe
