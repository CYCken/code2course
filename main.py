import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 匯入模組化後的核心產生器
from engine import Code2Course

# 載入環境變數 (例如 Gemini API Key)
load_dotenv()

# =========================================================
# 選單與流程控制器 (CLI Runner)
# =========================================================

def _get_target_folders(root_dir):
    try:
        folders = [f for f in os.listdir(root_dir) 
                   if os.path.isdir(os.path.join(root_dir, f)) and not f.startswith('.')]
        folders.sort()
        return folders
    except Exception:
        return []

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

def main():
    print("====== 🤖 Code2Course 教學影片生成工具 (模組化版) ======")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    config_path = os.path.join(root_dir, 'code2course_config.json')
    
    # 嘗試讀取 external config
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"讀取設定檔發生錯誤: {e}")
    config['root_dir'] = root_dir

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
        questionary.Choice(title="[5] 獨立階段 5：讀取 Stage 2 Json 腳本，進行 TTS 合成語音與背景影片", value=5)
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
        # --- 階段 1：掃描 ---
        if current_mode == 1 or (current_mode == 0 and not is_chained_execution):
            if not target_folder:
                folders = _get_target_folders(root_dir)
                if not folders:
                    print(f"在 {root_dir} 下找不到任何可分析的資料夾。")
                    return
                target_folder = questionary.select("📂 請選擇要分析的專案資料夾：", choices=folders).ask()

            if not target_folder: return

            # 初始化產生器並建立輸出目錄
            full_target_path = os.path.join(root_dir, target_folder)
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
