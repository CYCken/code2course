# Code2Course 可分發包準備指南

## 選項 1: PyInstaller 單一可執行檔案 (推薦) ⭐

### 優點

- ✅ **真正的單一檔案** - 無需安裝 Python
- ✅ **跨平台** - Mac/Linux/Windows 通用
- ✅ **自包含** - 包含所有 Python library 與 ffmpeg
- ✅ **零設定** - 用戶只需點擊執行
- ✅ **最簡單** - 對非技術用戶友好

### 打包步驟

1. **確保系統有 ffmpeg**

   ```bash
   # Mac (使用 Homebrew)
   brew install ffmpeg

   # Linux
   sudo apt-get install ffmpeg
   ```

2. **執行打包腳本**

   ```bash
   chmod +x build_exe.sh
   ./build_exe.sh
   ```

   腳本會自動：
   - 安裝 PyInstaller
   - 驗證 ffmpeg 存在
   - 包含所有 hidden imports (MoviePy, imageio, numpy 等)
   - 打包 ffmpeg 二進位檔
   - 建立啟動腳本

3. **輸出結果**
   - `dist/code2course` (或 `code2course.exe` on Windows)
   - `dist/run.sh` (Mac/Linux 啟動腳本)
   - `dist/run.bat` (Windows 啟動腳本)
   - `dist/code2course_config.example.json`

4. **壓縮分發**
   ```bash
   # 只壓縮 dist 目錄中的內容
   cd dist
   zip -r ../Code2Course_dist.zip .
   cd ..
   ```

### 用戶使用方式

**Mac/Linux**

```bash
unzip Code2Course_dist.zip
./run.sh
```

**Windows**

```
解壓 Code2Course_dist.zip
雙擊 run.bat
```

程式會自動：

1. 檢查設定檔
2. 首次執行時提示輸入 API 金鑰
3. 保存設定
4. 啟動主程式

---

## 選項 2: 虛擬環境包 (開發者友好)

### 優點

- ✅ 較小的檔案大小
- ✅ 易於源碼修改與測試
- ✅ 透明的依賴管理
- ⚠️ **但需要用戶手動裝 ffmpeg**

### 準備步驟

1. **複製整個 code2course 資料夾**

   ```bash
   cp -r code2course Code2Course_Dist
   ```

2. **建立虛擬環境並安裝依賴**

   ```bash
   cd Code2Course_Dist
   python3 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # 或 Windows: venv\Scripts\activate
   pip install -r requirements.txt
   deactivate
   ```

3. **清理不需要的檔案** (可選)

   ```bash
   rm -rf .git __pycache__ .DS_Store .pytest_cache
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -delete
   ```

4. **壓縮分發**
   ```bash
   zip -r Code2Course_venv.zip Code2Course_Dist/
   ```

### 使用方式

**Mac 用戶**

```bash
unzip Code2Course_venv.zip
cd Code2Course_Dist
./run_mac.command
```

**Windows 用戶**

```
解壓 Code2Course_venv.zip
進入 Code2Course_Dist 資料夾
雙擊 run_windows.bat
```

**重要：用戶需要自行安裝 ffmpeg**

- Mac: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`
- Windows: 下載自 https://ffmpeg.org/download.html

---

## 對比表

| 特性        | PyInstaller 版    | 虛擬環境版        |
| ----------- | ----------------- | ----------------- |
| 文件大小    | 較大 (~300-400MB) | 中等 (~200-300MB) |
| 用戶易用性  | ⭐⭐⭐⭐⭐        | ⭐⭐⭐            |
| Python 依賴 | 包含              | 包含              |
| ffmpeg      | 包含              | ❌ 需用戶裝       |
| 修改源碼    | ❌ 困難           | ✅ 容易           |
| 跨平台      | ✅ (需個別編譯)   | ✅ 同平台通用     |
| 推薦用途    | 終端用戶分發      | 開發者 / 測試     |

---

## 常見問題

### Q: PyInstaller 打包後仍需要 Python 嗎？

**A:** 不需要。可執行檔包含了 Python 直譯器和所有相依套件。

### Q: ffmpeg 會被打進 exe 嗎？

**A:** 會的。`build_exe.sh` 會自動偵測系統 ffmpeg 位置並打包進去。

### Q: 虛擬環境包如果用戶沒有裝 ffmpeg 會怎樣？

**A:** 在執行到影片合成階段時會出錯。你需要在文件中清楚提醒用戶安裝。

### Q: 可以只分發 venv 而不分發源碼嗎？

**A:** 可以，但 Python 虛擬環境只能用於建立它的同一平台。不能跨平台。

### Q: 如何更新已分發的版本？

**A:**

- PyInstaller 版：重新執行 `build_exe.sh` 並重新分發
- 虛擬環境版：用戶可在虛擬環境中執行 `pip install --upgrade -r requirements.txt`

---

## 建議分發流程

1. **選擇 PyInstaller 版本** (最終用戶最佳體驗)
2. 執行 `./build_exe.sh` 測試打包
3. 測試生成的可執行檔
4. 建立一份 README 說明 API 金鑰取得方式
5. 壓縮 `dist/` 目錄為 ZIP
6. 上傳到 GitHub Release / 網站供下載
