@echo off
setlocal
set "ARCH=%~1"
if "%ARCH%"=="" set "ARCH=x64"
set "CLEAN=%~2"
set "VS=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat"
set "BUILD=C:\Users\DMS\Desktop\Hapymaher\test\rxcmvs-build\%ARCH%"
set "OUT=C:\Users\DMS\Desktop\Hapymaher\tools\RxCMVS"
call "%VS%" -arch=%ARCH% -host_arch=x64 >nul
if errorlevel 1 exit /b 1
if /i "%CLEAN%"=="clean" cmake --build "%BUILD%" --target clean
cmake -S . -B "%BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release -DRXCMVS_BIN_DIR=%OUT%
if errorlevel 1 exit /b 1
cmake --build "%BUILD%"
if errorlevel 1 exit /b 1
echo [OK] output at %OUT%
