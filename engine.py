import os
import google.generativeai as genai
from utils.style_config import load_style_config
from stages.scanner import run_stage1
from stages.analyzer import run_stage2, enrich_with_media_meta, generate_external_tool_scripts, generate_marp_markdown
from stages.assets import run_stage3
from stages.presenter import run_stage4
from stages.synthesizer import run_stage5

class Code2Course:
    def __init__(self, target_dir=None, config=None):
        self.target_dir = target_dir
        self.config = config or {}
        self.api_key = self.config.get("GEMINI_API_KEY", "").strip()
        
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
            
        self.pexels_api_key = self.config.get("PEXELS_API_KEY", "").strip()
        if not self.pexels_api_key:
            self.pexels_api_key = os.getenv("PEXELS_API_KEY", "").strip()
            
        # 設定 Gemini API Key
        genai.configure(api_key=self.api_key)
        
        # 從設定檔讀取模型名稱，若無則預設使用 1.5 Flash
        self.model_name = self.config.get("gemini_model", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
        print(f"-> 已載入 Gemini 模型: {self.model_name}")
        
        # 載入樣式設定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.style = load_style_config(current_dir)

    def stage1_scan_project(self, temp_dir):
        """第一階段：單純掃描專案並產生 Prompt"""
        return run_stage1(self.target_dir, self.config, temp_dir)

    def stage2_gemini_and_ppt(self, prompt_text, final_dir, temp_dir, project_name):
        """第二階段：呼叫 Gemini 產出 JSON 分鏡圖"""
        structured_content = run_stage2(self.model, prompt_text, final_dir, temp_dir, self.config, project_name)
        # 為了相容性，回傳 structured_content, None (原本這階段不產 PPT，但回傳值預期有兩個)
        return structured_content, None

    def stage2_1_enrich_media(self, temp_dir, final_dir, project_name):
        """獨立階段 2-1：基於現有分析結果生成多媒體專屬資料"""
        import os
        import json
        
        analysis_file = os.path.join(temp_dir, "gemini_analysis_result.json")
        if not os.path.exists(analysis_file):
            print(f"❌ 找不到核心分析結果: {analysis_file}\n請先執行階段 2。")
            return None
            
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                core_content = json.load(f)
        except Exception as e:
            print(f"❌ 讀取核心分析檔案失敗: {e}")
            return None
            
        print(f"-> [階段 2-1] 讀取到 {len(core_content)} 頁核心內容，開始生成專屬資料...")
        inv_list, rem_list = enrich_with_media_meta(self.model, core_content, self.config)
        
        if final_dir:
            # 重新產生外部工具腳本
            generate_external_tool_scripts(final_dir, self.config, project_name, inv_list, rem_list)
            # 同時更新一下 PPT Markdown (避免有變動)
            marp_file = os.path.join(final_dir, f"{project_name}_professional_slides.md")
            generate_marp_markdown(core_content, marp_file)
            print(f"-> [階段 2-1] 專屬資料 (InVideo/Remotion) 已存放至: {final_dir}")
            
        return core_content

    def stage3_fetch_pexels_assets(self, structured_content, temp_dir, force_overwrite=False, specific_slides=None):
        """第三階段：純粹抓取 Pexels 素材"""
        return run_stage3(self.pexels_api_key, structured_content, temp_dir, force_overwrite, specific_slides)

    def _generate_internal_ppt(self, structured_content, output_ppt_path, temp_dir=None):
        """第四階段：產生/更新 PPT 簡報 (Internal helper renamed for compatibility)"""
        return run_stage4(structured_content, output_ppt_path, self.style, temp_dir)

    def stage4_synthesize_media(self, structured_content, output_video_path, temp_dir):
        """第五階段：語音與影片合成 (Compatibility name for run_stage5)"""
        return run_stage5(structured_content, output_video_path, temp_dir, style=self.style)
