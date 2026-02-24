import requests
import json
import os
import sys
import shutil
import wikipedia
import urllib.parse
import random  # 新增：用于引入随机性
from bs4 import BeautifulSoup
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

# 定义“安全/温和”的类型 ID 池
# 电影：喜剧(35), 剧情(18), 动画(16), 家庭(10751), 奇幻(14), 科幻(878), 爱情(10749), 音乐(10402)
SAFE_MOVIE_GENRES = ["35", "18", "16", "10751", "14", "878", "10749", "10402"]
# 剧集：喜剧(35), 剧情(18), 动画(16), 家庭(10751), 科幻/奇幻(10765), 纪录片(99)
SAFE_TV_GENRES = ["35", "18", "16", "10751", "10765", "99"]

# 设置维基百科语言为中文
wikipedia.set_lang("zh")

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

# ---------------- 信息增强模块 (Wiki & Baidu) ----------------

def get_wikipedia_summary(query):
    print(f"   🔍 尝试搜索 Wiki: {query}...")
    try:
        search_results = wikipedia.search(query)
        if not search_results: return ""
        page = wikipedia.page(search_results[0], auto_suggest=False)
        return f"{page.summary[:600]}...\n(📚 来源: 维基百科)"
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            page = wikipedia.page(e.options[0], auto_suggest=False)
            return f"{page.summary[:600]}...\n(📚 来源: 维基百科)"
        except: return ""
    except Exception:
        return ""

def get_baidu_baike_summary(title):
    print(f"   🔍 尝试搜索百度百科: {title}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        url = f"https://baike.baidu.com/item/{urllib.parse.quote(title)}"
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = 'utf-8'
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            summary_div = soup.find("div", class_="lemma-summary") or soup.find("div", class_="lemma-summary-box")
            if summary_div:
                text = summary_div.get_text().strip().replace("\n", "").replace("\xa0", "")
                return f"{text[:600]}...\n(🐼 来源: 百度百科)"
    except Exception:
        pass
    return ""

def get_english_fallback(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "en-US"}, timeout=5)
        return resp.json().get("overview", "")
    except: return ""

def get_external_ids(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/external_ids"
    try:
        return requests.get(url, headers=HEADERS, timeout=5).json()
    except: return {}

# ---------------- 核心获取逻辑 ----------------

def get_credits(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "zh-CN"}, timeout=5)
        data = resp.json()
        directors = [c["name"] for c in data.get("crew", []) if c["job"] == "Director"]
        actors = [c["name"] for c in data.get("cast", [])[:6]]
        return {"directors": directors, "actors": actors}
    except:
        return {"directors": [], "actors": []}

def get_reviews(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/reviews"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        data = resp.json()
        results = data.get("results", [])
        valid_reviews = [r for r in results if len(r["content"]) > 50]
        sorted_reviews = sorted(valid_reviews, key=lambda x: len(x["content"]), reverse=True)[:2]
        
        reviews_text = []
        for r in sorted_reviews:
            clean_content = r["content"].strip()[:400]
            reviews_text.append(f"👤 {r['author']}: {clean_content}...")
        return reviews_text
    except:
        return []

def fetch_content(media_type, existing_ids, target_genre_id):
    """
    修改点：新增 target_genre_id 参数，定向获取特定类型
    """
    url = f"{BASE_URL}/discover/{media_type}"
    
    # 随机选择第1页或第2页 (前40个热门)，增加抽取盲盒的随机性
    random_page = random.randint(1, 2)
    
    params = {
        "language": "zh-CN",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "with_genres": target_genre_id, # 包含我们随机抽中的好类型
        "page": random_page
    }

    # 双重保险：在“好类型”中，依然严格排除“坏类型”标签 (比如带有恐怖标签的喜剧片)
    if media_type == "movie":
        params["without_genres"] = "28,27,53,80" # 排除动作、恐怖、惊悚、犯罪
    else:
        params["without_genres"] = "80,10759"    # 排除犯罪、动作冒险
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200: return None
        
        results = resp.json().get("results", [])
        
        # 【核心随机逻辑】：将获取到的20条热门结果打乱，避免永远抓排名第1的
        random.shuffle(results)
        
        target_item = None
        for item in results:
            if item["id"] not in existing_ids:
                target_item = item
                break
        
        if not target_item: return None

        # 获取基础详情
        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params={"language": "zh-CN"}, timeout=15)
        detail = detail_resp.json()
        
        title = detail.get("title") or detail.get("name")
        original_title = detail.get("original_title") or detail.get("original_name")
        tmdb_overview = detail.get("overview", "")

        # ---------------- 智能简介增强逻辑 ----------------
        final_description = tmdb_overview

        if len(tmdb_overview) < 30:
            print(f"   ⚠️ TMDB简介不足，正在寻找补充资料: {title}")
            wiki_text = get_wikipedia_summary(title)
            if not wiki_text and title != original_title:
                wiki_text = get_wikipedia_summary(original_title)
            
            if wiki_text:
                final_description = wiki_text
            else:
                baidu_text = get_baidu_baike_summary(title)
                if baidu_text:
                    final_description = baidu_text
                else:
                    en_overview = get_english_fallback(media_type, detail["id"])
                    if en_overview:
                        final_description = f"(暂无中文介绍，原文如下)\n{en_overview}"

        # 获取其他元数据
        ext_ids = get_external_ids(media_type, detail["id"])
        imdb_id = ext_ids.get("imdb_id")
        credits = get_credits(media_type, detail["id"])
        reviews = get_reviews(media_type, detail["id"])
        
        poster = download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", f"{media_type}_{detail['id']}_p.jpg")
        backdrop = download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", f"{media_type}_{detail['id']}_b.jpg")

        return {
            "update_date": datetime.now().strftime("%Y-%m-%d"),
            "id": detail["id"],
            "imdb_id": imdb_id,
            "douban_link": f"https://search.douban.com/movie/subject_search?search_text={imdb_id}" if imdb_id else f"https://search.douban.com/movie/subject_search?search_text={title}",
            "type": "电影" if media_type == "movie" else "剧集",
            "title": title,
            "original_title": original_title,
            "rating": round(detail.get("vote_average", 0), 1),
            "date": detail.get("release_date") or detail.get("first_air_date"),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "director": credits["directors"],
            "actors": credits["actors"],
            "description": final_description,
            "reviews": reviews,
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

    # 🎬 1. 获取电影 (2部)
    print("🎬 开始获取电影 (目标2部)...")
    # 随机打乱类型池，确保每次跑的类型顺序都不一样
    shuffled_movie_genres = random.sample(SAFE_MOVIE_GENRES, len(SAFE_MOVIE_GENRES))
    movie_count = 0
    
    for genre_id in shuffled_movie_genres:
        if movie_count >= 2: break  # 获取满 2 部就停止
        
        movie = fetch_content("movie", existing_ids, genre_id)
        if movie:
            new_items.append(movie)
            existing_ids.append(movie["id"]) # 马上加进已存在列表，避免重复
            print(f"   ✅ 成功获取电影 [{movie_count+1}/2]: 《{movie['title']}》")
            movie_count += 1

    # 📺 2. 获取剧集 (2部)
    print("\n📺 开始获取剧集 (目标2部)...")
    shuffled_tv_genres = random.sample(SAFE_TV_GENRES, len(SAFE_TV_GENRES))
    tv_count = 0
    
    for genre_id in shuffled_tv_genres:
        if tv_count >= 2: break
        
        tv = fetch_content("tv", existing_ids, genre_id)
        if tv:
            new_items.append(tv)
            existing_ids.append(tv["id"])
            print(f"   ✅ 成功获取剧集 [{tv_count+1}/2]: 《{tv['title']}》")
            tv_count += 1

    # 保存结果
    print("\n💾 正在保存数据...")
    if new_items:
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        
        current_data.extend(new_items)
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        print(f"🎉 更新完成！本次新增 {len(new_items)} 条精选内容。")
    else:
        print("⚠️ 无新内容更新。")

if __name__ == "__main__":
    main()
