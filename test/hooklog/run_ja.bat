@echo off
chcp 936 >nul
set CMVS_FONTHOOK=0
echo ==================================================
echo   Stage 1: original Japanese + patch DLL
echo   (font replacement OFF so Japanese renders normally)
echo.
echo   Check: Japanese text looks NORMAL.
echo   No broken kana, no stray line breaks.
echo   This proves the code patches did not damage the
echo   original behaviour.
echo.
echo   Then quit the game normally.
echo ==================================================
echo.
set "TARGET=%~1"
if not defined TARGET if not exist ".\cmvs32.exe" if exist "..\..\ハピメア フルHD版\cmvs32.exe" set "TARGET=..\..\ハピメア フルHD版\cmvs32.exe"
if defined TARGET (
  ".\launch.exe" "%TARGET%"
) else (
  ".\launch.exe"
)
echo.
echo   Done. Log: cnpatch.log in the game folder
pause
