@echo off
chcp 936 >nul
echo ==================================================
echo   Chinese test: inject cnpatch.dll and start Hapymaher
echo.
echo   Defaults (used when no env var is set):
echo     CMVS_PATCH=1      9 DBCS checks + 1 charset patch
echo     CMVS_FONT=SimHei  body + dialog font
echo     CMVS_FACESWAP=1   set 0 to keep the old font
echo     CMVS_NOTE=1       music-note glyph from NSimSun
echo     CMVS_UI=1         UI translation, table = cnpatch_ui.txt
echo     CMVS_UIFONT=1     set 0 to keep the dialog template font
echo.
echo   For the Japanese control run use run_ja.bat.
echo   Log: cnpatch.log in the game folder
echo ==================================================
echo.
".\launch.exe"
echo.
echo   Done. Log: cnpatch.log in the game folder
pause
