#!/bin/bash
# 自動化教材生成工具啟動腳本

echo "=== 準備啟動自動化教材生成工具 ==="

# 先進入腳本所在的目錄，確保路徑正確
cd "$(dirname "$0")" || exit 1

# 進入 code2course 目錄
cd code2course || { echo "❌ 找不到 code2course 目錄，請確認您在專案根目錄執行"; exit 1; }

# 檢查是否已建立虛擬環境
if [ ! -d "venv" ]; then
    echo "1. 發現尚未建立虛擬環境，正在自動建立中..."
    python3 -m venv venv
else
    echo "1. 虛擬環境 (venv) 已準備就緒。"
fi

# 啟動虛擬環境 (支援 macOS/Linux)
echo "2. 啟動虛擬環境..."
source venv/bin/activate

# 安裝所需套件 (安靜模式)
echo "3. 檢查並更新套件依賴 (pip install -r requirements.txt)..."
pip install -r requirements.txt -q

# 執行主程式
echo "4. 啟動核心程式 main.py"
echo "-----------------------------------"
python main.py
echo "-----------------------------------"

# 執行完畢後離開虛擬環境
deactivate
echo "✅ 執行結束！產出檔案請至 outputs/ 資料夾查看。"
