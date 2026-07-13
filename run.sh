#!/bin/bash
cd "$(dirname "$0")"

# 直接執行程式 (設定檢查已整合到主程式中)
if [ -x "./dist/code2course" ]; then
    ./dist/code2course "$@"
elif [ -x "./code2course" ]; then
    # 開發環境或舊版本
    ./code2course "$@"
else
    echo "❌ 找不到可執行檔 code2course"
    exit 1
fi
