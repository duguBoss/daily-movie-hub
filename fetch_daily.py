import requests
import json
import os
import sys
import shutil
from datetime import datetime

# ---------------- 配置区域 ----------------
TOKEN = os.environ.get("TMDB_API_KEY")
if not TOKEN:
    print("❌ 错误: 环境变量 TMDB_API_KEY 未找到！")
    sys.exit(1)

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"

DATA_DIR = "data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "weekly_updates.json")

# ---------------- 辅助功能 ----------------

def setup_directories(reset=False):
    if reset:
        print("🔄 周一重置: 清理旧数据...")
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)
    
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_existing_ids():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return [item["id"] for item in data]
            except:
                return []
    return []

def download_image(url, filename):
    if not url: return None
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)
            return f"images/{filename}"
    except:
        pass
    return None

# ---------------- 核心获取逻辑 ----------------

def get_credits(media_type, media_id):
    """获取导演和主演"""
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "zh-CN"}, timeout=10)
        data = resp.json()
        
        # 提取导演 (仅电影有导演，剧集通常是创作者)
        directors = [c["name"] for c in data.get("crew", []) if c["job"] == "Director"]
        # 提取前 5 名演员
        actors = [c["name"] for c in data.get("cast", [])[:5]]
        
        return {
            "directors": directors,
            "actors": actors
        }
    except:
        return {"directors": [], "actors": []}

def get_reviews(media_type, media_id):
    """获取热门长评 (通常是英文)"""
    url = f"{BASE_URL}/{media_type}/{media_id}/reviews"
    try:
        # Reviews 接口不一定有中文，所以不强制 zh-CN，否则可能为空
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        
        # 按内容长度排序，取前 3 条长评 (长评通常信息量大)
        # 或者按 verify_users 排序
        sorted_reviews = sorted(results, key=lambda x: len(x["content"]), reverse=True)[:3]
        
        reviews_text = []
        for r in sorted_reviews:
            clean_content = r["content"].strip()[:1000] # 截取前1000字防止太长
            reviews_text.append(f"【评论人: {r['author']}】\n{clean_content}...")
            
        return reviews_text
    except:
        return []

def fetch_content(media_type, existing_ids):
    url = f"{BASE_URL}/trending/{media_type}/day"
    params = {"language": "zh-CN"}
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200: return None
        
        results = resp.json().get("results", [])
        target_item = None
        
        # 去重逻辑
        for item in results:
            if item["id"] not in existing_ids:
                target_item = item
                break
        
        if not target_item: return None

        # --- 获取详情 ---
        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params=params, timeout=15)
        detail = detail_resp.json()
        
        # --- 获取 影评 & 卡司 (新增功能) ---
        credits = get_credits(media_type, detail["id"])
        reviews = get_reviews(media_type, detail["id"])

        # --- 下载图片 ---
        poster = download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", f"{media_type}_{detail['id']}_p.jpg")
        backdrop = download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", f"{media_type}_{detail['id']}_b.jpg")

        return {
            "update_date": datetime.now().strftime("%Y-%m-%d"),
            "id": detail["id"],
            "type": "电影" if media_type == "movie" else "剧集",
            "title": detail.get("title") or detail.get("name"),
            "original_title": detail.get("original_title") or detail.get("original_name"),
            "rating": round(detail.get("vote_average", 0), 1),
            "date": detail.get("release_date") or detail.get("first_air_date"),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "director": credits["directors"],  # 导演
            "actors": credits["actors"],       # 主演
            "overview": detail.get("overview", ""), # 官方简介
            "reviews": reviews,                # 抓取到的长评列表
            "poster_path": poster,
            "backdrop_path": backdrop
        }

    except Exception as e:
        print(f"❌ Error fetching {media_type}: {e}")
        return None

# ---------------- 主程序 ----------------

def main():
    print("🚀 任务开始...")
    is_monday = datetime.today().weekday() == 0
    setup_directories(reset=is_monday)
    
    existing_ids = load_existing_ids()
    new_items = []

    # 获取电影
    print("🎬 获取电影...")
    movie = fetch_content("movie", existing_ids)
    if movie: 
        new_items.append(movie)
        existing_ids.append(movie["id"])

    # 获取剧集
    print("📺 获取剧集...")
    tv = fetch_content("tv", existing_ids)
    if tv: 
        new_items.append(tv)

    # 保存
    if new_items:
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        
        current_data.extend(new_items)
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 更新完成，新增 {len(new_items)} 条。")
    else:
        print("⚠️ 无新内容更新。")

if __name__ == "__main__":
    main()
