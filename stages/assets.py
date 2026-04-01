import os
import json
import requests
import time
import random

def fetch_pexels_assets(pexels_api_key, query, asset_type='photo', save_path=None, page=1):
    """從 Pexels API 抓取圖片或影片，含基本的錯誤處理與 Rate Limit 偵測"""
    if not pexels_api_key:
        return None
        
    headers = {"Authorization": pexels_api_key}
    endpoint = "https://api.pexels.com/v1/search" if asset_type == 'photo' else "https://api.pexels.com/videos/search"
    
    # 嘗試次數 (對於 429 錯誤)
    max_retries = 2

    for attempt in range(max_retries):
        try:
            params = {"query": query, "per_page": 1, "page": page}
            response = requests.get(endpoint, headers=headers, params=params, timeout=12)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('photos') if asset_type == 'photo' else data.get('videos')
                if not items:
                    # 如果分頁太後面沒結果，則嘗試回歸到第一頁
                    if page > 1:
                        return fetch_pexels_assets(pexels_api_key, query, asset_type, save_path, page=1)
                    return None
                    
                if asset_type == 'photo':
                    img_data = items[0]['src']
                    url = img_data['landscape']
                    photographer = items[0].get('photographer', 'Pexels User')
                    pexels_url = items[0].get('url', '')
                else:
                    video_files = items[0].get('video_files', [])
                    selected_video = next((v for v in video_files if v['quality'] == 'hd'), video_files[0])
                    url = selected_video['link']
                    
                if save_path:
                    resp = requests.get(url, stream=True, timeout=20)
                    if resp.status_code == 200:
                        with open(save_path, 'wb') as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        if asset_type == 'photo':
                            return {"path": save_path, "photographer": photographer, "url": pexels_url}
                        return save_path
                return url
            
            elif response.status_code == 429:
                print(f"⚠️ 觸發 Pexels Rate Limit (429)，嘗試等待 5 秒... (第 {attempt+1} 次)")
                time.sleep(5)
                continue
            else:
                print(f"❌ Pexels API 錯誤代碼 {response.status_code} for query: {query}")
                return None

        except Exception as e:
            print(f"Pexels 溝通異常 ({asset_type}): {e}")
            return None
    
    return None

def run_stage3(pexels_api_key, structured_content, temp_dir, force_overwrite=False, specific_slides=None):
    """
    第三階段：純粹抓取 Pexels 素材
    功能：
    1. 遍歷分鏡腳本中的關鍵字
    2. 下載對應圖片與影片 B-roll
    3. 支援覆寫與跳過邏輯 (全域或指定 Slide)
    """
    if not pexels_api_key or not pexels_api_key.strip():
        print("-> [階段 3] 未偵測到 Pexels API Key，無法進行素材抓取。")
        return False

    print(f"-> [階段 3] 開始抓取 Pexels 素材，目標目錄: {temp_dir}")
    count_success = 0
    count_failed = 0
    count_skipped = 0

    image_metadata_map = {}

    for slide in structured_content:
        num = slide.get('slide_num', 1)
        include_image = slide.get('include_image', True)
        if not include_image:
            continue

        kw_photo = slide.get('visual_keywords_photo', 'technology')
        kw_video = slide.get('visual_keywords_video', 'coding')
        
        photo_path = os.path.join(temp_dir, f"slide_{num}_pexels_bg.jpg")
        video_path = os.path.join(temp_dir, f"slide_{num}_pexels_broll.mp4")

        # 判斷是否需要覆寫 (1. 全域強制覆寫 2. 指定清單內包含此頁)
        should_overwrite_this = force_overwrite
        if not should_overwrite_this and specific_slides:
            if str(num) in [str(s) for s in specific_slides]:
                should_overwrite_this = True

        # 圖片處理
        if os.path.exists(photo_path) and not should_overwrite_this:
            count_skipped += 1
        else:
            # A 方案：隨機頁碼邏輯
            # 如果是重新抓取 (overwrite)，則在 Pexels 搜尋結果的前 10 頁中隨機挑選，避免拿到重覆圖片
            search_page = random.randint(1, 10) if should_overwrite_this else 1
            
            print(f"正在{'重新' if should_overwrite_this else ''}抓取第 {num} 頁圖片 (關鍵字: {kw_photo}, Page: {search_page})...")
            res_meta = fetch_pexels_assets(pexels_api_key, kw_photo, asset_type='photo', save_path=photo_path, page=search_page)
            if res_meta and isinstance(res_meta, dict):
                image_metadata_map[str(num)] = res_meta
                count_success += 1
            elif res_meta: # Fallback
                count_success += 1
            else: 
                count_failed += 1

        # 影片處理 (暫時註解，目前合成階段主要使用圖片以確保文字可讀性)
        # if os.path.exists(video_path) and not should_overwrite_this:
        #     pass 
        # else:
        #     if should_overwrite_this:
        #         search_page = random.randint(1, 5) # 影片結果較少，頁數設定保守一點
        #         print(f"正在重新抓取第 {num} 頁影片 (關鍵字: {kw_video}, Page: {search_page})...")
        #         fetch_pexels_assets(pexels_api_key, kw_video, asset_type='video', save_path=video_path, page=search_page)
        #     else:
        #         fetch_pexels_assets(pexels_api_key, kw_video, asset_type='video', save_path=video_path)

    # 儲存圖片來源資料供 PPT 使用
    if image_metadata_map:
        source_file = os.path.join(temp_dir, "image_sources.json")
        with open(source_file, "w", encoding="utf-8") as f:
            json.dump(image_metadata_map, f, ensure_ascii=False, indent=4)

    print(f"\n✨ [階段 3] 素材抓取結束！")
    print(f"成功: {count_success} | 失敗: {count_failed} | 跳過: {count_skipped}")
    return True
