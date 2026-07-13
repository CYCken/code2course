@echo off
chcp 65001 >nul
title Code2Course Windows 啟動器

echo === 啟動 Code2Course (Windows) ===

cd /d "%~dp0"

REM 啟動虛擬環境 (假設已預先安裝)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ 已啟動虛擬環境
) else (
    echo ❌ 找不到虛擬環境，請確認 venv 已正確安裝
    pause
    exit /b 1
)

REM 執行設定腳本
echo 🔧 檢查設定檔...
python setup.py

REM 執行主程式
echo 🚀 啟動主程式...
python main.py --config code2course_config.json %*

echo ✅ 執行完成！
pause