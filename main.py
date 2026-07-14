import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# 處理 dotenv 導入 (PyInstaller 相容性)
# 使用 getattr 檢查是否能 import dotenv
dotenv_module = None
try:
    import dotenv
    dotenv_module = dotenv
except ImportError:
    pass

# 使用 getattr 取得 load_dotenv 函數
if dotenv_module and hasattr(dotenv_module, 'load_dotenv'):
    load_dotenv = dotenv_module.load_dotenv
else:
    # 如果 dotenv 不可用，使用 fallback (可執行檔可能缺少 dotenv)
    def load_dotenv(dotenv_path=None, stream=None, verbose=False, override=False, interpolate=True, encoding='utf-8'):
        """Fallback load_dotenv 當 python-dotenv 不可用時"""
        import os
        env_file = dotenv_path or '.env'
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r', encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if override or key not in os.environ:
                                os.environ[key.strip()] = value.strip()
            except Exception:
                pass

# 匯入模組化後的核心產生器
from engine import Code2Course
from utils.project_selection import get_selectable_project_folders, resolve_analysis_target_path, select_analysis_path

# 載入環境變數 (例如 Gemini API Key)
load_dotenv()

# =========================================================
# 選單與流程控制器 (CLI Runner)
# =========================================================

def _get_target_folders(root_dir, current_app_dir=None):
    return get_selectable_project_folders(
        root_dir,
        current_app_dir=current_app_dir,
        include_all=True,
    )

def select_history_stage_dir(root_dir):
    """用於各階段接關，從 outputs 選出前人留下的 scope 與 time 資料夾進度"""
    import questionary
    outputs_dir = os.path.join(root_dir, "outputs")
    if not os.path.exists(outputs_dir):
        print("📁 找不到 outputs 資料夾，請先執行 階段 1。")
        return None, None
        
    projects = [f for f in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, f))]
    if not projects:
        print(" outputs 內無任何專案歷史，請先執行階段 1。")
        return None, None
    
    selected_project = questionary.select(
        "📂 請選擇要接續處理的專案 (scope folder)：", 
        choices=projects
    ).ask()
    if not selected_project:
        return None, None
    
    project_path = os.path.join(outputs_dir, selected_project)
    timestamps = [f for f in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, f))]
    timestamps.sort(reverse=True) # 近期的放前面
    if not timestamps:
        print(f"專案 {selected_project} 找不到任何歷史時間點資料夾。")
        return None, None
    
    # 如果只有一個時間點，直接自動選取，不跳選單
    if len(timestamps) == 1:
        selected_timestamp = timestamps[0]
        print(f"-> 選取唯一時間點 (time folder): {selected_timestamp}")
    else:
        selected_timestamp = questionary.select(
            "🕒 請選擇要接續執行進度的時間點 (time folder)：", 
            choices=timestamps
        ).ask()
        
    if not selected_timestamp:
        return None, None
    
    return selected_project, selected_timestamp

def _resolve_project_root(app_dir):
    """決定真正的專案根目錄，優先使用外層專案根目錄（若存在設定檔），避免誤用 code2course 自己的設定。"""
    app_dir = os.path.abspath(app_dir or "")
    cwd = os.path.abspath(os.getcwd() or ".")

    def iter_parent_dirs(start_dir):
        current = start_dir
        while True:
            yield current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    def find_config_dir(candidates):
        seen = set()
        ordered = []
        for candidate in candidates:
            if candidate and candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        for candidate in ordered:
            config_path = os.path.join(candidate, 'code2course_config.json')
            if os.path.exists(config_path):
                return candidate, config_path
        return None, None

    # 首先優先檢查與工具目錄同層或其上層的外部專案根目錄。
    if app_dir:
        parent_of_app = os.path.dirname(app_dir)
        parent_candidates = []
        for candidate in iter_parent_dirs(parent_of_app):
            if candidate not in parent_candidates:
                parent_candidates.append(candidate)
        parent_candidates.append(app_dir)
        project_dir, config_path = find_config_dir(parent_candidates)
        if project_dir and project_dir != app_dir:
            return project_dir, config_path

    # 再檢查目前工作目錄與其祖先。
    candidates = []
    for candidate in iter_parent_dirs(cwd):
        if candidate not in candidates:
            candidates.append(candidate)
    if app_dir:
        for candidate in iter_parent_dirs(app_dir):
            if candidate not in candidates:
                candidates.append(candidate)

    project_dir, config_path = find_config_dir(candidates)
    if project_dir:
        return project_dir, config_path

    fallback_dir = cwd if cwd else app_dir
    fallback_config = os.path.join(fallback_dir, 'code2course_config.json') if fallback_dir else None
    return fallback_dir, fallback_config


def check_and_setup_config(config_path, config_example):
    """檢查並設定必要的 API 金鑰"""
    
    # 如果設定檔不存在，複製範例
    if not os.path.exists(config_path):
        if os.path.exists(config_example):
            shutil.copy2(config_example, config_path)
            print(f"✅ 已複製設定檔：{config_path}")
        else:
            print(f"❌ 找不到範例設定檔：{config_example}")
            return {}

    # 讀取設定檔
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 讀取設定檔失敗：{e}")
        return {}

    # 檢查是否需要設定 API 金鑰（只在第一次運行或設定不完整時）
    needs_setup = (
        not config.get("GEMINI_API_KEY", "").strip() or 
        config.get("GEMINI_API_KEY", "").strip() == "YOUR_GEMINI_API_KEY_HERE" or
        config.get("GEMINI_API_KEY", "").strip().startswith("test_")  # 測試用的金鑰也視為需要設定
    )
    
    if needs_setup:
        # 檢查並提示輸入 API 金鑰
        updated = False

        print("\n" + "=" * 50)
        print("🔑 Code2Course API 金鑰設定")
        print("=" * 50)

        print("\n[必填] Gemini API 金鑰")
        print("來源：https://aistudio.google.com/app/apikey")
        print("說明：用於 AI 分析與課程大綱生成")
        
        try:
            gemini_key = input("輸入 GEMINI_API_KEY: ").strip()
            if gemini_key:
                config["GEMINI_API_KEY"] = gemini_key
                updated = True
                print("✅ 已設定")
            else:
                print("⚠️  未設定 Gemini API 金鑰，某些功能將無法使用")
        except (KeyboardInterrupt, EOFError):
            print("\n⚠️  設定取消，未設定 Gemini API 金鑰")

        print("\n[選填] Pexels API 金鑰")
        print("來源：https://www.pexels.com/api/")
        print("說明：用於下載背景圖片與影片")
        
        try:
            pexels_key = input("輸入 PEXELS_API_KEY (可留空): ").strip()
            if pexels_key:
                config["PEXELS_API_KEY"] = pexels_key
                updated = True
                print("✅ 已設定")
            else:
                print("⏭️  跳過 (稍後可手動編輯)")
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  設定取消，跳過 Pexels API 金鑰")

        # 寫回設定檔
        if updated:
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"\n✅ 設定檔已更新：{config_path}")
            except Exception as e:
                print(f"❌ 寫入設定檔失敗：{e}")
    else:
        print("\n✅ API 金鑰已設定 (如需修改請使用設定選項)")
    
    print("\n" + "=" * 50)
    return config

def main():
    print("====== 🤖 Code2Course 教學影片生成工具 (模組化版) ======")
    
    # 判斷執行環境並正確定位檔案目錄
    import sys
    
    # PyInstaller 打包環境：嵌入資源解壓到暫存目錄，但實際應用設定應該在 code2course 目錄
    if hasattr(sys, '_MEIPASS'):
        resource_dir = sys._MEIPASS
        app_dir = os.getcwd()
        print(f"📦 檢測到打包環境，嵌入資源目錄: {resource_dir}")
        print(f"📂 實際應用目錄: {app_dir}")
    else:
        resource_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = resource_dir
        print(f"🔨 開發環境，應用目錄: {app_dir}")
    
    # 後續工作路徑
    config_example = os.path.join(resource_dir, 'code2course_config.example.json')
    root_dir, config_path = _resolve_project_root(app_dir)

    print(f"📂 專案根目錄: {root_dir}")
    print(f"⚙️ 設定檔位置: {config_path}")
    
    # 檢查並設定 API 金鑰
    config = check_and_setup_config(config_path, config_example)
    if not config:
        print("❌ 設定失敗，程式結束")
        return
    
    config['root_dir'] = root_dir
    config['app_dir'] = app_dir

    try:
        import questionary
    except ImportError:
        print("\n缺少 questionary 套件，請先在終端機輸入: pip install -r requirements.txt\n")
        return

    # 要求使用者選擇模式
    mode_choices = [
        questionary.Choice(title="[0] 完整自動化流程 (掃描 -> Gemini 分析 -> 抓取素材 -> 產生簡報 -> 產生影片)", value=0),
        questionary.Choice(title="[1] 獨立階段 1：純粹掃描專案，產生 Prompt 檔 (供您手動微調)", value=1),
        questionary.Choice(title="[2] 獨立階段 2：讀取 Prompt，送交 Gemini 產生 PPT 與 Json 腳本", value=2),
        questionary.Choice(title="[2-1] 獨立階段 2-1：基於現有分析結果生成多媒體專屬資料 (InVideo/Remotion)", value=2.1),
        questionary.Choice(title="[3] 獨立階段 3：抓取 Pexels 素材", value=3),
        questionary.Choice(title="[4] 獨立階段 4：產生/更新 PPT 簡報 (基於現有 Stage 2 JSON 與 Stage 3 素材)", value=4),
        questionary.Choice(title="[5] 獨立階段 5：讀取 Stage 2 Json 腳本，進行 TTS 合成語音與背景影片", value=5),
        questionary.Choice(title="[6] 設定選項：修改 API 金鑰與樣式設定", value=6)
    ]
    
    # 支援 Github Actions 的無介面自動執行 (直接吃環境變數)
    auto_mode_env = os.getenv("AUTO_MODE")
    initial_mode = 0
    if auto_mode_env is not None:
        try:
            initial_mode = int(auto_mode_env)
            print(f"-> 偵測到 AUTO_MODE={initial_mode}，將跳過互動選單自動執行。")
        except ValueError:
            initial_mode = 0
    else:
        initial_mode = questionary.select(
            "🛠️ 請選擇執行模式：",
            choices=mode_choices
        ).ask()

    if initial_mode is None:
        return

    # ---------------------------------------------------------
    # 初始化變數 (共用狀態)
    # ---------------------------------------------------------
    target_folder = config.get("target_folder")
    generator = None
    actual_final_dir = None
    actual_temp_dir = None
    prompt_text = ""
    structured_content = None
    
    current_mode = initial_mode
    is_chained_execution = False # 標記是否為點選「接續下一階段」而來的

    # ---------------------------------------------------------
    # 流程執行迴圈
    # ---------------------------------------------------------
    while True:
        # --- 設定選項 ---
        if current_mode == 6:
            print("\n" + "=" * 60)
            print("⚙️  設定選項")
            print("=" * 60)
            
            # 重新載入設定
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            except Exception as e:
                print(f"❌ 讀取設定檔失敗：{e}")
                current_config = config
            
            # 設定選項選單
            setting_choices = [
                questionary.Choice(title="🔑 修改 API 金鑰設定", value="api_keys"),
                questionary.Choice(title="🎨 修改樣式設定", value="style"),
                questionary.Choice(title="📂 修改專案設定", value="project"),
                questionary.Choice(title="⬅️  返回主選單", value="back")
            ]
            
            setting_choice = questionary.select("請選擇要修改的設定：", choices=setting_choices).ask()
            
            if setting_choice == "api_keys":
                print("\n🔑 API 金鑰設定")
                print("-" * 30)
                
                # Gemini API 金鑰
                current_gemini = current_config.get('GEMINI_API_KEY', '')
                if current_gemini:
                    print(f"目前 Gemini API 金鑰：{current_gemini[:15]}...")
                else:
                    print("目前 Gemini API 金鑰：未設定")
                
                new_gemini = questionary.password("新 Gemini API 金鑰 (留空不修改):").ask()
                if new_gemini and new_gemini.strip():
                    current_config["GEMINI_API_KEY"] = new_gemini.strip()
                    print("✅ Gemini API 金鑰已更新")
                
                # Pexels API 金鑰
                current_pexels = current_config.get('PEXELS_API_KEY', '')
                if current_pexels:
                    print(f"目前 Pexels API 金鑰：{current_pexels[:15]}...")
                else:
                    print("目前 Pexels API 金鑰：未設定")
                
                new_pexels = questionary.password("新 Pexels API 金鑰 (留空不修改):").ask()
                if new_pexels and new_pexels.strip():
                    current_config["PEXELS_API_KEY"] = new_pexels.strip()
                    print("✅ Pexels API 金鑰已更新")
                    
            elif setting_choice == "style":
                print("\n🎨 樣式設定")
                print("-" * 30)
                
                # 載入樣式設定
                style_path = os.path.join(app_dir, 'code2course_style.json')
                try:
                    with open(style_path, 'r', encoding='utf-8') as f:
                        style_config = json.load(f)
                except Exception as e:
                    print(f"❌ 讀取樣式設定失敗：{e}")
                    style_config = {}
                
                # 顯示目前樣式設定
                print(f"目前字體：{style_config.get('font_name', '未設定')}")
                print(f"目前字體大小：{style_config.get('font_size', '未設定')}")
                print(f"主題顏色：{style_config.get('theme_color', '未設定')}")
                
                # 修改字體
                new_font = questionary.text(f"新字體 (目前: {style_config.get('font_name', 'Arial')}, 留空不修改):").ask()
                if new_font and new_font.strip():
                    style_config["font_name"] = new_font.strip()
                    print("✅ 字體已更新")
                
                # 修改字體大小
                new_size_str = questionary.text(f"新字體大小 (目前: {style_config.get('font_size', 24)}, 留空不修改):").ask()
                if new_size_str and new_size_str.strip():
                    try:
                        style_config["font_size"] = int(new_size_str.strip())
                        print("✅ 字體大小已更新")
                    except ValueError:
                        print("❌ 字體大小必須是數字")
                
                # 修改主題顏色
                new_color = questionary.text(f"新主題顏色 (目前: {style_config.get('theme_color', '#0066CC')}, 留空不修改):").ask()
                if new_color and new_color.strip():
                    style_config["theme_color"] = new_color.strip()
                    print("✅ 主題顏色已更新")
                
                # 儲存樣式設定
                try:
                    with open(style_path, 'w', encoding='utf-8') as f:
                        json.dump(style_config, f, indent=2, ensure_ascii=False)
                    print("✅ 樣式設定已儲存")
                except Exception as e:
                    print(f"❌ 儲存樣式設定失敗：{e}")
                    
            elif setting_choice == "project":
                print("\n📂 專案設定")
                print("-" * 30)
                
                # 顯示目前專案設定
                print(f"目標資料夾：{current_config.get('target_folder', '未設定')}")
                print(f"最大字元數：{current_config.get('max_chars', '未設定')}")
                print(f"支援的副檔名：{', '.join(current_config.get('supported_exts', []))}")
                print(f"排除的資料夾：{', '.join(current_config.get('exclude_dirs', []))}")
                
                # 修改目標資料夾
                new_target = questionary.text(f"新目標資料夾 (目前: {current_config.get('target_folder', '')}, 留空不修改):").ask()
                if new_target and new_target.strip():
                    current_config["target_folder"] = new_target.strip()
                    print("✅ 目標資料夾已更新")
                
                # 修改最大字元數
                new_max_chars_str = questionary.text(f"新最大字元數 (目前: {current_config.get('max_chars', 300000)}, 留空不修改):").ask()
                if new_max_chars_str and new_max_chars_str.strip():
                    try:
                        current_config["max_chars"] = int(new_max_chars_str.strip())
                        print("✅ 最大字元數已更新")
                    except ValueError:
                        print("❌ 最大字元數必須是數字")
                
            elif setting_choice == "back":
                pass
            
            # 儲存設定
            if setting_choice in ["api_keys", "project"]:
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(current_config, f, indent=2, ensure_ascii=False)
                    print("✅ 設定已儲存")
                except Exception as e:
                    print(f"❌ 儲存設定失敗：{e}")
            
            # 返回主選單
            current_mode = questionary.select(
                "🛠️ 請選擇執行模式：",
                choices=mode_choices
            ).ask()
            if current_mode is None:
                return
            continue

        # --- 階段 1：掃描 ---
        if current_mode == 1 or (current_mode == 0 and not is_chained_execution):
            if not target_folder:
                selected_path = select_analysis_path(
                    root_dir,
                    current_app_dir=app_dir,
                    prompt_title="📂 請選擇要分析的專案資料夾（選擇 all 會分析整個專案根目錄）：",
                    questionary_module=questionary,
                )
                if not selected_path:
                    return
                target_folder = os.path.basename(selected_path) or "all"
                full_target_path = selected_path
            else:
                full_target_path = resolve_analysis_target_path(root_dir, target_folder, current_app_dir=app_dir)

            if not full_target_path:
                print("❌ 無法解析分析目標。")
                return

            if target_folder == "all" or os.path.abspath(full_target_path) == os.path.abspath(root_dir):
                print(f"-> 已選擇分析整個專案根目錄: {full_target_path}")
            else:
                print(f"-> 已選擇分析資料夾: {full_target_path}")

            # 初始化產生器並建立輸出目錄
            generator = Code2Course(target_dir=full_target_path, config=config)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            actual_final_dir = os.path.join(root_dir, "outputs", target_folder, timestamp)
            actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
            os.makedirs(actual_temp_dir, exist_ok=True)

            prompt_text = generator.stage1_scan_project(temp_dir=actual_temp_dir)
            if not prompt_text: return
            
            if current_mode == 1:
                print(f"\n✅ 階段 1 完成！Prompt 已備份至：\n{os.path.join(actual_temp_dir, 'gemini_prompt_record.txt')}")
                if not questionary.confirm("是否接續執行階段 2 (Gemini 分析)？", default=True).ask():
                    break
                current_mode = 2
                is_chained_execution = True
                continue # 跳轉到下一階段

        # --- 階段 2：Gemini 分析 ---
        if current_mode == 2 or (current_mode == 0 and not is_chained_execution):
            if not is_chained_execution and current_mode == 2:
                # 接關模式：手動選歷史資料夾
                p_name, t_stamp = select_history_stage_dir(root_dir)
                if not p_name: return
                target_folder = p_name
                actual_final_dir = os.path.join(root_dir, "outputs", p_name, t_stamp)
                actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
                prompt_path = os.path.join(actual_temp_dir, "gemini_prompt_record.txt")
                if not os.path.exists(prompt_path):
                    print(f"❌ 找不到 Prompt 紀錄：{prompt_path}")
                    return
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
                generator = Code2Course(config=config)

            structured_content, _ = generator.stage2_gemini_and_ppt(prompt_text, actual_final_dir, actual_temp_dir, target_folder)
            if not structured_content: return
            
            if current_mode == 2:
                print(f"\n✅ 階段 2 完成！腳本已儲存至：\n{actual_temp_dir}")
                if not questionary.confirm("是否接續執行階段 3 (Pexels 素材抓取)？", default=True).ask():
                    break
                current_mode = 3
                is_chained_execution = True
                continue

        # --- 階段 2-1：多媒體增強 (獨立) ---
        if current_mode == 2.1:
            p_name, t_stamp = select_history_stage_dir(root_dir)
            if not p_name: return
            actual_final_dir = os.path.join(root_dir, "outputs", p_name, t_stamp)
            actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
            
            generator = Code2Course(config=config)
            structured_content = generator.stage2_1_enrich_media(actual_temp_dir, actual_final_dir, p_name)
            
            if structured_content:
                print(f"\n✅ 階段 2-1 完成！多媒體資料經已更新至：\n{actual_final_dir}")
                if questionary.confirm("是否接續執行階段 3 (Pexels 素材抓取)？", default=True).ask():
                    current_mode = 3
                    is_chained_execution = True
                    target_folder = p_name # 補齊變數給後續階段
                    continue
            break

        # --- 階段 3：素材抓取 ---
        if current_mode == 3 or (current_mode == 0 and not is_chained_execution):
            force_overwrite = False
            specific_slides = None
            
            if not is_chained_execution and current_mode == 3:
                # 接關模式
                p_name, t_stamp = select_history_stage_dir(root_dir)
                if not p_name: return
                target_folder = p_name
                actual_final_dir = os.path.join(root_dir, "outputs", p_name, t_stamp)
                actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
                analysis_path = os.path.join(actual_temp_dir, "gemini_analysis_result.json")
                if not os.path.exists(analysis_path):
                    print(f"❌ 找不到分析腳本：{analysis_path}")
                    return
                with open(analysis_path, "r", encoding="utf-8") as f:
                    structured_content = json.load(f)
                generator = Code2Course(config=config)
                
                # 選單...
                asset_choice = questionary.select("🎨 請選擇 Pexels 素材處理方式：", choices=[
                    questionary.Choice(title="1. 跳過已存在 (僅補缺)", value="skip"),
                    questionary.Choice(title="2. 全部重新下載 (全部覆寫)", value="all"),
                    questionary.Choice(title="3. 手動選擇特定投影片重新抓取", value="manual")
                ]).ask()
                if asset_choice == "all": force_overwrite = True
                elif asset_choice == "manual":
                    slide_choices = [questionary.Choice(title=f"Slide {s.get('slide_num')}: {s.get('title')}", value=str(s.get('slide_num'))) for s in structured_content if s.get('include_image', True)]
                    specific_slides = questionary.checkbox("✅ 請勾選要「重新抓取」影像的投影片：", choices=slide_choices).ask()
                    if not specific_slides: return

            generator.stage3_fetch_pexels_assets(structured_content, actual_temp_dir, force_overwrite=force_overwrite, specific_slides=specific_slides)
            
            if current_mode == 3:
                print(f"\n✅ 階段 3 完成！素材已下載至：\n{actual_temp_dir}")
                if not questionary.confirm("是否接續執行階段 4 (產生 PPT)？", default=True).ask():
                    break
                current_mode = 4
                is_chained_execution = True
                continue

        # --- 階段 4：產生 PPT ---
        if current_mode == 4 or (current_mode == 0 and not is_chained_execution):
            if not is_chained_execution and current_mode == 4:
                # 接關模式
                p_name, t_stamp = select_history_stage_dir(root_dir)
                if not p_name: return
                target_folder = p_name
                actual_final_dir = os.path.join(root_dir, "outputs", p_name, t_stamp)
                actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
                analysis_path = os.path.join(actual_temp_dir, "gemini_analysis_result.json")
                if not os.path.exists(analysis_path):
                    print(f"❌ 找不到分析腳本：{analysis_path}")
                    return
                with open(analysis_path, "r", encoding="utf-8") as f:
                    structured_content = json.load(f)
                generator = Code2Course(config=config)
            
            ppt_file = os.path.join(actual_final_dir, f"{target_folder}_course_slides.pptx")
            generator._generate_internal_ppt(structured_content, output_ppt_path=ppt_file, temp_dir=actual_temp_dir)
            
            if current_mode == 4:
                print(f"\n✅ 階段 4 完成！PPT 已儲存至：\n{actual_final_dir}")
                if not questionary.confirm("是否接續執行階段 5 (影音合成)？", default=True).ask():
                    break
                current_mode = 5
                is_chained_execution = True
                continue

        # --- 階段 5：影音合成 ---
        if current_mode == 5 or (current_mode == 0 and not is_chained_execution):
            if not is_chained_execution and current_mode == 5:
                # 接關模式
                p_name, t_stamp = select_history_stage_dir(root_dir)
                if not p_name: return
                target_folder = p_name
                actual_final_dir = os.path.join(root_dir, "outputs", p_name, t_stamp)
                actual_temp_dir = os.path.join(actual_final_dir, "temp_analysis_and_tts")
                analysis_path = os.path.join(actual_temp_dir, "gemini_analysis_result.json")
                if not os.path.exists(analysis_path):
                    print(f"❌ 找不到分析腳本：{analysis_path}")
                    return
                with open(analysis_path, "r", encoding="utf-8") as f:
                    structured_content = json.load(f)
                generator = Code2Course(config=config)

            video_file = os.path.join(actual_final_dir, f"{target_folder}_course_video.mp4")
            generator.stage4_synthesize_media(structured_content, video_file, actual_temp_dir)
            print(f"\n🎉 任務全數完成！最終影片位於：\n{video_file}")
            break # 這是最後一階段

        # 如果是模式 0，在執行完一遍循環後就應該結束 (因為它一跑就是全部)
        if current_mode == 0:
            break

if __name__ == "__main__":
    main()
