@echo off
title PC Cleaner Macro
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Erro ao iniciar. Verifique se o Python 3 esta instalado.
    pause
)