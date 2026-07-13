#!/bin/bash
# PyInstaller 打包腳本 for Code2Course
# 支援 Mac 和 Linux，包含 ffmpeg 二進位檔打包

set -e

echo "=== Code2Course PyInstaller 打包腳本 ==="

# 檢查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 找不到 python3，請先安裝 Python 3"
    exit 1
fi

# 建立專用的打包虛擬環境 (避免污染全域環境)
VENV_DIR=".pyinstaller_venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "1️⃣ 建立專用打包虛擬環境..."
    python3 -m venv "$VENV_DIR"
fi

# 啟動虛擬環境
echo "2️⃣ 啟動打包虛擬環境..."
source "$VENV_DIR/bin/activate"

# 在虛擬環境中安裝 PyInstaller 和所有依賴
echo "3️⃣ 安裝 PyInstaller 和依賴..."
pip install -q pyinstaller
pip install -q -r requirements.txt

# 檢查 ffmpeg 是否已安裝
echo "4️⃣ 檢查 ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ 系統未找到 ffmpeg，嘗試透過 Homebrew 安裝 (Mac)..."
    if command -v brew &> /dev/null; then
        brew install -q ffmpeg
    else
        echo "❌ 無法自動安裝 ffmpeg"
        echo "   Mac 用戶請執行: brew install ffmpeg"
        echo "   Linux 用戶請執行: sudo apt-get install ffmpeg"
        exit 1
    fi
fi

FFMPEG_PATH=$(which ffmpeg)
echo "✅ 找到 ffmpeg: $FFMPEG_PATH"

# 建立輸出目錄
mkdir -p dist

# 清理舊的打包檔案
rm -rf build dist/code2course dist/code2course.exe

echo ""
echo "3️⃣ 開始 PyInstaller 打包 main.py..."

echo "🔨 開始編譯可執行檔..."
# 在虛擬環境中運行 PyInstaller
source "$VENV_DIR/bin/activate"
pyinstaller --onefile \
    --console \
    --name code2course \
    --add-data "code2course_config.example.json:." \
    --add-data "code2course_style.example.json:." \
    --add-data "code2course_prompt.example.txt:." \
    --add-binary "$FFMPEG_PATH:." \
    --hidden-import google.generativeai \
    --hidden-import questionary \
    --hidden-import python_pptx \
    --hidden-import moviepy \
    --hidden-import moviepy.editor \
    --hidden-import imageio \
    --hidden-import imageio_ffmpeg \
    --hidden-import numpy \
    --hidden-import decorator \
    --hidden-import requests \
    --hidden-import urllib3 \
    --hidden-import certifi \
    --hidden-import charset_normalizer \
    --hidden-import idna \
    --hidden-import PIL \
    --hidden-import pillow \
    --hidden-import websockets \
    --hidden-import aiohttp \
    --hidden-import python_dotenv \
    --hidden-import pydub \
    --collect-all moviepy \
    --collect-all edge_tts \
    --collect-all imageio \
    --collect-all python_dotenv \
    main.py

# 複製必要檔案到輸出目錄
echo ""
echo "4️⃣ 複製設定檔案..."
cp code2course_config.example.json dist/code2course_config.json
cp code2course_style.example.json dist/code2course_style.json

# 建立啟動腳本
echo "5️⃣ 建立啟動腳本..."

cat > dist/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# 直接執行程式 (設定檢查已整合到主程式中)
if [ -x "./code2course" ]; then
    ./code2course "$@"
else
    echo "❌ 找不到可執行檔 code2course"
    exit 1
fi
EOF

cat > dist/run.bat << 'EOF'
@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === Code2Course Runner ===

set "EXE_NAME=code2course.exe"
set "EXE_PATH=%~dp0%EXE_NAME%"

if not exist "%EXE_PATH%" (
    set "EXE_NAME=code2course"
    set "EXE_PATH=%~dp0code2course"
)

if exist "%EXE_PATH%" (
    echo [OK] Found executable: %EXE_NAME%
    echo [RUN] Starting program...
    "%EXE_PATH%" %*
) else (
    echo [ERROR] Could not find executable: code2course.exe or code2course
    echo Please make sure you are running this from the extracted dist folder.
    pause
    exit /b 1
)

pause
EOF

python3 - <<'PY'
from pathlib import Path
p = Path('dist/run.bat')
text = p.read_text()
p.write_text(text.replace('\n', '\r\n'), encoding='utf-8')
PY

chmod +x dist/run.sh

# 退出虛擬環境並清理
deactivate
echo ""
echo "🧹 清理打包虛擬環境..."
rm -rf "$VENV_DIR"

echo ""
echo "✅ 打包完成！"
echo ""
echo "📦 產出檔案位置："
if [ -f "dist/code2course" ]; then
    echo "  ✓ Mac/Linux 可執行檔: dist/code2course"
    echo "  ✓ 啟動腳本: dist/run.sh"
fi
echo "  ✓ 設定範例: dist/code2course_config.example.json"
echo ""
echo "🚀 使用方式："
echo "  Mac/Linux: ./dist/run.sh"
echo "  Windows: dist\\run.bat"
echo ""
echo "💡 首次執行會自動建立 code2course_config.json，請填入 API 金鑰"
