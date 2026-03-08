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
# 使用 Gemini 3.1 Flash Lite 预览版
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

# 仓库配置：用于生成 HTML 里的图片链接
# 请确保环境变量里有 GITHUB_REPO (格式: 用户名/仓库名)
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

# ================= 2. 流量爆款 Prompt (纯文本版) =================

WX_PROMPT_TEMPLATE = """
# Role: 顶级影视大V / 爆款制造机 (Viral Content Creator)

## Profile
你是一位全网最懂年轻人痛点、审美毒辣的**影视自媒体大V**。
你的任务是根据我提供的影视元数据（剧情简介、影评、导演等），撰写出极具画面感和情绪价值的爆款推文。

## 🧠 Traffic Psychology (流量密码)
1. **情绪共鸣**：戳中现代人的孤独、内耗、焦虑或渴望。
2. **审美碾压**：用高级的文字描写，让读者觉得“看这部片子能提升我的品味”。
3. **极致悬念**：只谈张力和人物困境，不谈结局，勾引读者点开。

## ✍️ Writing Style
- 拒绝平铺直叙，多用“剪辑式”短句。
- 第一人称“我”视角。多描写氛围、温度和人物内心的波澜。
- 绝不剧透。

---

## Part 1: Title Generation (标题生成)
公式：[情绪标签/痛点] + [反差钩子] + 《作品名》
要求：18-28字。要有网感（杀疯了、后劲大、窒息、封神、深夜破防）。

---

## Part 2: HTML Content Generation (正文填充)
请将文案填充到 HTML 模板。**保留 HTML 标签和样式，输出压缩为一行的代码。**

### HTML Template 指令：
- [首]：填一个冲击力强的汉字（如 痛/欲/烈/破）。
- [黄金开场]：基于剧情简介描述一个震撼的瞬间，250字。
- [深度种草]：聚焦主角的两难困境和网友神评，400字。
- [拉片]：通过文字构建这部片的视听高级感，300字。
- [价值升华]：联系现实生活，给读者一个救赎或思考的理由，350字。
- [金句]：提取或原创一句扎心台词。

<section style="margin:0;padding:0;background-color:#fff;font-family:-apple-system-font,BlinkMacSystemFont,'Helvetica Neue','PingFang SC',sans-serif;letter-spacing:1.5px;color:#333;text-align:justify;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzXgUR7FJnf11qGIo8nmKt6RxibXrb5s4RFb9UZ9UOHQy7fqQyI377Licw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;margin:0;"><section style="display:block;padding:20px 15px;overflow:hidden;"><section style="float:left;font-size:48px;line-height:0.9;margin-top:4px;padding-right:8px;font-weight:bold;color:#e63946;font-family:Georgia,serif;">[首]</section><section style="font-size:16px;line-height:1.8;">[黄金开场]</section></section><section style="margin:0;padding:25px 15px;background-color:#1a1a1a;color:#fff;"><section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:15px;"><section><section style="font-size:22px;font-weight:bold;line-height:1.2;color:#fff;">[title]</section><section style="font-size:14px;color:#999;margin-top:4px;">[original_title]</section></section><section style="text-align:right;"><section style="font-size:28px;font-weight:bold;color:#e63946;line-height:1;font-family:Georgia;">[rating]</section><section style="font-size:10px;color:#666;letter-spacing:1px;">TMDB</section></section></section><section style="font-size:13px;line-height:1.8;color:#ccc;border-top:1px solid #333;padding-top:15px;"><p style="margin:0;"><strong>类型：</strong>[genres]</p><p style="margin:0;"><strong>导演：</strong>[director]</p><p style="margin:0;"><strong>主演：</strong>[actors]</p><p style="margin:0;"><strong>上映：</strong>[date]</p></section></section><section style="display:block;font-size:16px;line-height:1.8;padding:25px 15px;background-color:#fff;">[深度种草]</section><section style="margin:0;padding:30px 15px;background-color:#f4f4f4;border-left:8px solid #e63946;"><section style="font-size:20px;font-weight:bold;color:#111;line-height:1.4;padding-bottom:10px;">[独家短评]</section><section style="font-size:16px;line-height:1.8;color:#555;">[拉片]</section></section><img src="[backdrop_url]" style="width:100%;display:block;vertical-align:top;"><section style="margin:0;padding:30px 15px;background-color:#1a1a1a;"><section style="font-size:20px;font-weight:bold;color:#e63946;line-height:1.4;padding-bottom:10px;">[灵魂拷问]</section><section style="font-size:16px;line-height:1.8;color:#bbb;">[价值升华]</section></section><section style="display:block;text-align:center;padding:35px 15px;background-color:#fff;"><section style="width:20px;height:2px;background:#e63946;margin:0 auto 15px;"></section><section style="line-height:1.6;font-size:18px;font-weight:bold;color:#111;font-family:serif;">“[金句台词]”</section><section style="width:20px;height:2px;background:#e63946;margin:15px auto 0;"></section></section><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzk57DCmhVC16o9ILH0Tn1YPEiarfLRRQSVFN2mJdeYibGnBPialPIzvojw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;"></section>

## Input Meta Data (JSON):
{{input}}

## Final Output Format (Strict JSON):
{
   "title": "爆款标题",
   "content": "压缩后的HTML内容"
}
"""

# ================= 3. 辅助逻辑 =================

def setup_directories(reset=False):
    if reset:
        print("🔄 重置图片目录...")
        if os.path.exists(IMAGES_DIR):
            shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'a').close()

def load_history():
    history_set = set()
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            history_set.add(line.strip())
    # 兼容历史数据
    if not history_set and os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    prefix = "movie" if item.get("type") == "电影" else "tv"
                    history_set.add(f"{prefix}_{item['id']}")
        except: pass
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

# ================= 4. Gemini 纯文本生成逻辑 =================

def generate_gemini_content(media_data, image_filename):
    """
    纯文本生成：不再处理 Base64 图片，仅基于文字信息
    """
    print(f"   🤖 Gemini ({GEMINI_MODEL}) 正在撰写: 《{media_data['title']}》...")
    
    # 注入 CDN 链接供 HTML 模板使用 (即使 AI 不看图片，HTML 里也需要显示它)
    media_data["backdrop_url"] = f"{CDN_PREFIX}{image_filename}" if image_filename else ""
    
    # 构造 Prompt
    input_json_str = json.dumps(media_data, ensure_ascii=False)
    final_prompt = WX_PROMPT_TEMPLATE.replace("{{input}}", input_json_str)

    # API 端点 (v1alpha)
    url = f"https://generativelanguage.googleapis.com/v1alpha/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": final_prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.8
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=90)
        if resp.status_code == 200:
            res_json = resp.json()
            content_text = res_json['candidates'][0]['content']['parts'][0]['text']
            # 清理代码块标记
            content_text = re.sub(r'^```json\s*', '', content_text)
            content_text = re.sub(r'\s*```$', '', content_text)
            return json.loads(content_text)
        else:
            print(f"   ❌ API 错误: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Gemini 生成异常: {e}")
    return None

# ================= 5. TMDB 获取逻辑 =================

def fetch_content(media_type, history_set, strategy="trending"):
    today = datetime.now()
    params = {
        "language": "zh-CN",
        "include_adult": "false",
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
            if uid not in history_set and item.get("overview") and len(item.get("overview")) > 10:
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
            "tagline": detail.get("tagline", ""),
            "reviews": [r["content"][:200] for r in reviews_raw[:3]]
        }
        return raw_data, backdrop_file

    except Exception as e:
        print(f"❌ TMDB 抓取失败: {e}")
        return None, None

# ================= 6. 主程序 =================

def main():
    print(f"🚀 流程启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    is_monday = datetime.today().weekday() == 0
    setup_directories(reset=is_monday)
    
    history_set = load_history()
    new_items = []
    new_history_ids = []

    # 每日选品配置
    tasks = [
        ("movie", "fresh", "🆕 最新电影"),
        ("movie", "trending", "🔥 热门电影"),
        ("tv", "fresh", "🆕 最新剧集"),
        ("tv", "hidden_gem", "💎 高分剧集"),
    ]

    for m_type, strategy, label in tasks:
        print(f"\n{label} 匹配中...")
        raw_data, backdrop_file = fetch_content(m_type, history_set, strategy)
        
        if raw_data:
            print(f"   ✅ 选中: 《{raw_data['title']}》")
            ai_res = generate_gemini_content(raw_data, backdrop_file)
            
            final_item = raw_data.copy()
            final_item["update_date"] = datetime.now().strftime("%Y-%m-%d")
            final_item["backdrop_path"] = f"images/{backdrop_file}" if backdrop_file else ""
            
            if ai_res:
                final_item["wx_title"] = ai_res.get("title")
                final_item["wx_content"] = ai_res.get("content")
            else:
                final_item["wx_title"] = f"今日必看：{raw_data['title']}"
                final_item["wx_content"] = f"<p>{raw_data['overview']}</p>"

            new_items.append(final_item)
            uid = f"{m_type}_{raw_data['id']}"
            history_set.add(uid)
            new_history_ids.append(uid)
        else:
            print("   ⚠️ 无符合条件的新片。")

    if new_items:
        # 保存 JSON
        curr_data = []
        if os.path.exists(JSON_FILE):
            try:
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    curr_data = json.load(f)
            except: pass
        
        # 合并新旧数据，只保留 50 条
        updated_data = new_items + curr_data
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(updated_data[:50], f, ensure_ascii=False, indent=2)
        
        # 永久保存 ID
        save_to_history(new_history_ids)
        print(f"\n🎉 运行成功！历史库目前共 {len(history_set)} 条。")
    else:
        print("\n⚠️ 本次运行未抓取到新内容。")

if __name__ == "__main__":
    main()
