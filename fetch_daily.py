import requests
import json
import os
import sys
import shutil
import random
import re
import base64
from datetime import datetime, timedelta

# ================= 配置区域 =================

TMDB_TOKEN = os.environ.get("TMDB_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# 默认使用你指定的 3.1 flash lite，如果报错可改为 gemini-2.0-flash
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview") 

# 仓库配置 (用于生成 HTML 里的图片 CDN 链接)
# ⚠️⚠️⚠️ 请修改这里为你的 "用户名/仓库名" ⚠️⚠️⚠️
GITHUB_REPO = "duguBoss/daily-movie-hub" 
CDN_PREFIX = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@main/data/images/"

if not TMDB_TOKEN:
    print("❌ 错误: 环境变量 TMDB_API_KEY 未找到！")
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

# 屏蔽类别
BLOCKED_GENRES = "27,10752"

# ================= PROMPT (适配 Gemini 多模态) =================
WX_PROMPT_TEMPLATE = """
# Role: 顶级影视大V / 爆款制造机 (Viral Content Creator)

## Profile
你是一位全网最懂年轻人痛点、审美毒辣的**影视大V**。
**【重要】：我同时上传了一张这部作品的视觉海报/剧照。请你务必结合这张图片的色调、光影、构图，以及下方的元数据，写出极具画面感的文案。**

## 🧠 Traffic Psychology
1. **情绪共鸣**：针对现代人的焦虑（孤独、搞钱、内耗），提供情绪出口。
2. **审美碾压**：用极致的画面描写（引用你看到的图片细节），让用户觉得“看这部片子能提升我的品味”。
3. **极致悬念**：用“不敢看”、“猜不到”的诱惑勾引“想看”的欲望。

## 🚫 Constraints
1. **禁止爹味说教**。
2. **禁止百度百科**（不要列出生卒年等废话）。
3. **禁止平铺直叙**（不要按时间顺序讲故事）。

---

## Part 1: Title Generation (标题生成)

**爆款标题公式** = `[情绪标签/人群痛点]` + `[极度夸张/反差的钩子]` + `[书名号]`
**要求**：字数 18-28 字。要有“网感”（杀疯了、封神、窒息、深夜破防）。

---

## Part 2: HTML Content Generation (正文填充)

请将生成的文案填充到下方的 HTML 模板中。
**注意：保留 HTML 标签和样式，只修改 `[...]` 中的文字。**

**写作语气要求**：
- **开头**：必须黄金3秒定律。结合你看到的图片视觉冲击力来描写！
- **中间**：不要剧透结局！描述张力。
- **结尾**：升华主题，联系现实生活。

### HTML Template:
(请严格填充下方 [] 区域，不要修改 style，输出一行压缩代码)

<section style="margin:0;padding:0;background-color:#fff;font-family:-apple-system-font,BlinkMacSystemFont,'Helvetica Neue','PingFang SC',sans-serif;letter-spacing:1.5px;color:#333;text-align:justify;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzXgUR7FJnf11qGIo8nmKt6RxibXrb5s4RFb9UZ9UOHQy7fqQyI377Licw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;margin:0;"><section style="display:block;padding:20px 15px;overflow:hidden;"><section style="float:left;font-size:48px;line-height:0.9;margin-top:4px;padding-right:8px;font-weight:bold;color:#e63946;font-family:Georgia,serif;">[这里只填一个极具冲击力的汉字，如“杀/欲/痛/爆/神”]</section><section style="font-size:16px;line-height:1.8;">[此处250字。**黄金开场**。结合图片视觉！描写片中最让你“头皮发麻”的瞬间。用第一人称“我”来写。]</section></section><section style="margin:0;padding:25px 15px;background-color:#1a1a1a;color:#fff;"><section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:15px;"><section><section style="font-size:22px;font-weight:bold;line-height:1.2;color:#fff;">[title]</section><section style="font-size:14px;color:#999;margin-top:4px;">[original_title]</section></section><section style="text-align:right;"><section style="font-size:28px;font-weight:bold;color:#e63946;line-height:1;font-family:Georgia;">[rating]</section><section style="font-size:10px;color:#666;letter-spacing:1px;">TMDB</section></section></section><section style="font-size:13px;line-height:1.8;color:#ccc;border-top:1px solid #333;padding-top:15px;"><p style="margin:0;"><strong>类型：</strong>[genres]</p><p style="margin:0;"><strong>导演：</strong>[director]</p><p style="margin:0;"><strong>主演：</strong>[actors]</p><p style="margin:0;"><strong>上映：</strong>[date]</p></section></section><section style="display:block;font-size:16px;line-height:1.8;padding:25px 15px;background-color:#fff;">[此处400字。**深度种草**。不要写流水账！聚焦于主角面临的**两难困境**。结合 reviews 里的观众反馈，用“网友说”来增加可信度。]</section><section style="margin:0;padding:30px 15px;background-color:#f4f4f4;border-left:8px solid #e63946;"><section style="font-size:20px;font-weight:bold;color:#111;line-height:1.4;padding-bottom:10px;">[一句只有看过片才懂的、细思极恐或极度浪漫的短评]</section><section style="font-size:16px;line-height:1.8;color:#555;">[此处300字。**高光时刻拉片**。选取一个具体的镜头（光影、配乐），夸它。让读者觉得你品味很好。]</section></section><img src="[backdrop_url-这里必须填入我提供的完整图片链接]" style="width:100%;display:block;vertical-align:top;"><section style="margin:0;padding:30px 15px;background-color:#1a1a1a;"><section style="font-size:20px;font-weight:bold;color:#e63946;line-height:1.4;padding-bottom:10px;">[一句直击灵魂的拷问，如：我们终其一生在寻找什么？]</section><section style="font-size:16px;line-height:1.8;color:#bbb;">[此处350字。**价值升华**。聊聊片子背后的人性。联系现实生活。]</section></section><section style="display:block;text-align:center;padding:35px 15px;background-color:#fff;"><section style="width:20px;height:2px;background:#e63946;margin:0 auto 15px;"></section><section style="line-height:1.6;font-size:18px;font-weight:bold;color:#111;font-family:serif;">“[提取全片最扎心的一句金句台词]”</section><section style="width:20px;height:2px;background:#e63946;margin:15px auto 0;"></section></section><section style="display:block;text-align:center;padding:40px 15px 30px;background-color:#fff;"><section style="display:inline-block;margin:0 auto;"><span style="display:inline-block;padding:4px 12px;margin:4px;border:1px solid #e63946;color:#e63946;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签1:情绪]</span><span style="display:inline-block;padding:4px 12px;margin:4px;background-color:#f4f4f4;color:#666;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签2:看点]</span><span style="display:inline-block;padding:4px 12px;margin:4px;background-color:#f4f4f4;color:#666;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签3:类型]</span></section></section><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzk57DCmhVC16o9ILH0Tn1YPEiarfLRRQSVFN2mJdeYibGnBPialPIzvojw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;"></section>

## Input Meta Data (Json):
{{input}}

## Final Output Format (Strict JSON):
{
   "title": "符合爆款逻辑的标题",
   "content": "填充完整的HTML代码"
}
"""

# ================= 辅助功能 =================

def setup_directories(reset=False):
    if reset:
        print("🔄 周一重置: 清理旧数据...")
        if os.path.exists(DATA_DIR):
            try:
                for filename in os.listdir(IMAGES_DIR):
                    file_path = os.path.join(IMAGES_DIR, filename)
                    os.unlink(file_path)
            except: pass
        os.makedirs(IMAGES_DIR, exist_ok=True)
    
    if not os.path.exists(JSON_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            pass

def load_history():
    history_set = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                history_set.add(line.strip())
    # 迁移逻辑
    if not history_set and os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    media_type = "movie" if item.get("type") == "电影" else "tv"
                    history_set.add(f"{media_type}_{item['id']}")
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                for uid in history_set:
                    f.write(f"{uid}\n")
        except: pass
    return history_set

def save_to_history(new_id_list):
    if not new_id_list: return
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        for uid in new_id_list:
            f.write(f"{uid}\n")

def download_image(url, filename):
    if not url: return None
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            file_path = os.path.join(IMAGES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)
            return filename 
    except: pass
    return None

# ================= Gemini 生成逻辑 (多模态) =================

def generate_gemini_content(media_data, image_filename):
    if not GEMINI_API_KEY:
        print("   ⚠️ 未配置 GEMINI_API_KEY，跳过 AI 生成。")
        return None

    print(f"   🤖 请求 Gemini ({GEMINI_MODEL}) (多模态) 生成: 《{media_data['title']}》...")
    
    # 1. 准备图片数据 (Base64)
    image_path = os.path.join(IMAGES_DIR, image_filename)
    if not os.path.exists(image_path):
        print("   ⚠️ 图片文件不存在，无法进行多模态生成。")
        return None
        
    with open(image_path, "rb") as img_file:
        # 读取图片并转为 base64 字符串
        b64_image = base64.b64encode(img_file.read()).decode('utf-8')

    # 2. 准备 Prompt 和 元数据
    # 注入 CDN 链接供 HTML 使用
    media_data["backdrop_url"] = f"{CDN_PREFIX}{image_filename}"
    input_json_str = json.dumps(media_data, ensure_ascii=False)
    final_prompt = WX_PROMPT_TEMPLATE.replace("{{input}}", input_json_str)

    # 3. 构造 Gemini 请求 Payload
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    data = {
        "contents": [{
            "parts": [
                { "text": final_prompt },  # 文本 Prompt
                {
                    "inlineData": {
                        "mimeType": "image/jpeg", # 假设下载的是 jpg，tmdb通常是jpg
                        "data": b64_image
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json" # 强制 Gemini 返回 JSON
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=120)
        
        if resp.status_code == 200:
            result = resp.json()
            try:
                # 解析 Gemini 响应结构
                content_text = result['candidates'][0]['content']['parts'][0]['text']
                # 清洗可能存在的 markdown 标记
                content_text = re.sub(r'^```json\s*', '', content_text)
                content_text = re.sub(r'\s*```$', '', content_text)
                return json.loads(content_text)
            except (KeyError, json.JSONDecodeError) as e:
                print(f"   ❌ Gemini 响应解析失败: {e}")
                print(f"   🔍 原始响应: {result}")
                return None
        else:
            print(f"   ❌ Gemini API Error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"   ❌ Gemini Request Failed: {e}")
        return None

# ================= TMDB 获取逻辑 =================

def get_discovery_params(media_type, strategy):
    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    base_params = {
        "language": "zh-CN",
        "include_adult": "false",
        "without_genres": BLOCKED_GENRES,
        "vote_count.gte": 50,
    }

    if strategy == "fresh":
        if media_type == "movie":
            base_params["primary_release_date.gte"] = three_months_ago
            base_params["primary_release_date.lte"] = today_str
        else:
            base_params["first_air_date.gte"] = three_months_ago
            base_params["first_air_date.lte"] = today_str
        base_params["sort_by"] = "popularity.desc"
        base_params["page"] = random.randint(1, 3)

    elif strategy == "hidden_gem":
        base_params["vote_average.gte"] = 7.5
        base_params["sort_by"] = "vote_average.desc"
        base_params["vote_count.gte"] = 200 
        base_params["page"] = random.randint(1, 15)

    else: 
        base_params["sort_by"] = "popularity.desc"
        base_params["page"] = random.randint(1, 30)

    return base_params

def get_credits(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    try:
        resp = requests.get(url, headers=HEADERS, params={"language": "zh-CN"}, timeout=5)
        data = resp.json()
        directors = [c["name"] for c in data.get("crew", []) if c["job"] == "Director"]
        actors = [c["name"] for c in data.get("cast", [])[:4]]
        return {"directors": directors, "actors": actors}
    except:
        return {"directors": [], "actors": []}

def get_reviews(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}/reviews"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        data = resp.json()
        results = data.get("results", [])
        reviews = [r["content"][:200] for r in results if len(r["content"]) > 10][:3]
        return reviews
    except: return []

def fetch_content(media_type, history_set, strategy="trending"):
    url = f"{BASE_URL}/discover/{media_type}"
    params = get_discovery_params(media_type, strategy)
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200: return None, None, None
        
        results = resp.json().get("results", [])
        random.shuffle(results)
        
        target_item = None
        for item in results:
            unique_id = f"{media_type}_{item['id']}"
            if unique_id not in history_set and item.get("overview") and len(item.get("overview")) > 5:
                target_item = item
                break
        
        if not target_item: return None, None, None

        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params={"language": "zh-CN"}, timeout=15)
        detail = detail_resp.json()
        
        credits = get_credits(media_type, detail["id"])
        reviews = get_reviews(media_type, detail["id"])

        poster_filename = f"{media_type}_{detail['id']}_p.jpg"
        backdrop_filename = f"{media_type}_{detail['id']}_b.jpg"
        
        download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", poster_filename)
        # 确保下载 backdrop，因为 Gemini 需要它
        if detail.get('backdrop_path'):
            download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", backdrop_filename)
        else:
            backdrop_filename = None # 如果没有 backdrop，Gemini 这一步会报错或跳过，需要处理

        raw_data = {
            "id": detail["id"],
            "unique_id": f"{media_type}_{detail['id']}",
            "title": detail.get("title") or detail.get("name"),
            "original_title": detail.get("original_title") or detail.get("original_name"),
            "type": "电影" if media_type == "movie" else "剧集",
            "rating": round(detail.get("vote_average", 0), 1),
            "date": detail.get("release_date") or detail.get("first_air_date"),
            "genres": [g["name"] for g in detail.get("genres", [])],
            "director": credits["directors"],
            "actors": credits["actors"],
            "overview": detail.get("overview", ""),
            "reviews": reviews,
            "douban_link": f"https://search.douban.com/movie/subject_search?search_text={detail.get('imdb_id') or (detail.get('title') or detail.get('name'))}"
        }

        return raw_data, poster_filename, backdrop_filename

    except Exception as e:
        print(f"❌ Error fetching {media_type}: {e}")
        return None, None, None

# ================= 主程序 =================

def main():
    print("🚀 任务开始...")
    is_monday = datetime.today().weekday() == 0
    setup_directories(reset=is_monday)
    
    history_set = load_history()
    print(f"📚 历史记录: {len(history_set)} 条")
    
    new_items = []
    new_history_ids = [] 

    tasks = [
        ("movie", "fresh", "🆕 最新电影"),
        ("movie", "trending", "🔥 热门电影"),
        ("tv", "fresh", "🆕 最新剧集"),
        ("tv", "hidden_gem", "💎 高分剧集"),
    ]

    for media_type, strategy, label in tasks:
        print(f"\n{label} 挖掘中...")
        raw_data, poster_file, backdrop_file = fetch_content(media_type, history_set, strategy)
        
        if raw_data:
            print(f"   ✅ 捕获: 《{raw_data['title']}》")
            
            # 使用 Gemini 生成
            if backdrop_file:
                ai_content = generate_gemini_content(raw_data, backdrop_file)
            else:
                print("   ⚠️ 缺少背景图，跳过 Gemini 生成")
                ai_content = None

            final_item = raw_data.copy()
            final_item["update_date"] = datetime.now().strftime("%Y-%m-%d")
            final_item["poster_path"] = f"images/{poster_file}" if poster_file else ""
            final_item["backdrop_path"] = f"images/{backdrop_file}" if backdrop_file else ""
            
            if ai_content:
                print("   ✨ Gemini 文案生成成功！")
                final_item["wx_title"] = ai_content.get("title", f"推荐：{raw_data['title']}")
                final_item["wx_content"] = ai_content.get("content", "")
            else:
                final_item["wx_title"] = f"推荐：{raw_data['title']}"
                final_item["wx_content"] = "<p>生成失败</p>"

            new_items.append(final_item)
            history_set.add(raw_data["unique_id"])
            new_history_ids.append(raw_data["unique_id"])
        else:
            print("   ⚠️ 无新内容")

    print("\n💾 保存数据...")
    if new_items:
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                try: current_data = json.load(f)
                except: current_data = []
        
        current_data = new_items + current_data
        current_data = current_data[:50]
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
            
        save_to_history(new_history_ids)
        print(f"🎉 新增 {len(new_items)} 条。")
    else:
        print("⚠️ 无更新")

if __name__ == "__main__":
    main()
