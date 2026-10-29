@echo off
chcp 936 >nul
set CMVS_FONT=SimSun
echo ==================================================
echo   Stage 2b: Chinese + DLL, font = SimSun (proportional)
echo.
echo   SimHei is reported by GDI as fixed-pitch (0x36),
echo   SimSun as proportional (0x07) - same as the font the
echo   AI patch ends up using. Testing whether that flag is
echo   what makes the message box size itself correctly.
echo.
echo   CHECK: does the box now wrap the text?
echo ==================================================
echo.
".\launch.exe"
echo.
echo   Done. Log: cnpatch.log in the game folder
pause
