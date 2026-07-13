# Code2Course 打包與分發快速指南

## 三分鐘快速上手

### 1️⃣ 打包可執行檔 (PyInstaller 版，推薦)

```bash
# 一鍵打包 (自動檢查依賴、打包 ffmpeg、生成啟動腳本)
./build_exe.sh

# 輸出在 dist/ 目錄
# 可直接分發給用戶
```

### 2️⃣ 分發給用戶

```bash
# 壓縮打包好的檔案
cd dist
zip -r ../Code2Course_v1.0.zip .
cd ..

# 現在 Code2Course_v1.0.zip 就是可分發的完整包
```

### 3️⃣ 用戶使用流程

**第一次執行** (自動設定)：

```bash
# Mac/Linux
unzip Code2Course_v1.0.zip
./run.sh

# Windows
解壓 Code2Course_v1.0.zip
雙擊 run.bat
```

程式會：

1. ✅ 檢測到首次執行
2. ✅ 自動複製設定檔
3. ✅ 提示輸入 GEMINI_API_KEY (必填) 和 PEXELS_API_KEY (選填)
4. ✅ 保存設定
5. ✅ 啟動主程式

**之後每次執行**：

```bash
./run.sh  # 直接執行，無需再設定
```

---

## 打包過程中可能出現的問題

### ❌ 找不到 ffmpeg

```
⚠️ 系統未找到 ffmpeg，嘗試透過 Homebrew 安裝...
```

**解決方案**：

- Mac: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`
- Windows: 下載自 https://ffmpeg.org/download.html

### ❌ PyInstaller 找不到某個 module

可能的原因是有新增了 Python 依賴，但 `build_exe.sh` 中未列出 hidden import。

**解決方案**：
編輯 `build_exe.sh`，在 `--hidden-import moviepy \` 下方新增：

```bash
--hidden-import your_new_module \
```

### ❌ 打包檔案太大

PyInstaller 版本的可執行檔通常 300-400MB，虛擬環境版本約 200-300MB。

**建議**：

- 用 ZIP 格式壓縮可減少 30-50% 大小
- 分發 ZIP 而不是直接分發目錄

---

## 驗證打包結果

### 測試可執行檔是否正常

```bash
# 測試可執行檔能否啟動 (需要設定檔)
cd dist

# Mac/Linux
./code2course --help  # 若有 help 選項

# Windows
code2course.exe  # 應該能顯示選單

# 或執行啟動腳本
./run.sh  # Mac/Linux
run.bat   # Windows
```

---

## 選擇打包方式

| 需求                | 推薦方案        | 理由                       |
| ------------------- | --------------- | -------------------------- |
| 分發給非技術用戶    | PyInstaller     | 一個檔案，無需安裝任何東西 |
| 給公司/團隊內部使用 | PyInstaller     | 最簡單的使用體驗           |
| GitHub Release 發布 | PyInstaller ZIP | 檔案較小，下載快           |
| 給開發者            | 虛擬環境 ZIP    | 可自由修改原始碼           |
| 雲端部署 (Docker)   | 虛擬環境        | Docker 可輕鬆整合          |

---

## 完整流程範例

```bash
# 步驟 1: 打包
./build_exe.sh

# 步驟 2: 測試
cd dist
./run.sh  # 測試啟動腳本是否正常
cd ..

# 步驟 3: 壓縮
cd dist
zip -r ../Code2Course_v1.0.zip .
cd ..

# 步驟 4: 上傳分發
# 上傳 Code2Course_v1.0.zip 到 GitHub Release / 網站

# 步驟 5: 告知用戶
# 下載、解壓、執行 run.sh (或 run.bat)
```

---

## 用戶常見問題

### Q: 為什麼檔案這麼大？

**A:** 包含了完整的 Python 環境 + 所有依賴 + ffmpeg，確保「完全無依賴」使用。

### Q: 能不能用 VPN？

**A:** 取決於 Gemini / Pexels API 在你地區是否可用。網路設定在 `code2course_config.json` 中。

### Q: 如何更新到新版本？

**A:** 重新下載新的 ZIP 包，使用新的可執行檔。舊的 `code2course_config.json` 會保留。

### Q: 能在 Linux 伺服器上執行嗎？

**A:** 可以。同時提供 Mac/Linux 和 Windows 版本的可執行檔。
