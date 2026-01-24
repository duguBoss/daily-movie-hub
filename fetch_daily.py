import requests
import json
import os
import sys

# 1. 检查 Key 是否存在
API_KEY = os.environ.get("TMDB_API_KEY")
if not API_KEY:
    print("❌ 严重错误: 环境变量 TMDB_API_KEY 未找到！请在 Settings -> Secrets 里配置。")
    sys.exit(1) # 强制报错退出

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
OUTPUT_DIR = "data"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# 2. 打印当前工作目录，方便调试
print(f"📂 当前工作目录: {os.getcwd()}")

try:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"✅ 创建目录成功: {IMAGES_DIR}")
except Exception as e:
    print(f"❌ 创建目录失败: {e}")
    sys.exit(1)

def download_image(url, filename):
    if not url: return None
    print(f"⬇️ 正在下载图片: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return f"images/{filename}"
        else:
            print(f"⚠️ 图片下载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 图片下载出错: {e}")
    return None

def main():
    print("🚀 开始请求 TMDB API...")
    
    # 获取 Trending
    trending_url = f"{BASE_URL}/trending/movie/day"
    params = {"api_key": API_KEY, "language": "zh-CN"}
    
    resp = requests.get(trending_url, params=params, timeout=10)
    
    if resp.status_code != 200:
        print(f"❌ API 请求失败! 状态码: {resp.status_code}")
        print(f"错误信息: {resp.text}")
        sys.exit(1) # 强制报错退出

    data = resp.json()
    if not data.get("results"):
        print("❌ API 返回结果为空 (results 列表为空)")
        sys.exit(1)

    top_movie = data["results"][0]
    movie_id = top_movie["id"]
    print(f"⭐ 获取到今日热门电影 ID: {movie_id} - {top_movie.get('title')}")

    # 获取详情
    detail_url = f"{BASE_URL}/movie/{movie_id}"
    detail_resp = requests.get(detail_url, params=params, timeout=10)
    detail = detail_resp.json()

    # 图片处理
    poster_src = f"{IMAGE_BASE_URL}{detail.get('poster_path')}" if detail.get('poster_path') else None
    backdrop_src = f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}" if detail.get('backdrop_path') else None

    local_poster = download_image(poster_src, "poster_daily.jpg")
    local_backdrop = download_image(backdrop_src, "backdrop_daily.jpg")

    final_data = {
        "id": detail.get("id"),
        "title": detail.get("title"),
        "overview": detail.get("overview"),
        "vote_average": detail.get("vote_average"),
        "release_date": detail.get("release_date"),
        "poster_path": local_poster, 
        "backdrop_path": local_backdrop,
        "update_time": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
    }

    # 写入文件
    json_path = os.path.join(OUTPUT_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已成功写入: {json_path}")
    
    # 再次检查文件是否存在
    if os.path.exists(json_path):
        print("🔍 文件检查通过：latest.json 存在。")
    else:
        print("❌ 文件检查失败：latest.json 未找到！")
        sys.exit(1)

if __name__ == "__main__":
    main()
