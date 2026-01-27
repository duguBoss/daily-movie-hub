import requests
import json
import os
import sys
import shutil
import wikipedia
import urllib.parse
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
    """
    获取维基百科简介 (无需API Key)
    """
    print(f"   🔍 尝试搜索 Wiki: {query}...")
    try:
        # 搜索最匹配的条目
        search_results = wikipedia.search(query)
        if not search_results:
            return ""
        
        # 获取第一个结果的页面
        page = wikipedia.page(search_results[0], auto_suggest=False)
        summary = page.summary[:600] # 截取前600字
        return f"{summary}...\n(📚 来源: 维基百科)"
    
    except wikipedia.exceptions.DisambiguationError as e:
        # 如果遇到歧义（例如“狂飙”有电视剧和词语），尝试取第一个选项
        try:
            page = wikipedia.page(e.options[0], auto_suggest=False)
            return f"{page.summary[:600]}...\n(📚 来源: 维基百科)"
        except:
            return ""
    except Exception as e:
        # print(f"   Wiki获取微小错误: {e}") # 忽略非致命错误
        return ""

def get_baidu_baike_summary(title):
    """
    获取百度百科简介 (通过爬虫，无需API Key)
    """
    print(f"   🔍 尝试搜索百度百科: {title}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # URL 编码
        encoded_title = urllib.parse.quote(title)
        url = f"https://baike.baidu.com/item/{encoded_title}"
        
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = 'utf-8' # 强制utf-8
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 百度百科简介的常见 class
            summary_div = soup.find("div", class_="lemma-summary") or \
                          soup.find("div", class_="lemma-summary-box") or \
                          soup.find("div", attrs={"class": lambda x: x and "lemmaSummary" in x})
            
            if summary_div:
                text = summary_div.get_text().strip().replace("\n", "").replace("\xa0", "")
                return f"{text[:600]}...\n(🐼 来源: 百度百科)"
    except Exception:
        pass
    return ""

def get_english_fallback(media_type, media_id):
    """获取 TMDB 英文简介作为保底"""
    url = f"{BASE_URL}/{media_type}/{media_id}"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "en-US"}, timeout=5)
        return resp.json().get("overview", "")
    except:
        return ""

def get_external_ids(media_type, media_id):
    """获取外部ID (IMDb)"""
    url = f"{BASE_URL}/{media_type}/{media_id}/external_ids"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        return resp.json()
    except:
        return {}

# ---------------- 核心获取逻辑 ----------------

def get_credits(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "zh-CN"}, timeout=5)
        data = resp.json()
        directors = [c["name"] for c in data.get("crew", []) if c["job"] == "Director"]
        actors = [c["name"] for c in data.get("cast", [])[:6]] # 取前6位
        return {"directors": directors, "actors": actors}
    except:
        return {"directors": [], "actors": []}

def get_reviews(media_type, media_id):
    """获取评论 (优先显示长评)"""
    url = f"{BASE_URL}/{media_type}/{media_id}/reviews"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        data = resp.json()
        results = data.get("results", [])
        # 简单过滤掉太短的评论，按长度降序
        valid_reviews = [r for r in results if len(r["content"]) > 50]
        sorted_reviews = sorted(valid_reviews, key=lambda x: len(x["content"]), reverse=True)[:2]
        
        reviews_text = []
        for r in sorted_reviews:
            # 截断过长评论
            clean_content = r["content"].strip()[:400]
            reviews_text.append(f"👤 {r['author']}: {clean_content}...")
        return reviews_text
    except:
        return []

def fetch_content(media_type, existing_ids):
    # 1. 获取 Trending 列表
    url = f"{BASE_URL}/trending/{media_type}/day"
    params = {"language": "zh-CN"}
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200: return None
        
        results = resp.json().get("results", [])
        target_item = None
        
        # 去重查找
        for item in results:
            if item["id"] not in existing_ids:
                target_item = item
                break
        
        if not target_item: return None

        # 2. 获取基础详情
        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params=params, timeout=15)
        detail = detail_resp.json()
        
        title = detail.get("title") or detail.get("name")
        original_title = detail.get("original_title") or detail.get("original_name")
        tmdb_overview = detail.get("overview", "")

        # ---------------- 智能简介增强逻辑 ----------------
        final_description = tmdb_overview
        source_note = ""

        # 策略 A: 如果 TMDB 中文简介太短 (<30字) 或为空
        if len(tmdb_overview) < 30:
            print(f"   ⚠️ TMDB简介不足，正在寻找补充资料: {title}")
            
            # 尝试 1: 维基百科 (首选)
            wiki_text = get_wikipedia_summary(title)
            if not wiki_text and title != original_title:
                # 如果中文搜不到，试一下搜原名
                wiki_text = get_wikipedia_summary(original_title)
            
            if wiki_text:
                final_description = wiki_text
            else:
                # 尝试 2: 百度百科 (备选)
                baidu_text = get_baidu_baike_summary(title)
                if baidu_text:
                    final_description = baidu_text
                else:
                    # 尝试 3: 英文简介 + 提示
                    en_overview = get_english_fallback(media_type, detail["id"])
                    if en_overview:
                        final_description = f"(暂无中文介绍，原文如下)\n{en_overview}"
        
        # ------------------------------------------------

        # 3. 获取其他元数据
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
            # 生成豆瓣搜索链接，而不是爬虫，规避风险
            "douban_link": f"https://search.douban.com/movie/subject_search?search_text={imdb_id}" if imdb_id else f"https://search.douban.com/movie/subject_search?search_text={title}",
            "type": "电影" if media_type == "movie" else "剧集",
            "title": title,
            "original_title": original_title,
            "rating": round(detail.get("vote_average", 0), 1),
            "date": detail.get("release_date") or detail.get("first_air_date"),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "director": credits["directors"],
            "actors": credits["actors"],
            "description": final_description, # 这里是增强后的简介
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

    # 获取电影
    print("🎬 获取电影...")
    movie = fetch_content("movie", existing_ids)
    if movie: 
        new_items.append(movie)
        existing_ids.append(movie["id"])
        print(f"   ✅ 成功获取: 《{movie['title']}》")

    # 获取剧集
    print("📺 获取剧集...")
    tv = fetch_content("tv", existing_ids)
    if tv: 
        new_items.append(tv)
        print(f"   ✅ 成功获取: 《{tv['title']}》")

    # 保存结果
    if new_items:
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        
        current_data.extend(new_items)
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        print(f"🎉 更新完成，新增 {len(new_items)} 条内容。")
    else:
        print("⚠️ 无新内容更新。")

if __name__ == "__main__":
    main()
