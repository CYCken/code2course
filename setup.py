#!/usr/bin/env python3
"""
Code2Course 設定與啟動腳本
負責初始化設定檔並提示用戶輸入必要的 API 金鑰
"""

import os
import json
import shutil
import sys

def setup_config(config_file="code2course_config.json", config_example="code2course_config.example.json"):
    """設定 code2course_config.json"""
    
    # 如果設定檔不存在，複製範例
    if not os.path.exists(config_file):
        if os.path.exists(config_example):
            shutil.copy2(config_example, config_file)
            print(f"✅ 已複製設定檔：{config_file}")
        else:
            print(f"❌ 找不到範例設定檔：{config_example}")
            return False

    # 讀取設定檔
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 讀取設定檔失敗：{e}")
        return False

    # 檢查並提示輸入 API 金鑰
    updated = False

    print("\n" + "=" * 50)
    print("🔑 Code2Course API 金鑰設定")
    print("=" * 50)

    if not config.get("GEMINI_API_KEY", "").strip():
        print("\n[必填] Gemini API 金鑰")
        print("來源：https://aistudio.google.com/app/apikey")
        print("說明：用於 AI 分析與課程大綱生成")
        gemini_key = input("\n輸入 GEMINI_API_KEY (按 Enter 跳過): ").strip()
        if gemini_key:
            config["GEMINI_API_KEY"] = gemini_key
            updated = True
            print("✅ 已設定")
        else:
            print("⚠️  未設定 Gemini API 金鑰，某些功能將無法使用")
    else:
        print("\n✅ Gemini API 金鑰已設定")

    if not config.get("PEXELS_API_KEY", "").strip():
        print("\n[選填] Pexels API 金鑰")
        print("來源：https://www.pexels.com/api/")
        print("說明：用於下載背景圖片與影片")
        pexels_key = input("\n輸入 PEXELS_API_KEY (按 Enter 跳過): ").strip()
        if pexels_key:
            config["PEXELS_API_KEY"] = pexels_key
            updated = True
            print("✅ 已設定")
        else:
            print("⏭️  跳過 (稍後可手動編輯)")
    else:
        print("\n✅ Pexels API 金鑰已設定")

    # 寫回設定檔
    if updated:
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 設定檔已更新：{config_file}")
        except Exception as e:
            print(f"❌ 寫入設定檔失敗：{e}")
            return False
    
    print("\n" + "=" * 50)
    return True

def check_dependencies():
    """檢查是否有必要的系統工具"""
    import subprocess
    
    # 檢查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        print("✅ ffmpeg 已安裝")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  找不到 ffmpeg，影片合成功能將無法使用")
        print("   Mac: brew install ffmpeg")
        print("   Linux: sudo apt-get install ffmpeg")
        return False

if __name__ == "__main__":
    print("=== Code2Course 初始化設定 ===\n")
    
    # 檢查依賴
    check_dependencies()
    
    # 設定 API 金鑰
    if setup_config():
        print("\n✅ 初始化完成！準備啟動主程式...\n")
        sys.exit(0)
    else:
        print("\n❌ 初始化失敗")
        input("按 Enter 鍵繼續...")  # Windows 相容
        sys.exit(1)
