@echo off
chcp 65001 >nul
title Excel同期システム セットアップ

echo.
echo  ╔══════════════════════════════════════╗
echo  ║  Excel同期システム セットアップ       ║
echo  ╚══════════════════════════════════════╝
echo.

:: Python の存在確認
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Pythonがインストールされていません。
    echo.
    echo 以下のURLからPython 3.11以上をインストールしてください:
    echo   https://www.python.org/downloads/
    echo.
    echo ※ インストール時に「Add Python to PATH」にチェックを入れてください。
    echo.
    pause
    exit /b 1
)

:: Python バージョン確認
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python %PYVER% が見つかりました
echo.

:: tkinter の存在確認
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] tkinterが利用できません。
    echo Pythonを再インストールし、「tcl/tk and IDLE」を有効にしてください。
    echo.
    pause
    exit /b 1
)

echo セットアップウィザードを起動しています...
echo.

:: インストーラー起動
python "%~dp0scripts\installer.py"

if %errorlevel% neq 0 (
    echo.
    echo [エラー] セットアップ中にエラーが発生しました。
    echo.
    pause
)
