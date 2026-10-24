@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Günlük Finans ve Ekonomi Bülteni hazırlanıyor...
python main.py %*
echo.
pause
