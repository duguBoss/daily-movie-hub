import requests
import json
import os
import sys

# 从环境变量获取 Key
API_KEY = os.environ.get("TMDB_API_KEY")
if not API_KEY:
    print("Error: TMDB_API_KEY is missing")
    sys.exit(1)

# 配置
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500" # 海报尺寸
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original" # 背景图尺寸
OUTPUT_DIR = "data" # 数据保存目录
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# 确保目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)

def download_image(url, filename):
    """下载图片并保存"""
    if not url:
        return None
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return f"images/{filename}" # 返回相对路径
    except Exception as e:
        print(f"Failed to download image: {e}")
    return None

def main():
    # 1. 获取今日 Trending 电影 (只要第一名)
    trending_url = f"{BASE_URL}/trending/movie/day"
    params = {"api_key": API_KEY, "language": "zh-CN"}
    
    resp = requests.get(trending_url, params=params)
    data = resp.json()
    
    if not data.get("results"):
        print("No trending data found.")
        return

    top_movie = data["results"][0]
    movie_id = top_movie["id"]
    
    # 2. 获取更详细的信息 (包含时长、类型等)
    detail_url = f"{BASE_URL}/movie/{movie_id}"
    detail_resp = requests.get(detail_url, params=params)
    detail = detail_resp.json()

    # 3. 提取我们需要的数据
    # 拼接完整的图片URL进行下载
    poster_src = f"{IMAGE_BASE_URL}{detail.get('poster_path')}" if detail.get('poster_path') else None
    backdrop_src = f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}" if detail.get('backdrop_path') else None

    # 下载图片 (覆盖旧文件，保持仓库轻量)
    # 如果你想保留历史，可以在文件名里加上日期，但仓库会越来越大
    local_poster = download_image(poster_src, "poster_daily.jpg")
    local_backdrop = download_image(backdrop_src, "backdrop_daily.jpg")

    final_data = {
        "id": detail.get("id"),
        "title": detail.get("title"),
        "original_title": detail.get("original_title"),
        "tagline": detail.get("tagline"), # 宣传语
        "overview": detail.get("overview"),
        "genres": [g["name"] for g in detail.get("genres", [])],
        "release_date": detail.get("release_date"),
        "runtime": f"{detail.get('runtime')}分钟",
        "vote_average": round(detail.get("vote_average", 0), 1),
        "imdb_id": detail.get("imdb_id"),
        # 这里的路径是相对于 data/ 目录的
        "poster_path": local_poster, 
        "backdrop_path": local_backdrop,
        "update_time": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
    }

    # 4. 写入 JSON
    json_path = os.path.join(OUTPUT_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully updated data for: {final_data['title']}")

if __name__ == "__main__":
    main()
