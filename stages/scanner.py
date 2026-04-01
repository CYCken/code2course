import os
from pathlib import Path

def read_source_files(target_dir, config):
    """讀取目標資料夾內的特定副檔名檔案"""
    if not target_dir:
        return {}
        
    supported_exts = config.get("supported_exts", ['.md', '.c', '.py', '.cpp', '.h'])
    contents = {}
    target_path = Path(target_dir)
    
    # 排除清單：避免讀取龐大的底層函式庫，防止超出 Gemini 100 萬 Token 限制
    exclude_dirs = config.get("exclude_dirs", ['drivers', 'rte', 'cmsis', 'build', 'node_modules', 'lib'])
    
    total_chars = 0
    max_chars = config.get("max_chars", 300000)  # 安全保護機制：限制最多讀取多少字元，防止方案超用

    # 遞迴尋找符合的檔案
    if os.path.isdir(target_path):
        for ext in supported_exts:
            for filepath in target_path.rglob(f"*{ext}"):
                file_str = str(filepath)
                
                if any(f"/{ex_dir}/" in file_str.lower() or f"\\{ex_dir}\\" in file_str.lower() for ex_dir in exclude_dirs):
                    continue
                    
                if total_chars > max_chars:
                    print(f"\n⚠️ 目錄規模龐大，讀取已達到 Token 安全邊界 ({max_chars} 字元)。已自動略過剩餘的細節檔案。\n")
                    return contents

                try:
                    # 加入 errors='ignore' 自動略過亂碼與舊編碼
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if len(content) > 50000:
                            content = content[:50000] + "\n...[內容過長已截斷]"
                        contents[file_str] = content
                        total_chars += len(content)
                except Exception:
                    pass
    return contents

def run_stage1(target_dir, config, temp_dir):
    """
    第一階段：單純掃描專案並產生 Prompt (不呼叫 Gemini)
    功能：
    1. 走訪指定的 local 資料夾 (target_dir)
    2. 將程式碼與外層的 auto_edu_prompt.txt 結合
    3. 將生成的最終 Prompt 寫入到暫存區
    """
    print(f"-> [階段 1] 開始掃描資料夾: {target_dir}")
    source_texts = read_source_files(target_dir, config)
    
    if not source_texts:
        print("未找到任何支援的程式碼或文件。")
        return None

    print("開始組合檔案內容...")
    merged_text = ""
    for filepath, content in source_texts.items():
        file_name = os.path.basename(filepath)
        merged_text += f"\n\n--- 檔案：{file_name} ---\n{content}\n"
        
    prompt_template_path = os.path.join(config.get("root_dir", "."), "code2course_prompt.txt")
    
    # 固定輸出結構描述，減少主回傳負擔
    output_structure = "1. **全局開場 (Course Overview)**\n2. **段落連貫 (Transitions)**\n3. **專業配圖與影片建議 (Visual Keywords)**：為需要的投影片提供適合在 Pexels 搜尋的照片與影片關鍵字 (英文)。\n4. **Marp Markdown 程式碼**: 為整份課程產生一份精美的 Marp Markdown 內容。"

    json_schema_fields = """        "slide_num": 1,
        "title": "🌟 課程標題",
        "bullet_points": ["重點 1", "重點 2"],
        "script": "口語化的講稿內容...",
        "include_image": true,
        "visual_keywords_photo": "engineering technology clean",
        "visual_keywords_video": "coding scrolling screen",
        "marp_content": "--- \\n# 🌟 課程標題 \\n- 重點 1 \\n- 重點 2\""""

    default_prompt = f"""[請注意：如果你要自訂此樣板，請保留最後一行的 {{merged_text}}，自動化工具才能把專案程式碼合併進來]

請你扮演「首席大師級技術講師 🧑‍🏫」，負責將這些專案原始碼，整合成一堂「有頭有尾、脈絡連貫」的線上微課程教材。
請根據專案的難度與廣度，決定最適合的課程架構。

你的輸出必須包含以下結構化資訊：
{output_structure}

輸出的格式必須是純 JSON 陣列 (Array) 結構，不需要 markdown code block，直接輸出 JSON 字串即可：
[
    {{
{json_schema_fields}
    }},
    ...
]
"""
    # 附加佈局與圖片策略 (這部分通常是固定的)
    default_prompt += """
### 圖片使用策略 (include_image)：
不要每一頁都包含圖片。僅在以下情況將 "include_image" 設為 true，並提供 Pexels 搜尋關鍵字：
- 當內容包含 **比喻 (Metaphor/Analogy)** 時，尋找能呈現該比喻的意象圖。
- 當內容 **需要圖像解釋** (例如複雜架構圖、電路、具體實物描述) 時。
- 當該頁的 **文字內容較少，留白過多**，加入圖片能讓視覺更平衡且美觀時。
若不符合上述條件，請將 "include_image" 設為 false，並將視覺關鍵字留空。

所有帶圖的投影片將自動採用「全螢幕高品質背景」排版。

以下為專案原始資料內容：
{merged_text}
"""
    # 如果使用者已定義 auto_edu_prompt.txt 則讀取，否則自動產生預設模板
    if os.path.exists(prompt_template_path):
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as pf:
                prompt = pf.read()
        except Exception:
            prompt = default_prompt
    else:
        prompt = default_prompt
        try:
            with open(prompt_template_path, "w", encoding="utf-8") as pf:
                pf.write(default_prompt)
            print(f"-> 初次執行，已生成樣板 Prompt 檔案: {prompt_template_path}")
        except Exception:
            pass
            
    # 安全機制：若使用者自訂的 Prompt 忘記加上 {merged_text}，則強力附加在最後
    if "{merged_text}" not in prompt:
        prompt += "\n\n以下為專案原始資料內容：\n{merged_text}"
        
    # 替換進原本的合併程式碼
    prompt = prompt.replace("{merged_text}", merged_text)
    
    # 輸出至紀錄檔案
    if temp_dir:
        try:
            prompt_path = os.path.join(temp_dir, "gemini_prompt_record.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"-> [階段 1] 已掃描完成！並將發送給 API 的 Prompt 封裝備份至: {prompt_path}")
        except Exception as e:
            print(f"無法寫入 Prompt：{e}")
            
    return prompt
