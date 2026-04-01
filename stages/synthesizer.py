import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

def run_stage5(structured_content, output_video_path, temp_dir, style=None):
    """
    第五階段：語音與影片合成 (純圖片背景版)
    功能：
    1. 語音：使用 edge-tts 將腳本轉換為語音檔
    2. 影片：從結構化分鏡表繪製背景 (使用 Pillow)，增加高對比遮罩，與語音檔合成 (MoviePy)
    """
    if style is None:
        style = {}
        
    try:
        # 兼容 MoviePy 1.x 與 2.x
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
        
    if not structured_content:
        print("無結構化 JSON 腳本可進行影片合成。")
        return

    print("-> [階段 5] 開始進行語音合成與教學影片生成")
    
    # 從 Style 中取得顏色與大小 (轉換為 tuple)
    overlay_rgba = tuple(style.get("video_overlay_rgba", [0, 0, 0, 160]))
    banner_rgba = tuple(style.get("video_banner_rgba", [41, 128, 185, 180]))
    card_mask_rgba = tuple(style.get("video_card_mask_rgba", [20, 20, 20, 127]))
    bg_color_rgb = tuple(style.get("video_bg_color_rgb", [25, 28, 36]))
    text_color_rgb = tuple(style.get("video_text_color_rgb", [255, 255, 255]))
    title_size = style.get("video_title_font_size", 80)
    body_size = style.get("video_body_font_size", 50)

    final_clips = []
    total_slides = len(structured_content)
    for idx, slide_data in enumerate(structured_content):
        slide_num = slide_data.get('slide_num', 1)
        text_script = str(slide_data.get('script', ''))
        audio_path = os.path.join(temp_dir, f"slide_{slide_num}_audio.mp3")
        
        # 1. 生成語音
        if not os.path.exists(audio_path):
            print(f"\r正在生成語音腳本: 第 {slide_num} / {total_slides} 頁 (edge-tts)...", end="", flush=True)
            subprocess.run(["edge-tts", "--voice", "zh-TW-HsiaoChenNeural", "--text", text_script, "--write-media", audio_path], check=True, capture_output=True)
        
    if total_slides > 0:
        print() # 結束進度條換行
        
    for slide_data in structured_content:
        slide_num = slide_data.get('slide_num', 1)
        pexels_img_path = os.path.join(temp_dir, f"slide_{slide_num}_pexels_bg.jpg")
        if os.path.exists(pexels_img_path):
            try:
                img = Image.open(pexels_img_path).resize((1920, 1080))
            except Exception:
                img = Image.new('RGB', (1920, 1080), color=bg_color_rgb)
        else:
            img = Image.new('RGB', (1920, 1080), color=bg_color_rgb)
        
        # 3. 製作文字遮罩圖層 (直接在圖片上繪製)
        # 先加一層全局半透明背景讓整體變暗
        overlay = Image.new('RGBA', img.size, overlay_rgba)
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        
        draw = ImageDraw.Draw(img)
        
        # 尋找支援中文的字型
        font_title = None
        font_body = None
        system_fonts = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
        ]
        for f_path in system_fonts:
            if os.path.exists(f_path):
                try:
                    font_title = ImageFont.truetype(f_path, title_size)
                    font_body = ImageFont.truetype(f_path, body_size)
                    break
                except Exception:
                    continue
        if not font_title:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

        # 頂部橫幅
        draw.rectangle([(0, 0), (1920, 150)], fill=banner_rgba)
        title_text = str(slide_data.get('title', '無標題'))
        draw.text((100, 35), title_text, font=font_title, fill=text_color_rgb)

        # 中間內文區塊遮罩 (Card Effect)
        # 如果是「無背景圖片」的投影片，則不顯示額外的遮罩框，統一背景色即可
        points = slide_data.get('bullet_points', [])
        if points:
            if os.path.exists(pexels_img_path):
                # 建立一個獨立圖層來進行透明度融合 (Pillow draw.rectangle 不會自動 blending)
                mask_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                mask_draw = ImageDraw.Draw(mask_layer)
                mask_draw.rectangle([(80, 200), (1840, 950)], fill=card_mask_rgba)
                img = Image.alpha_composite(img, mask_layer)
                draw = ImageDraw.Draw(img)
            
            y_offset = 250
            for point in points:
                bullet_str = f"• {point}"
                chunk_len = 35
                chunks = [bullet_str[i:i+chunk_len] for i in range(0, len(bullet_str), chunk_len)]
                for chunk in chunks:
                    draw.text((120, y_offset), chunk, font=font_body, fill=text_color_rgb)
                    y_offset += 75
                y_offset += 30
            
        # 儲存繪製好的影格圖片
        final_frame_path = os.path.join(temp_dir, f"slide_{slide_num}_final_frame.png")
        img.convert('RGB').save(final_frame_path)
        
        # 4. 結合 MoviePy
        audioclip = AudioFileClip(audio_path)
        videoclip = ImageClip(final_frame_path)
        
        # 兼容 MoviePy 1.x 與 2.x 的 API
        if hasattr(videoclip, 'with_duration'):
            videoclip = videoclip.with_duration(audioclip.duration).with_audio(audioclip)
        else:
            videoclip = videoclip.set_duration(audioclip.duration).set_audio(audioclip)
            
        final_clips.append(videoclip)
        
    print("所有分頁合成完畢，開始串接影片...")
    final_video = concatenate_videoclips(final_clips)
    final_video.write_videofile(output_video_path, fps=24, codec="libx264", audio_codec="aac")
    
    print(f"-> [階段 5] 教學影片合成完畢，已保存至: {output_video_path}")
