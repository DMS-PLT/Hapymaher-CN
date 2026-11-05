@echo off
chcp 936 >nul
echo ==================================================
echo   Chinese test: inject cnpatch.dll and start Hapymaher FD
echo.
echo   Same DLL as the main game
echo   (both cmvs32.exe are byte-identical).
echo.
echo   Defaults (used when no env var is set):
echo     CMVS_PATCH=1      9 DBCS checks + 1 charset patch
echo     CMVS_FONT=SimHei  body + dialog font
echo     CMVS_FACESWAP=1   set 0 to keep the old font
echo     CMVS_NOTE=1       music-note glyph from NSimSun
echo     CMVS_UI=1         UI translation, table = cnpatch_ui.txt
echo     CMVS_UIFONT=1     set 0 to keep the dialog template font
echo.
echo   Log: cnpatch.log in the FD game folder
echo ==================================================
echo.
set "TARGET=%~1"
if not defined TARGET if exist "..\..\ハピメア Fragmentation Dream フルHD版\cmvs32.exe" set "TARGET=..\..\ハピメア Fragmentation Dream フルHD版\cmvs32.exe"
if defined TARGET (
  "%~dp0launch.exe" "%TARGET%"
) else (
  "%~dp0launch.exe" fd
)
echo.
echo   Done. Log: cnpatch.log in the FD game folder
pause
