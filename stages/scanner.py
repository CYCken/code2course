import os
import json
from pathlib import Path


def _summarize_project_structure(target_dir, config):
    """建立專案目錄結構摘要，讓 Prompt 更接近整個專案分析。"""
    if not target_dir:
        return "(無有效目標目錄)"

    target_path = Path(target_dir)
    if not target_path.exists() or not target_path.is_dir():
        return "(目錄不存在)"

    exclude_dirs = set(config.get("exclude_dirs", ['drivers', 'rte', 'cmsis', 'build', 'node_modules', 'lib']))
    summary_lines = []

    try:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = sorted([d for d in dirs if not any(f"/{d}/" in f"/{os.path.join(root, d)}/" or f"\\{d}\\" in f"{os.path.join(root, d)}\\" for _ in [0])])
            dirs[:] = sorted([d for d in dirs if d not in exclude_dirs and not d.startswith('.')])
            rel_root = os.path.relpath(root, target_path)
            if rel_root == '.':
                current_prefix = '.'
            else:
                current_prefix = rel_root
            if files:
                visible_files = sorted([f for f in files if not f.startswith('.')])[:20]
                summary_lines.append(f"{current_prefix}/: {', '.join(visible_files)}")
                if len(files) > 20:
                    summary_lines.append(f"... 以及 {len(files) - 20} 個其他檔案")
    except Exception:
        return "(結構摘要建立失敗)"

    return "\n".join(summary_lines[:40]) or "(無可顯示的檔案結構)"


def _is_excluded_path(path_str, exclude_dirs):
    path_str_lower = path_str.lower()
    return any(f"/{ex_dir}/" in path_str_lower or f"\\{ex_dir}\\" in path_str_lower for ex_dir in exclude_dirs)


def _iter_supported_files(target_dir, config):
    if not target_dir:
        return []

    target_path = Path(target_dir)
    if not target_path.exists() or not target_path.is_dir():
        return []

    supported_exts = config.get("supported_exts", ['.md', '.c', '.py', '.cpp', '.h'])
    exclude_dirs = set(config.get("exclude_dirs", ['drivers', 'rte', 'cmsis', 'build', 'node_modules', 'lib']))
    exclude_dirs.update({'code2course', 'code2course-'})

    results = []
    for ext in supported_exts:
        for filepath in target_path.rglob(f"*{ext}"):
            if not filepath.is_file():
                continue
            file_str = str(filepath)
            if _is_excluded_path(file_str, exclude_dirs):
                continue
            try:
                rel_parts = filepath.relative_to(target_path).parts
            except Exception:
                rel_parts = ()
            if any(part.lower() in {'code2course', 'code2course-'} for part in rel_parts):
                continue
            results.append(filepath)
    return sorted(results)


def estimate_project_size(target_dir, config):
    """預檢專案內容規模，提供大型專案的切分依據。"""
    files = _iter_supported_files(target_dir, config)
    total_bytes = 0
    for filepath in files:
        try:
            total_bytes += os.path.getsize(filepath)
        except Exception:
            continue
    return {
        'file_count': len(files),
        'estimated_chars': total_bytes,
        'too_large': total_bytes > config.get("max_chars", 300000),
    }


def read_source_files(target_dir, config):
    """讀取目標資料夾內的特定副檔名檔案"""
    if not target_dir:
        return {}

    supported_exts = config.get("supported_exts", ['.md', '.c', '.py', '.cpp', '.h'])
    contents = {}
    target_path = Path(target_dir)

    exclude_dirs = set(config.get("exclude_dirs", ['drivers', 'rte', 'cmsis', 'build', 'node_modules', 'lib']))
    exclude_dirs.update({'code2course', 'code2course-'})

    total_chars = 0
    max_chars = config.get("max_chars", 300000)

    if os.path.isdir(target_path):
        for ext in supported_exts:
            for filepath in target_path.rglob(f"*{ext}"):
                file_str = str(filepath)
                if _is_excluded_path(file_str, exclude_dirs):
                    continue
                try:
                    rel_parts = filepath.relative_to(target_path).parts
                except Exception:
                    rel_parts = ()
                if any(part.lower() in {'code2course', 'code2course-'} for part in rel_parts):
                    continue

                if total_chars > max_chars:
                    print(f"\n⚠️ 目錄規模龐大，讀取已達到 Token 安全邊界 ({max_chars} 字元)。已自動略過剩餘的細節檔案。\n")
                    return contents

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if len(content) > 50000:
                            content = content[:50000] + "\n...[內容過長已截斷]"
                        contents[file_str] = content
                        total_chars += len(content)
                except Exception:
                    pass
    return contents


def _summarize_folder_with_gemini(model, folder_path, file_snippets):
    """對單一資料夾做 Gemini 摘要，作為大型專案的第一層理解。"""
    if not model:
        return None
    try:
        prompt = f"""請你扮演資深工程講師，為下面的專案資料夾做重點摘要。請只輸出中文摘要，不要寫程式碼。請包含：
1. 這個資料夾的角色與主要功能
2. 重要檔案與關鍵概念
3. 它對整體專案的貢獻

[資料夾] {folder_path.name}
[檔案內容片段]
{file_snippets}
"""
        response = model.generate_content(prompt)
        return getattr(response, 'text', '').strip() or None
    except Exception as exc:
        print(f"   ⚠️ 資料夾摘要失敗 ({folder_path.name}): {exc}")
        return None


def build_folder_priority_context(target_dir, config, model=None):
    """對超大專案建立「先按資料夾分析」的摘要內容，供後續 Gemini 分層分析。"""
    target_path = Path(target_dir)
    if not target_path.exists() or not target_path.is_dir():
        return None

    exclude_dirs = set(config.get("exclude_dirs", ['drivers', 'rte', 'cmsis', 'build', 'node_modules', 'lib']))
    exclude_dirs.update({'code2course', 'code2course-', 'outputs'})
    supported_exts = config.get("supported_exts", ['.md', '.c', '.py', '.cpp', '.h'])

    folder_summaries = []
    for child in sorted(target_path.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith('.'):
            continue
        if child.name.lower() in exclude_dirs:
            continue
        folder_items = []
        for ext in supported_exts:
            for filepath in child.rglob(f"*{ext}"):
                if not filepath.is_file():
                    continue
                file_str = str(filepath)
                if _is_excluded_path(file_str, exclude_dirs):
                    continue
                folder_items.append(filepath)
                if len(folder_items) >= 8:
                    break
            if len(folder_items) >= 8:
                break

        if not folder_items:
            continue

        summary_lines = []
        for filepath in folder_items:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    snippet = f.read(400).replace('\n', ' ').strip()
            except Exception:
                snippet = ''
            summary_lines.append(f"- {filepath.name}: {snippet[:240]}")

        heuristic_summary = "\n".join(summary_lines)
        gemini_summary = None
        if model is not None:
            gemini_summary = _summarize_folder_with_gemini(model, child, heuristic_summary)

        folder_summaries.append({
            'folder': child.name,
            'summary': gemini_summary or heuristic_summary,
            'summary_mode': 'gemini' if gemini_summary else 'heuristic'
        })

    return {
        'mode': 'folder_priority',
        'project_root': str(target_path),
        'folder_summaries': folder_summaries,
    }


def prepare_project_context(target_dir, config, model=None):
    """依據專案規模選擇完整內容或分層資料夾摘要。"""
    size_info = estimate_project_size(target_dir, config)
    if size_info['too_large']:
        folder_context = build_folder_priority_context(target_dir, config, model=model)
        if folder_context and folder_context['folder_summaries']:
            return {
                'mode': 'folder_priority',
                'size_info': size_info,
                'folder_context': folder_context,
            }

    source_texts = read_source_files(target_dir, config)
    merged_text = ""
    for filepath, content in source_texts.items():
        file_name = os.path.basename(filepath)
        merged_text += f"\n\n--- 檔案：{file_name} ---\n{content}\n"
    return {
        'mode': 'full',
        'size_info': size_info,
        'source_texts': source_texts,
        'merged_text': merged_text,
    }

def run_stage1(target_dir, config, temp_dir, model=None):
    """
    第一階段：單純掃描專案並產生 Prompt (不呼叫 Gemini)
    功能：
    1. 走訪指定的 local 資料夾 (target_dir)
    2. 將程式碼與外層的 auto_edu_prompt.txt 結合
    3. 將生成的最終 Prompt 寫入到暫存區
    """
    print(f"-> [階段 1] 開始掃描資料夾: {target_dir}")
    project_context = prepare_project_context(target_dir, config, model=model)
    size_info = project_context.get('size_info', {})
    if size_info.get('too_large'):
        print(f"-> [階段 1] 偵測到大型專案 (約 {size_info.get('estimated_chars', 0)} 字元)，改採資料夾優先摘要模式。")

    if project_context.get('mode') == 'full':
        source_texts = project_context.get('source_texts', {})
        if not source_texts:
            print("未找到任何支援的程式碼或文件。")
            return None
        merged_text = project_context.get('merged_text', '')
    else:
        folder_context = project_context.get('folder_context', {})
        if not folder_context.get('folder_summaries'):
            print("未找到任何支援的程式碼或文件。")
            return None
        merged_text = ""
        for item in folder_context['folder_summaries']:
            merged_text += f"\n\n### 資料夾：{item['folder']}\n{item['summary']}\n"

    project_structure = _summarize_project_structure(target_dir, config)
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

請把這次分析視為「完整專案導向的教學設計」，而不是僅針對單一檔案或局部程式碼片段。請先理解專案的整體目的、架構與功能流程，再整理出一個適合微課教學的脈絡。

專案分析範圍：{target_dir}
專案結構摘要：
{project_structure}

如果這是一個大型專案，請先以資料夾為單位理解關鍵功能，並在輸出中強調各資料夾的角色與彼此之間的互動。

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

            meta_path = os.path.join(temp_dir, "scan_mode.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "mode": project_context.get('mode', 'full'),
                    "size_info": project_context.get('size_info', {}),
                    "project_root": target_dir,
                }, f, ensure_ascii=False, indent=2)

            print(f"-> [階段 1] 已掃描完成！並將發送給 API 的 Prompt 封裝備份至: {prompt_path}")
        except Exception as e:
            print(f"無法寫入 Prompt：{e}")
            
    return prompt
