import os
import json
import re
import sys
import time
import threading

def generate_marp_markdown(structured_content, output_path):
    """產生 Marp 格式的 Markdown 檔案"""
    marp_header = "---\nmarp: true\ntheme: default\nclass: invert\npaginate: true\n---\n\n"
    full_content = marp_header
    for slide in structured_content:
        content = slide.get('marp_content', '')
        if content:
            if not content.startswith('---'):
                full_content += "---\n"
            full_content += content + "\n\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    return output_path

def generate_external_tool_scripts(output_dir, config, project_name, invideo_list=None, remotion_list=None):
    """產生給 InVideo AI 與 Remotion 使用的專屬資料案 (完全獨立輸出)"""
    
    # 1. InVideo 專用資料
    if config.get("enable_invideo") and invideo_list:
        invideo_prompt_path = os.path.join(output_dir, f"{project_name}_invideo_prompt.txt")
        invideo_json_path = os.path.join(output_dir, f"{project_name}_invideo.json")
        
        invideo_text = f"Create a professional educational video about {project_name}. \n\n"
        for item in invideo_list:
            scene = item.get('invideo_scene', '')
            script = item.get('voiceover', '')
            invideo_text += f"Scene {item.get('slide_num')}: {scene}\nVoiceover: {script}\n\n"
        
        with open(invideo_prompt_path, "w", encoding="utf-8") as f:
            f.write(invideo_text)
        with open(invideo_json_path, "w", encoding="utf-8") as f:
            json.dump(invideo_list, f, ensure_ascii=False, indent=4)
            
        print(f"-> InVideo 專用輸出已產生: {invideo_json_path}")
        
    # 2. Remotion 專用資料
    if config.get("enable_remotion") and remotion_list:
        remotion_json_path = os.path.join(output_dir, f"{project_name}_remotion.json")
        remotion_wrapper = {
            "project_name": project_name,
            "slides": remotion_list
        }
        with open(remotion_json_path, "w", encoding="utf-8") as f:
            json.dump(remotion_wrapper, f, ensure_ascii=False, indent=4)
        print(f"-> Remotion 專用輸出已產生: {remotion_json_path}")

def _call_gemini_silent(model, prompt, config):
    """不帶動畫的 Gemini 呼叫，用於背景增強作業"""
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
        safety_settings=safety_settings
    )
    return response.text

def enrich_with_media_meta(model, core_content, config):
    """
    二次增強函式：不合併回原本的資料，直接產出專用的 Enrichment 列表。
    """
    enable_invideo = config.get("enable_invideo", False)
    enable_remotion = config.get("enable_remotion", False)
    
    # 建立任務說明 (用於 Console 顯示)
    task_parts = []
    if enable_invideo: task_parts.append("InVideo")
    if enable_remotion: task_parts.append("Remotion")
    task_desc = " + ".join(task_parts)
    print(f"   ({task_desc})...")

    batch_size = 5
    final_invideo = []
    final_remotion = []
    
    total = len(core_content)
    for i in range(0, total, batch_size):
        batch = core_content[i:i+batch_size]
        start_idx = i + 1
        end_idx = min(i + batch_size, total)
        print(f"   正在處理 第 {start_idx}~{end_idx} 頁...")
        
        context_data = [{"slide_num": s.get("slide_num"), "title": s.get("title"), "script": s.get("script")} for s in batch]
            
        instructions = "請根據標題與講稿，為每一頁產生專屬多媒體資訊。\n"
        if enable_invideo: instructions += "- invideo_scene: 分鏡描述 (英文)\n"
        if enable_remotion: instructions += "- remotion_data: 動畫屬性 (JSON)\n"
            
        prompt = f"""
[TASK: MEDIA ENRICHMENT - STRICT JSON ONLY]
{instructions}
[REQUIREMENTS]
- Return a VALID JSON array of {len(batch)} objects.
- Each object MUST contain "slide_num" and the enriched fields.
- Ensure all strings are properly escaped. If including quotes inside strings, use \\".
- NO conversational text. NO Markdown blocks. ONLY the raw JSON array.

[INPUT DATA]
{json.dumps(context_data, ensure_ascii=False)}
"""
        try:
            raw_response = _call_gemini_silent(model, prompt, config).strip()
            # 移除可能存在的 Markdown 標籤以防干擾
            json_str = re.sub(r'^```json\s*|\s*```$', '', raw_response, flags=re.MULTILINE).strip()
            
            # 使用更強大的正則提取，防止 AI 夾雜廢話
            match = re.search(r'(\[.*\])', json_str, re.DOTALL)
            if match:
                json_to_parse = match.group(1)
            else:
                json_to_parse = json_str
                
            batch_enriched = json.loads(json_to_parse, strict=False)
            
            # 分別歸類到獨立列表，不污染 Core
            for enriched_item in batch_enriched:
                s_num = enriched_item.get('slide_num')
                # 找出原始講稿備用
                orig = next((s for s in batch if s['slide_num'] == s_num), {})
                
                if enable_invideo:
                    final_invideo.append({
                        "slide_num": s_num,
                        "invideo_scene": enriched_item.get('invideo_scene', ''),
                        "voiceover": orig.get('script', '')
                    })
                if enable_remotion:
                    final_remotion.append({
                        "slide_num": s_num,
                        "title": orig.get('title', ''),
                        "script": orig.get('script', ''),  # 補回講稿，這對 Remotion 很重要
                        "bullet_points": orig.get('bullet_points', []),
                        "remotion_data": enriched_item.get('remotion_data', {})
                    })
        except Exception as e:
            print(f"      ⚠️ 第 {start_idx}~{end_idx} 頁增強失敗: {e}")
            
    return final_invideo, final_remotion

def run_stage2(model, prompt_text, final_dir, temp_dir, config, project_name):
    """
    第二階段 (解耦分析版本)：
    - 第一波：獲取核心內容 (Script/Marp)
    - 第二波：(可選) 獲取 InVideo/Remotion 專用資料並獨立產出
    """
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    print(f"-> [階段 2] 開始進行 AI 分析: {project_name}")
    
    stop_spinner = False
    start_time = time.time()
    def spinner():
        chars = ['|', '/', '-', '\\']
        idx = 0
        while not stop_spinner:
            sys.stdout.write(f"\r正在進行核心分析 {chars[idx % 4]} ")
            sys.stdout.flush(); idx += 1; time.sleep(0.1)
        duration = time.time() - start_time
        sys.stdout.write(f"\rAI 核心分析完成！(耗時 {duration:.1f} 秒)                   \n")

    spinner_thread = threading.Thread(target=spinner); spinner_thread.start()
    final_prompt = prompt_text + "\n\n[要求] 直接輸出 JSON 陣列，內容必須正確轉義。不包含 invideo 或 remotion 欄位。"

    try:
        safety_settings = {cat: HarmBlockThreshold.BLOCK_NONE for cat in [HarmCategory.HARM_CATEGORY_HARASSMENT, HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT]}
        response = model.generate_content(final_prompt, generation_config={"response_mime_type": "application/json"}, safety_settings=safety_settings)
    finally:
        stop_spinner = True; spinner_thread.join()

    try:
        match = re.search(r'(\[.*\])', response.text, re.DOTALL)
        core_content = json.loads(match.group(1) if match else response.text, strict=False)
        
        # 顯示頁數彙報
        total_slides = len(core_content) if core_content else 0
        print(f"-> Gemini 分析完成！本課程共產出 {total_slides} 頁內容。")

        # 保存核心結果
        if core_content and temp_dir:
            with open(os.path.join(temp_dir, "gemini_analysis_result.json"), "w", encoding="utf-8") as f:
                json.dump(core_content, f, ensure_ascii=False, indent=4)
        
        # 二次增強處：獨立產出，不合併回 core_content
        inv_list, rem_list = [], []
        enable_invideo = config.get("enable_invideo", False)
        enable_remotion = config.get("enable_remotion", False)

        if enable_invideo or enable_remotion:
            # 建立動態狀態文字
            tasks = []
            if enable_invideo: tasks.append("InVideo")
            if enable_remotion: tasks.append("Remotion")
            task_str = " + ".join(tasks)
            
            print(f"-> [偵測到擴充需求] 開始生成專屬資料 ({task_str})...")
            inv_list, rem_list = enrich_with_media_meta(model, core_content, config)
            
        # 產生結果檔案
        if final_dir:
            generate_marp_markdown(core_content, os.path.join(final_dir, f"{project_name}_professional_slides.md"))
            generate_external_tool_scripts(final_dir, config, project_name, inv_list, rem_list)
            
        return core_content
    except Exception as e:
        print(f"\n執行過程中發生錯誤：{e}"); return None
