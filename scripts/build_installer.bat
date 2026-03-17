@echo off
chcp 65001 >nul
title インストーラービルド

echo.
echo  ╔══════════════════════════════════════╗
echo  ║  インストーラー .exe ビルド           ║
echo  ╚══════════════════════════════════════╝
echo.
echo ※ このスクリプトはWindows環境で実行してください。
echo ※ PyInstallerが必要です。
echo.

:: PyInstaller 確認・インストール
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstallerをインストールしています...
    pip install pyinstaller
    echo.
)

echo ビルドを開始します...
echo.

:: ビルド実行
pyinstaller --onefile --windowed ^
    --name "Excel同期セットアップ" ^
    --add-data "../src;src" ^
    --add-data "../config;config" ^
    --add-data "../requirements.txt;." ^
    --add-data "../pyproject.toml;." ^
    --add-data "../scripts/initial_setup.py;scripts" ^
    installer.py

if %errorlevel% equ 0 (
    echo.
    echo ======================================
    echo  ビルド成功！
    echo  出力先: dist\Excel同期セットアップ.exe
    echo ======================================
) else (
    echo.
    echo [エラー] ビルドに失敗しました。
)

echo.
pause
