# Code2Course (教學影片生成庫)

這是一個強大的本地端自動化工具。它可以將你指定的軟韌體專案原始碼（C / Python / Markdown 等），透過讀取設定檔與客製化教學 Prompt，交由 Gemini API 自動分析並梳理出結構化的大綱，再利用 `python-pptx` 生成投影片，最終經由 `edge-tts` 與 `MoviePy` 合成為「帶有語音解說的教學影片」 (MP4)。

---

## 🎯 專案理念：模組化與專業化

Code2Course 已全面升級為**五階段模組化架構**。您可以一次跑完所有流程，也可以針對特定階段進行細粒度調整與重複執行，不再需要為了修改一個錯字而重新跑完耗時的 AI 分析或素材下載。

---

## 📦 安裝與配置方式

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
├── code2course_config.json    <-- 全域設定檔（填寫 API Key、工具開關、指定資料夾）
├── code2course_style.json     <-- 風格設定檔（PPT 與影片的字型、顏色、遮罩與邊距）
├── code2course_prompt.txt     <-- Gemini 生成樣板（執行第一次後會自動產生）
├── run.sh                     <-- 自動啟動腳本 (Mac/Linux 一鍵執行)
├── outputs/                   <-- 所有產出的教材 PPT 與影片產出
└── code2course/               <-- 核心程式碼資料夾
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

## 🕹️ 五階段運轉與「接力執行」模式

Code2Course 現已支援 **5 種獨立接關模式**，並具備 **智慧接力 (Stage Chaining)** 功能：

### 1. 五大獨立階段 (與子階段)
- **`[0] 完整流程`**：最懶人的做法，從掃描到產出影片一次搞定 (1->2->2-1->3->4->5)。
- **`[1] 掃描專案`**：爬取原始碼，產出 `gemini_prompt_record.txt`。
- **`[2] AI 核心分析`**：獲取課程大綱與講稿。採兩階段設計，大幅提升大型專案穩定性。
- **`[2-1] 媒體增強`**：**（NEW!）** 基於現有分析結果生成 InVideo/Remotion 分鏡。免重跑分析，開發必備。
- **`[3] 下載素材`**：從 Pexels 下載相關的背景圖片與影片。
- **`[4] 產生 PPT`**：利用 `python-pptx` 渲染出專業投影片。
- **`[5] 合成影音`**：進行 `edge-tts` 與 `MoviePy` 影片合成。

### 2. 智慧接力 (Stage Chaining)
當您執行完任一個「獨立階段」後，系統會詢問：**「是否接續執行下一個階段？」**。
- 如果選擇「是」，系統會**自動帶著目前的進度**直接進入下一關，不需要重新選取歷史資料夾。這讓您可以分段檢查結果，滿意後再一鍵推進。

---

## ⚙️ 核心功能優化

### 🖼️ 細粒度素材管理 (Stage 3 優化)
在重新抓取素材時，您現在有三個選擇：
- **跳過已存在**：僅補齊漏掉的圖片。
- **全部重新下載**：強制刷新所有頁面的素材。
- **手動選擇特定投影片**：系統會列出所有投影片標題，讓您**只勾選**想要換掉的那幾頁。

> **💡 自動隨機化**：為了避免重複抓到相同的圖，只要是「重新抓取」或「手動勾選」的頁面，系統會自動在 Pexels 搜尋結果中**隨機跳頁**，確保您每次都能拿到不同的驚喜！

### 🎥 影片可讀性強化 (Stage 5 優化)
- **內文遮罩 (Card Mask)**：比照 PPT 設計，在影片文字後方加入了 50% 透明度的深色遮罩塊，確保即使背景圖片很花，文字依然絕對清晰。
- **統一化底色**：當該頁沒有背景圖時，系統會自動隱藏遮罩框，讓畫面呈現簡潔統一的底色。

### 🤖 兩階段 AI 分析引擎 (Stage 2 & 2-1)
為了應對大規模專案（如 30 頁以上），系統將分析流程拆解為：
1. **Pass 1 (核心內容)**：專注於邏輯、講稿、Marp 結構，產出穩定的 Core JSON。
2. **Pass 2 (媒體增強)**：根據 Core JSON 內容，批次產出 `invideo_scene` 與 `remotion_data`。
- **解耦輸出**：現在會自動產出專屬的 `{project}_invideo.json` 與 `remotion_data.json`，不再污染核心分析檔。
- **故障恢復**：若增強過程失敗，可直接啟動 **[2-1] 階段** 進行補救，無需重新進行耗時的核心分析。

---

## ⚙️ 設定檔說明 (`code2course_config.json`)

此設定檔掌控了整個生成器的運作邏輯。格式如下：

```json
{
  "GEMINI_API_KEY": "",
  "PEXELS_API_KEY": "",
  "gemini_model": "gemini-2.5-flash",
  "enable_invideo": false,
  "enable_remotion": false,
  "supported_exts": [".md", ".c", ".py", ".cpp", ".h"],
  "exclude_dirs": ["drivers", "rte", "cmsis", "build", "node_modules", "lib"],
  "target_folder": "",
  "max_chars": 300000
}
```

- **`GEMINI_API_KEY`**: 必填！Gemini API 金鑰。
- **`PEXELS_API_KEY`**: (選填) Pexels API 金鑰。
- **`gemini_model`**: (選填) 指定使用的模型名稱。建議使用 `gemini-2.5-flash` (速度快) 或 `gemini-2.5-pro` (邏輯更強)。
- **`enable_invideo` / `enable_remotion`**: 是否要產出給 InVideo 或 Remotion 使用的專屬 JSON 與腳本檔案。
- **`supported_exts`**: 指定要讀取哪些副檔名的程式碼來分析。
- **`exclude_dirs`**: 資料夾排除清單。
- **`target_folder`**: 指定掃描目標資料夾，留空則開啟互動選單。
- **`max_chars`**: (選填) 單次掃描的最大字元數上限。預設為 `300000` (約 30 萬字元)，超過後會停止讀取細節檔案，以節省 API Token 並防止 context window 超載。

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

## 🎨 風格控制 (`code2course_style.json`)

這套工具現在支援百分之百的視覺客製化！您可以透過外層的 `code2course_style.json` (參考 `code2course_style.example.json`) 來調整：

- **字體大小**: 針對不同長度的標題與內文設定字級。
- **色彩系統**: 自訂背景色 (RGB) 與文字顏色。
- **遮罩 (Mask)**: 針對文字內容塊設定半透明遮罩的顏色與透明度 (Alpha)，確保在背景圖上清晰閱讀。
- **邊距**: 微調標題與內文的起始位置與間距。
- **影片風格**: 新增 `video_` 開頭的參數，可調整影片背景變暗程度、橫幅顏色、文字遮罩透明度與字體大小。

---

## 🖼️ 素材來源標註

為了尊重版權並方便追蹤素材，Code2Course 會在產生投影片時：
1. 自動收集所有從 Pexels 下載的圖片攝影師資訊。
2. 在 PPT 簡報的最後一頁**自動生成「References & Attributions」頁面**，列出所有使用的圖片來源。

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
          PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
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
