# Code2Course (教學影片生成庫)

這是一個強大的本地端自動化工具。它可以將你指定的軟韌體專案原始碼（C / Python / Markdown 等），透過讀取設定檔與客製化教學 Prompt，交由 Gemini API 自動分析並梳理出結構化的大綱，再利用 `python-pptx` 生成投影片，最終經由 `edge-tts` 與 `MoviePy` 合成為「帶有語音解說的教學影片」 (MP4)。

## 🎯 專案目錄結構

這是一個模組化、注重設定與原始碼分離的 Library 專案。請將所有設定檔放置在外層目錄，產出的資料也會存放在外層的 `outputs/`，以確保核心函式庫乾淨無污染。

### 📦 安裝與配置方式

### 📦 安裝與配置方式

想要將 **Code2Course** 引入您的任何專案，有兩種最主流的方式：

**選項 A：使用 Git Submodule (強烈推薦，方便未來更新這套工具)**

```bash
git submodule add https://github.com/CYCken/code2course.git code2course
```

**選項 B：直接 Clone 為一般資料夾**

```bash
git clone https://github.com/CYCken/code2course.git code2course
```

**後續設定步驟**：

1. 將剛才拉進來的 `code2course/` 裡面的 `run.sh` 複製一份到**外層的專案根目錄**。
2. 將 `code2course/code2course_config.example.json` 複製一份到外層，並重新命名為 `code2course_config.json`。
3. 打開 `code2course_config.json`，填入您的 `GEMINI_API_KEY`。

```text
your_project/ (根目錄)
├── code2course_config.json    <-- 全域設定檔（填寫 API Key、副檔名與指定資料夾）
├── code2course_prompt.txt     <-- Gemini 生成樣板（執行第一次後會自動產生，可自由改寫）
├── run.sh                     <-- 自動啟動腳本 (Mac/Linux 一鍵執行)
├── README.md                  <-- 本說明檔
├── outputs/                   <-- 所有生成的教材 PPT 與影片產出都會統一整理在這
└── code2course/               <-- 核心程式碼資料夾 (請勿隨意更動)
    ├── main.py
    └── requirements.txt
```

---

## 🚀 快速啟動 (One-click Run)

你**不再需要**手動建立 `venv` 或敲擊繁瑣的 `pip` 指令了！
開啟終端機 (Terminal) 並進入此目錄 (根目錄) 後，直接執行：

```bash
sh run.sh
```

這隻腳本會一次幫你自動完成：

1. 建立並啟用 Python 虛擬環境 (`venv`)
2. 檢查並安裝必要的相依套件 (`requirements.txt`)
3. 執行主程式 `main.py`
4. 結束後安全關閉虛擬環境

---

## ⚙️ 設定檔說明 (`code2course_config.json`)

此設定檔掌控了整個生成器的運作邏輯。格式如下：

```json
{
  "GEMINI_API_KEY": "",
  "supported_exts": [".md", ".c", ".py", ".cpp", ".h"],
  "exclude_dirs": ["drivers", "rte", "cmsis", "build", "node_modules", "lib"],
  "target_folder": ""
}
```

- **`GEMINI_API_KEY`**: 必填！請填入您的 Google API Key (優先權高於 `code2course/.env` 檔案)。
- **`supported_exts`**: 指定要讀取哪些副檔名的程式碼來分析。
- **`exclude_dirs`**: 這些字眼的資料夾將會被完全略過。避免像 `drivers` 或 `node_modules` 這種龐大的底層函式庫耗盡你的 API Token 額度。
- **`target_folder`**:
  - 若你想**跳過上下鍵的終端互動選單**，請在此填寫目標資料夾名稱（例如 `"Discovery-F4"`）。
  - 若留空 `""`，程式將自動啟動漂亮互動選單，讓你在終端機使用鍵盤上下挑選專案。

---

## 🧑‍🏫 自訂名師口吻 (`code2course_prompt.txt`)

執行第一次主程式 (或 `sh run.sh`) 後，系統若偵測不到樣板檔案，會在根目錄自動幫你產生一份**「預設的 `code2course_prompt.txt`」**。

這個純文字檔案包含了傳給 Gemini API 的所有 Prompt 指令方針。你可以：

- 自由修改老師的授課口吻 (例如要求「用幼稚園聽得懂的話講解」或「全英文授課」)。
- 調整四大微課程框架 (原為 Scope, Why, How, What)。
- 要求它專注於特定的硬體元件解析。

主程式每次執行時都會即時讀取這個 `.txt` 檔，因此你所有的打磨與測試都在外面進行，無需去修改 `main.py`。
請注意：自訂樣板時，必須保留文件最下方的 `{merged_text}` 標籤，程式才能把專案原始碼成功注入！

### 💡 魔改秘技：控制投影片數量
如果您的專案極度龐大，導致 AI 過度鑽牛角尖跑出四五十頁超長簡報，您可以直接把「總頁數限制指令」貼進 `code2course_prompt.txt` 裡面。

**建議放置位置與貼上範例：**
請將這段話加在「這份專案內含多個可能看似不相關的技術區塊...」的規則段落中，緊跟著您的邏輯主軸底下：

```text
進入每個觀念的教學細節時，請在心中默默遵循這四個邏輯主軸來分析：
- (Scope) 這是什麼核心功能？
- (Why do) 為何需要它？解決了什麼痛點或是工程難題？
- (How do) 運作邏輯是什麼？(善用生動的比喻或 Emoji 帶出畫面感)
- (What do) 程式碼具體達成了什麼？

👉 [進階控制]：請將相似的模組概念進行分類與合併，不要過度刁鑽於每一個微小檔案。請將最終輸出的投影片總數嚴格控制在 15 到 20 張以內，只講述最精華、最核心的系統脈絡。

輸出的格式必須是純 JSON 陣列 (Array) 結構...
```
只要加上這句話，Gemini 就會乖乖幫您把幾十個檔案濃縮成最精華的 15 頁大綱了！

---

## 🕹️ 斷點接關與多模式執行 (Multi-mode CLI)

程式現在支援 **4 種互動模式**，讓您不必每次修改一點 Prompt 就要重新等待掃描與生成：

- **`[0] 完整流程`**：最懶人的做法，從掃描到產出影片一次搞定。
- **`[1] 僅掃描專案 (產出 Prompt)`**：純粹把程式碼爬出來，組合成 `gemini_prompt_record.txt`。適合拿來手動檢查組合後的原始碼片段。
- **`[2] 僅 AI 處理 (讀取 Prompt 產出 PPT 與 JSON)`**：程式會尋找您「過去的掃描歷史 (`outputs/`)」，直接拿現成的 Prompt 去敲 Gemini，省去重掃的時間。如果您去微調了 txt 檔，只要跑這個階段就能立刻看新的 PPT 腳本是否有改善！
- **`[3] 僅合成影音 (讀取 JSON 產出影片)`**：程式會讀取 AI 已經生好的 `.json` 分鏡檔，專注於產生 `edge-tts` 語音跟渲染最終的 MP4 影片。

> **💡 接關設計**：當您選擇 [2] 或 [3] 時，系統會自動展開漂亮的終端機選單，讓您從 `outputs/` 資料夾裡的歷史時間紀錄中，選擇要接關的專案！

---

## 🤖 結合 GitHub Actions 打造全自動 CI/CD

您可以輕鬆地把這套教材產生器掛載到 GitHub，當任何開發者 Push 程式碼時，就自動在雲端產生一部最新教學影片！

只要在您的主專案資料夾建立 `.github/workflows/code2course_gen.yml`，貼上以下腳本：

```yaml
name: Code2Course Generator

on:
  push:
    branches:
      - main
  workflow_dispatch:
    inputs:
      target_folder:
        description: "要掃描的專案資料夾 (例如: Discovery-F4)"
        required: false
        default: "Discovery-F4"

jobs:
  build_materials:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      # 💡 提示：如果您把 code2course 抽離成獨立的 GitHub Repo
      # 您只需要解開下面這段的註解，Action 執行時就會自動把它抓下來用！
      # - name: Download Code2Course (External Library)
      #   uses: actions/checkout@v4
      #   with:
      #     repository: CYCken/code2course
      #     path: code2course

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install System Dependencies (FFmpeg & CJK Fonts)
        run: |
          sudo apt-get update
          # 安裝影像處理套件與中文字型，防止影片渲染出豆腐塊亂碼
          sudo apt-get install -y ffmpeg fonts-noto-cjk fonts-wqy-microhei

      - name: Install Python Dependencies
        run: |
          cd code2course
          pip install -r requirements.txt

      - name: Configure Headless Mode
        # 確保不會觸發終端機互動 UI 以免卡死
        run: |
          TARGET="${{ github.event.inputs.target_folder }}"
          # 如果是 push 進 main 分支，預設抓 Discovery-F4
          if [ -z "$TARGET" ]; then
              TARGET="Discovery-F4"
          fi

          # 將 target_folder 強制寫入 JSON config 中
          python3 -c "import json; f=open('code2course_config.json'); c=json.load(f); f.close(); c['target_folder']='$TARGET'; f=open('code2course_config.json','w'); json.dump(c,f); f.close()"

      - name: Run Code2Course Generator
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          AUTO_MODE: "0" # 告訴主程式這是在 CI 執行 Mode 0 (完整流程)
        run: |
          cd code2course
          python main.py

      - name: Upload Generated Output (Artifacts)
        uses: actions/upload-artifact@v4
        with:
          name: Code2Course-Materials-${{ github.sha }}
          path: outputs/
          retention-days: 14
```

> ⚠️ 請記得去 GitHub 專案的 `Settings` -> `Secrets and variables` -> `Actions` 新增一個名為 `GEMINI_API_KEY` 的 Secret，才不會暴露您的密碼！
