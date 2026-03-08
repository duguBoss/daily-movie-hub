import requests
import json
import os
import sys
import shutil
import random
from datetime import datetime, timedelta

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

# 【优化1：黑名单机制】
# 只屏蔽：恐怖(27 - 容易血腥), 战争(10752 - 容易血腥), 纪录片(99 - 阅读量通常较低，可根据需要保留)
# 成人内容通过 include_adult=false 屏蔽
BLOCKED_GENRES = "27,10752" 

# ---------------- 辅助功能 ----------------

def setup_directories(reset=False):
    if reset:
        print("🔄 周一重置: 清理旧数据...")
        if os.path.exists(DATA_DIR):
            try:
                # 保留 json，只清空图片，防止 history 丢失
                for filename in os.listdir(IMAGES_DIR):
                    file_path = os.path.join(IMAGES_DIR, filename)
                    os.unlink(file_path)
            except:
                pass
        os.makedirs(IMAGES_DIR, exist_ok=True)
    
    if not os.path.exists(JSON_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
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
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)
            return f"images/{filename}"
    except:
        pass
    return None

# ---------------- 网感文案生成引擎 (核心优化) ----------------

def generate_clickbait_title(title, rating, tagline):
    """生成具有点击欲望的标题"""
    prefixes = ["本周必看", "口碑炸裂", "深夜推荐", "剧荒自救", "高分神作"]
    prefix = random.choice(prefixes)
    
    # 如果有短评，利用短评做副标题
    if tagline and len(tagline) < 15:
        return f"{prefix} | 《{title}》：{tagline}"
    
    return f"{prefix} | 豆瓣高分《{title}》评分{rating}，错过后悔！"

def format_social_media_copy(detail, credits):
    """
    将枯燥的数据转化为社交媒体风格的文案
    """
    title = detail.get("title") or detail.get("name")
    original_title = detail.get("original_title") or detail.get("original_name")
    rating = round(detail.get("vote_average", 0), 1)
    date = detail.get("release_date") or detail.get("first_air_date")
    year = date.split("-")[0] if date else "未知年份"
    genres = [g["name"] for g in detail.get("genres", [])[:3]]
    overview = detail.get("overview", "")
    tagline = detail.get("tagline", "")
    
    director = credits.get("directors", [])
    director_str = f"🎬 导演：{director[0]}" if director else ""
    actors = credits.get("actors", [])
    actors_str = f"🌟 主演：{' / '.join(actors[:3])}" if actors else ""

    # 文案模板
    copy = f"""
🎥 **片名**：{title} ({year})
⭐️ **评分**：{rating} / 10
🏷 **类型**：{' #'.join(genres)}

{tagline if tagline else "🔥 剧情高能，全程无尿点！"}

{director_str}
{actors_str}

📖 **剧情速递**：
{overview[:180]}...

👉 **推荐理由**：
这部作品在 TMDB 拥有极高的人气。无论是剧情节奏还是演员演技都非常在线。{ "特别适合周末窝在沙发上刷！" if "剧情" in genres else "喜欢这类题材的朋友绝对不能错过！" }

#影视推荐 #好剧安利 #{title} #周末看什么
"""
    return copy.strip()

# ---------------- 多维选品逻辑 (Richness Strategy) ----------------

def get_discovery_params(media_type, strategy):
    """
    根据不同的策略生成 API 参数，确保内容丰富度
    """
    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    base_params = {
        "language": "zh-CN",
        "include_adult": "false",
        "without_genres": BLOCKED_GENRES,
        "vote_count.gte": 100, # 基础门槛，过滤掉没人看过的
    }

    print(f"   ⚙️ 正在应用选品策略: {strategy} ...")

    if strategy == "fresh":
        # 策略A：近期新片 (Richness: New)
        # 逻辑：最近3个月上映，按热度排序
        if media_type == "movie":
            base_params["primary_release_date.gte"] = three_months_ago
            base_params["primary_release_date.lte"] = today_str
        else:
            base_params["first_air_date.gte"] = three_months_ago
            base_params["first_air_date.lte"] = today_str
        base_params["sort_by"] = "popularity.desc"
        base_params["page"] = random.randint(1, 3) # 新片不用翻太后

    elif strategy == "hidden_gem":
        # 策略B：高分遗珠 (Richness: Quality)
        # 逻辑：评分很高(>7.5)，但不是最热门的
        base_params["vote_average.gte"] = 7.5
        base_params["sort_by"] = "vote_average.desc"
        base_params["vote_count.gte"] = 300 # 稍微提高人数门槛
        base_params["page"] = random.randint(1, 10)

    else: # trending
        # 策略C：经典热门 (Richness: Popularity)
        # 逻辑：传统的按热度，但是页码放得很宽，防止重复
        base_params["sort_by"] = "popularity.desc"
        base_params["page"] = random.randint(1, 20) # 翻到第20页去抓

    return base_params

# ---------------- 核心获取逻辑 ----------------

def get_credits(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "zh-CN"}, timeout=5)
        data = resp.json()
        directors = [c["name"] for c in data.get("crew", []) if c["job"] == "Director"]
        actors = [c["name"] for c in data.get("cast", [])[:5]]
        return {"directors": directors, "actors": actors}
    except:
        return {"directors": [], "actors": []}

def fetch_content(media_type, existing_ids, strategy="trending"):
    url = f"{BASE_URL}/discover/{media_type}"
    params = get_discovery_params(media_type, strategy)
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200: 
            print(f"   ⚠️ API Error: {resp.status_code}")
            return None
        
        results = resp.json().get("results", [])
        random.shuffle(results) # 再次打乱结果
        
        target_item = None
        for item in results:
            # 必须有简介，且不重复
            if item["id"] not in existing_ids and item.get("overview") and len(item.get("overview")) > 10:
                target_item = item
                break
        
        if not target_item: return None

        # 获取详情
        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params={"language": "zh-CN"}, timeout=15)
        detail = detail_resp.json()
        
        credits = get_credits(media_type, detail["id"])
        
        # 生成网感文案
        social_copy = format_social_media_copy(detail, credits)
        clickbait_title = generate_clickbait_title(
            detail.get("title") or detail.get("name"), 
            round(detail.get("vote_average", 0), 1),
            detail.get("tagline")
        )

        # 图片下载
        poster = download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", f"{media_type}_{detail['id']}_p.jpg")
        backdrop = download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", f"{media_type}_{detail['id']}_b.jpg")

        return {
            "update_date": datetime.now().strftime("%Y-%m-%d"),
            "id": detail["id"],
            "type": "电影" if media_type == "movie" else "剧集",
            "title": detail.get("title") or detail.get("name"),
            "clickbait_title": clickbait_title, # 这是你的文章标题
            "rating": round(detail.get("vote_average", 0), 1),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "description": social_copy, # 这是你的文章正文
            "poster_path": poster,
            "backdrop_path": backdrop,
            "release_date": detail.get("release_date") or detail.get("first_air_date")
        }

    except Exception as e:
        print(f"❌ Error fetching {media_type}: {e}")
        return None

# ---------------- 主程序 ----------------

def main():
    print("🚀 任务开始...")
    # 周一重置图片文件夹，节省空间
    is_monday = datetime.today().weekday() == 0
    setup_directories(reset=is_monday)
    
    existing_ids = load_existing_ids()
    new_items = []

    # 混合抓取计划：确保丰富度
    # 1部 新出的电影
    # 1部 热门的电影
    # 1部 新出的剧集
    # 1部 高分的剧集
    
    tasks = [
        ("movie", "fresh", "🆕 最新电影"),
        ("movie", "trending", "🔥 热门电影"),
        ("tv", "fresh", "🆕 最新剧集"),
        ("tv", "hidden_gem", "💎 高分剧集"),
    ]

    for media_type, strategy, label in tasks:
        print(f"\n{label} 挖掘中...")
        item = fetch_content(media_type, existing_ids, strategy)
        if item:
            new_items.append(item)
            existing_ids.append(item["id"])
            print(f"   ✅ 成功捕获: 《{item['title']}》")
        else:
            print("   ⚠️ 未找到合适内容，跳过。")

    # 保存结果
    print("\n💾 正在保存数据...")
    if new_items:
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                try: current_data = json.load(f)
                except: current_data = []
        
        # 新数据插在最前面
        current_data = new_items + current_data
        # 保持列表长度不超过 60 条，防止文件过大
        current_data = current_data[:60]
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        print(f"🎉 更新完成！新增 {len(new_items)} 条内容。")
    else:
        print("⚠️ 本次无内容更新。")

if __name__ == "__main__":
    main()
