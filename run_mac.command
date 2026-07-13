#!/bin/bash
# Code2Course Mac 啟動腳本
# 用法：雙擊此檔案或在終端機執行 ./run_mac.command

set -e

echo "=== 啟動 Code2Course (Mac) ==="

# 進入腳本所在目錄
cd "$(dirname "$0")"

# 啟動虛擬環境 (假設已預先安裝)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 已啟動虛擬環境"
else
    echo "❌ 找不到虛擬環境，請確認 venv 已正確安裝"
    exit 1
fi

# 執行設定腳本
echo "🔧 檢查設定檔..."
python3 setup.py

# 執行主程式
echo "🚀 啟動主程式..."
python3 main.py --config code2course_config.json "$@"

echo "✅ 執行完成！"