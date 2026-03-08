import requests
import json
import os
import sys
import shutil
import random
import re
from datetime import datetime, timedelta

# ================= 1. 配置区域 =================

TMDB_TOKEN = os.environ.get("TMDB_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

# 仓库配置：用于生成图片链接
GITHUB_REPO = os.environ.get("GITHUB_REPO", "duguBoss/daily-movie-hub") 
CDN_PREFIX = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@main/data/images/"

if not TMDB_TOKEN or not GEMINI_API_KEY:
    print("❌ 错误: TMDB_API_KEY 或 GEMINI_API_KEY 未配置！")
    sys.exit(1)

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_TOKEN}"
}

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"

DATA_DIR = "data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "weekly_updates.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history_ids.txt")

# 屏蔽：恐怖(27), 战争(10752)
BLOCKED_GENRES = "27,10752"

# 严苛关键词过滤列表（剧情简介中包含以下词汇将直接跳过）
SENSITIVE_KEYWORDS = ["伦理", "禁忌", "乱伦", "色情", "肉欲", "情色", "禁片", "尺度大"]

# ================= 2. 流量爆款 Prompt (严苛合规版) =================

WX_PROMPT_TEMPLATE = """
# Role: 顶级影视大V / 正能量爆款制造机

## 🚫 绝对红线 (Safety Redlines) - 必须严格遵守
1. **严禁伦理禁忌**：绝对禁止讨论、安利或描述任何涉及违背社会公序良俗、伦理禁忌、不伦关系的内容。
2. **严禁色情暗示**：文案中不得出现任何性暗示、低俗描写、感官刺激或暗示性的“大尺度”词汇。
3. **内容调性**：保持高级感和正向引导。即使是探讨人性，也要以深度、觉醒或救赎为底色。

## 🎯 Profile
你是一位全网最懂年轻人痛点、审美高级的影视自媒体大V。
请根据影视元数据，撰写出极具画面感和情感共鸣的爆款推文。

## ✍️ Writing Style
- 拒绝平铺直叙，多用“剪辑式”短句。
- 第一人称“我”视角。多描写氛围、温度和人物内心的挣扎。
- 绝不剧透结局。

---

## Part 1: Title Generation (标题生成)
要求：18-28字。要有网感（封神、顶级、后劲大、治愈、深度）。严禁使用低俗标题。

---

## Part 2: HTML Content Generation
请将文案填充到 HTML 模板。**压缩为一行的代码输出。**

### HTML 填充指令：
- [首]：填一个有力量的汉字（如 燃/亮/深/惊）。
- [黄金开场]：基于剧情描述一个极具张力的瞬间，250字。
- [深度种草]：聚焦主角的困境与内心抉择，400字。
- [拉片]：通过文字构建这部片的视听高级感，300字。
- [价值升华]：联系现实生活，给读者一个思考或治愈的理由，350字。
- [金句]：提取扎心台词。

<section style="margin:0;padding:0;background-color:#fff;font-family:-apple-system-font,BlinkMacSystemFont,'Helvetica Neue','PingFang SC',sans-serif;letter-spacing:1.5px;color:#333;text-align:justify;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzXgUR7FJnf11qGIo8nmKt6RxibXrb5s4RFb9UZ9UOHQy7fqQyI377Licw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;margin:0;"><section style="display:block;padding:20px 15px;overflow:hidden;"><section style="float:left;font-size:48px;line-height:0.9;margin-top:4px;padding-right:8px;font-weight:bold;color:#e63946;font-family:Georgia,serif;">[首]</section><section style="font-size:16px;line-height:1.8;">[黄金开场]</section></section><section style="margin:0;padding:25px 15px;background-color:#1a1a1a;color:#fff;"><section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:15px;"><section><section style="font-size:22px;font-weight:bold;line-height:1.2;color:#fff;">[title]</section><section style="font-size:14px;color:#999;margin-top:4px;">[original_title]</section></section><section style="text-align:right;"><section style="font-size:28px;font-weight:bold;color:#e63946;line-height:1;font-family:Georgia;">[rating]</section><section style="font-size:10px;color:#666;letter-spacing:1px;">TMDB</section></section></section><section style="font-size:13px;line-height:1.8;color:#ccc;border-top:1px solid #333;padding-top:15px;"><p style="margin:0;"><strong>类型：</strong>[genres]</p><p style="margin:0;"><strong>导演：</strong>[director]</p><p style="margin:0;"><strong>主演：</strong>[actors]</p><p style="margin:0;"><strong>日期：</strong>[date]</p></section></section><section style="display:block;font-size:16px;line-height:1.8;padding:25px 15px;background-color:#fff;">[深度种草]</section><section style="margin:0;padding:30px 15px;background-color:#f4f4f4;border-left:8px solid #e63946;"><section style="font-size:20px;font-weight:bold;color:#111;line-height:1.4;padding-bottom:10px;">[独家短评]</section><section style="font-size:16px;line-height:1.8;color:#555;">[拉片]</section></section><img src="[backdrop_url]" style="width:100%;display:block;vertical-align:top;"><section style="margin:0;padding:30px 15px;background-color:#1a1a1a;"><section style="font-size:20px;font-weight:bold;color:#e63946;line-height:1.4;padding-bottom:10px;">[灵魂拷问]</section><section style="font-size:16px;line-height:1.8;color:#bbb;">[价值升华]</section></section><section style="display:block;text-align:center;padding:35px 15px;background-color:#fff;"><section style="width:20px;height:2px;background:#e63946;margin:0 auto 15px;"></section><section style="line-height:1.6;font-size:18px;font-weight:bold;color:#111;font-family:serif;">“[金句台词]”</section><section style="width:20px;height:2px;background:#e63946;margin:15px auto 0;"></section></section><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzk57DCmhVC16o9ILH0Tn1YPEiarfLRRQSVFN2mJdeYibGnBPialPIzvojw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;"></section>

## Meta Data (JSON):
{{input}}

## Final Output Format (Strict JSON):
{
   "title": "爆款标题",
   "content": "压缩后的HTML"
}
"""

# ================= 3. 辅助逻辑 =================

def setup_directories(reset=False):
    # 修改：如果是周一，清空图片目录以释放空间
    if reset and os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'a').close()

def load_history():
    history_set = set()
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            history_set.add(line.strip())
    return history_set

def save_to_history(new_id_list):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        for uid in new_id_list:
            f.write(f"{uid}\n")

def download_image(url, filename):
    if not url: return None
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
                f.write(resp.content)
            return filename
    except: pass
    return None

# ================= 4. Gemini 生成逻辑 =================

def generate_gemini_content(media_data, image_filename):
    print(f"   🤖 Gemini 撰写中: 《{media_data['title']}》...")
    media_data["backdrop_url"] = f"{CDN_PREFIX}{image_filename}" if image_filename else ""
    input_json_str = json.dumps(media_data, ensure_ascii=False)
    final_prompt = WX_PROMPT_TEMPLATE.replace("{{input}}", input_json_str)

    url = f"https://generativelanguage.googleapis.com/v1alpha/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": final_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}
    }

    try:
        resp = requests.post(url, json=payload, timeout=90)
        if resp.status_code == 200:
            res_json = resp.json()
            content_text = res_json['candidates'][0]['content']['parts'][0]['text']
            content_text = re.sub(r'^```json\s*', '', content_text).replace('```', '')
            return json.loads(content_text)
    except: pass
    return None

# ================= 5. TMDB 获取逻辑 =================

def fetch_content(media_type, history_set, strategy="trending"):
    today = datetime.now()
    params = {
        "language": "zh-CN",
        "include_adult": "false", # 核心过滤：不包含成人内容
        "without_genres": BLOCKED_GENRES,
        "vote_count.gte": 50
    }

    if strategy == "fresh":
        params["sort_by"] = "popularity.desc"
        target_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        if media_type == "movie": params["primary_release_date.gte"] = target_date
        else: params["first_air_date.gte"] = target_date
        params["page"] = random.randint(1, 3)
    elif strategy == "hidden_gem":
        params["sort_by"] = "vote_average.desc"
        params["vote_average.gte"] = 7.8
        params["vote_count.gte"] = 150
        params["page"] = random.randint(1, 10)
    else:
        params["sort_by"] = "popularity.desc"
        params["page"] = random.randint(1, 30)

    try:
        resp = requests.get(f"{BASE_URL}/discover/{media_type}", headers=HEADERS, params=params, timeout=15)
        results = resp.json().get("results", [])
        random.shuffle(results)
        
        target = None
        for item in results:
            uid = f"{media_type}_{item['id']}"
            overview = item.get("overview", "")
            # 查重 + 文本长度过滤 + 严苛关键词过滤
            if uid not in history_set and len(overview) > 10:
                if not any(word in overview for word in SENSITIVE_KEYWORDS):
                    target = item
                    break
        
        if not target: return None, None

        # 详情补充
        detail = requests.get(f"{BASE_URL}/{media_type}/{target['id']}", headers=HEADERS, params={"language":"zh-CN"}).json()
        credits = requests.get(f"{BASE_URL}/{media_type}/{target['id']}/credits", headers=HEADERS, params={"language":"zh-CN"}).json()
        reviews_raw = requests.get(f"{BASE_URL}/{media_type}/{target['id']}/reviews", headers=HEADERS).json().get("results", [])

        # 图片下载
        backdrop_fn = f"{media_type}_{detail['id']}_b.jpg"
        backdrop_file = download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", backdrop_fn)
        poster_fn = f"{media_type}_{detail['id']}_p.jpg"
        download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", poster_fn)

        raw_data = {
            "id": detail["id"],
            "title": detail.get("title") or detail.get("name"),
            "original_title": detail.get("original_title") or detail.get("original_name"),
            "type": "电影" if media_type == "movie" else "剧集",
            "rating": round(detail.get("vote_average", 0), 1),
            "date": detail.get("release_date") or detail.get("first_air_date"),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "director": [c["name"] for c in credits.get("crew", []) if c["job"] == "Director"][:1],
            "actors": [c["name"] for c in credits.get("cast", [])[:4]],
            "overview": detail.get("overview", ""),
            "reviews": [r["content"][:200] for r in reviews_raw[:3]]
        }
        return raw_data, backdrop_file

    except: return None, None

# ================= 6. 主程序 =================

def main():
    print(f"🚀 任务启动: {datetime.now().strftime('%Y-%m-%d')}")
    # 保持目录结构
    setup_directories(reset=(datetime.today().weekday() == 0))
    
    # 全局历史防重查重
    history_set = load_history()
    
    new_items = []
    new_history_ids = []

    tasks = [
        ("movie", "fresh", "🆕 最新电影"),
        ("movie", "trending", "🔥 热门电影"),
        ("tv", "fresh", "🆕 最新剧集"),
        ("tv", "hidden_gem", "💎 高分剧集"),
    ]

    for m_type, strategy, label in tasks:
        print(f"\n{label} 探索中...")
        raw_data, backdrop_file = fetch_content(m_type, history_set, strategy)
        
        if raw_data:
            ai_res = generate_gemini_content(raw_data, backdrop_file)
            final_item = raw_data.copy()
            final_item["update_date"] = datetime.now().strftime("%Y-%m-%d")
            final_item["backdrop_path"] = f"images/{backdrop_file}" if backdrop_file else ""
            if ai_res:
                final_item["wx_title"] = ai_res.get("title")
                final_item["wx_content"] = ai_res.get("content")
            else:
                final_item["wx_title"] = f"今日精选：{raw_data['title']}"
                final_item["wx_content"] = f"<p>{raw_data['overview']}</p>"

            new_items.append(final_item)
            uid = f"{m_type}_{raw_data['id']}"
            new_history_ids.append(uid)
        else:
            print("   ⚠️ 未发现合适内容。")

    if new_items:
        # 修改：【日更覆盖逻辑】直接保存当日内容，不读取旧 JSON
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_items, f, ensure_ascii=False, indent=2)
        
        # 永久 ID 账本仍然追加，确保永远不重复抓取历史发过的片子
        save_to_history(new_history_ids)
        print(f"\n🎉 运行成功！当日 {len(new_items)} 条内容已更新覆盖。")
    else:
        print("\n⚠️ 本次运行无新内容。")

if __name__ == "__main__":
    main()
