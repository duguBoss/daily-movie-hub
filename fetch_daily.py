import requests
import json
import os
import sys

# 1. 从 GitHub Secrets 获取那个长长的 Token
# 注意：GitHub Secret 里的 TMDB_API_KEY 的值，必须改成你刚才发的那个长字符串(eyJ...)
TOKEN = os.environ.get("TMDB_API_KEY")

if not TOKEN:
    print("❌ 错误: 环境变量 TMDB_API_KEY 未找到！")
    sys.exit(1)

# 2. 配置 Headers (这是关键修改)
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"  # 注意这里拼装了 Bearer
}

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
OUTPUT_DIR = "data"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# 确保目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)

def download_image(url, filename):
    if not url: return None
    print(f"⬇️ 正在下载图片: {url}")
    try:
        # 下载图片不需要带 Authorization header，直接下即可
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return f"images/{filename}"
        else:
            print(f"⚠️ 图片下载失败: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 图片下载出错: {e}")
    return None

def main():
    print("🚀 开始请求 TMDB API (使用 Bearer Token 模式)...")
    
    # 获取 Trending (今日热门)
    url = f"{BASE_URL}/trending/movie/day"
    # 参数里只放语言，不放 api_key 了
    params = {"language": "zh-CN"} 
    
    try:
        # ⚠️ 关键点：这里传入 headers=HEADERS
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if resp.status_code != 200:
            print(f"❌ API 请求失败! 状态码: {resp.status_code}")
            print(f"错误信息: {resp.text}")
            sys.exit(1)

        data = resp.json()
        if not data.get("results"):
            print("❌ 结果为空")
            sys.exit(1)

        top_movie = data["results"][0]
        movie_id = top_movie["id"]
        print(f"⭐ 获取到今日热门电影: {top_movie.get('title')} (ID: {movie_id})")

        # 获取详情 (同样带上 headers)
        detail_url = f"{BASE_URL}/movie/{movie_id}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params=params, timeout=15)
        detail = detail_resp.json()

        # 图片处理
        poster_src = f"{IMAGE_BASE_URL}{detail.get('poster_path')}" if detail.get('poster_path') else None
        backdrop_src = f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}" if detail.get('backdrop_path') else None

        local_poster = download_image(poster_src, "poster_daily.jpg")
        local_backdrop = download_image(backdrop_src, "backdrop_daily.jpg")

        final_data = {
            "id": detail.get("id"),
            "title": detail.get("title"),
            "tagline": detail.get("tagline"),
            "overview": detail.get("overview"),
            "vote_average": round(detail.get("vote_average", 0), 1),
            "release_date": detail.get("release_date"),
            "runtime": f"{detail.get('runtime')}分钟",
            "poster_path": local_poster, 
            "backdrop_path": local_backdrop,
            "update_time": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
        }

        # 写入文件
        json_path = os.path.join(OUTPUT_DIR, "latest.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 成功！数据已保存到: {json_path}")

    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
