import requests
import json
import os
import sys
import shutil
import random
import re
from datetime import datetime, timedelta

# ================= 配置区域 =================

TMDB_TOKEN = os.environ.get("TMDB_API_KEY")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

# ⚠️ 请修改这里为你的 "用户名/仓库名"
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
# 🆕 新增：永久历史记录文件
HISTORY_FILE = os.path.join(DATA_DIR, "history_ids.txt")

# 屏蔽类别
BLOCKED_GENRES = "27,10752"

# ================= PROMPT (流量爆款版) =================
WX_PROMPT_TEMPLATE = """
# Role: 顶级影视大V / 爆款制造机 (Viral Content Creator)

## Profile
你不是一个只会写简介的机器人，你是全网最懂年轻人痛点、审美最毒辣的**影视大V**。你的文字必须有**“人味儿”**，要像在深夜和闺蜜/兄弟喝多了聊心事一样，既犀利又走心。你的目标只有一个：**让用户在划过屏幕的0.1秒内被标题击中，读完第一段后忍不住转发朋友圈。**

## 🧠 Traffic Psychology (流量密码)
你的内容必须包含以下要素之一：
1. **情绪共鸣**：针对现代人的焦虑（孤独、搞钱、内耗、原生家庭），提供情绪出口。
2. **审美碾压**：用极致的画面描写，让用户觉得“看这部片子能提升我的品味”。
3. **极致悬念**：用“不敢看”、“猜不到”的诱惑勾引“想看”的欲望。

## 🚫 Writing Constraints (绝对禁止)
1. **禁止爹味说教**：不要说“这部电影告诉我们...”，要说“看完这场戏，我直接在电影院哭成狗”。
2. **禁止百度百科**：严禁出现“XXX出生于XXX年”这种废话。
3. **禁止平铺直叙**：不要按时间顺序讲故事！直接把最劲爆的冲突甩在用户脸上。

---

## Part 1: Title Generation (标题生成)

**爆款标题公式** = `[情绪标签/人群痛点]` + `[极度夸张/反差的钩子]` + `[书名号]`

**要求**：
1. 必须包含书名号《作品名》。
2. 字数控制在 18-28 字。
3. **要有“网感”**：可以使用“杀疯了”、“封神”、“窒息”、“顶级”、“深夜破防”、“建议收藏”等词。

**Correct Examples (参考)**：
- [复仇/爽剧] 豆瓣9.4！全员恶人全员疯批，这才是成年人该看的《黑暗荣耀》！
- [治愈/破防] 建议深夜独自观看，这部《过往人生》后劲太大，我缓了整整三天。
- [人性/封神] 敢拍这种尺度的也就HBO了！《切尔诺贝利》撕开了多少人的遮羞布？

---

## Part 2: HTML Content Generation (正文填充)

请将生成的文案填充到下方的 HTML 模板中。
**注意：保留 HTML 标签和样式，只修改 `[...]` 中的文字。**

**写作语气要求**：
- **开头**：必须黄金3秒定律。第一句话就要抓人！用第一人称“我”来写主观感受。
- **中间**：不要剧透结局！要描述**张力**。结合我提供的 `reviews` (网友评论) 来增加真实感。
- **结尾**：升华主题，联系到读者的现实生活，引发共鸣。

### HTML Template:
(请严格填充下方 [] 区域，不要修改 style，输出一行压缩代码)

<section style="margin:0;padding:0;background-color:#fff;font-family:-apple-system-font,BlinkMacSystemFont,'Helvetica Neue','PingFang SC',sans-serif;letter-spacing:1.5px;color:#333;text-align:justify;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzXgUR7FJnf11qGIo8nmKt6RxibXrb5s4RFb9UZ9UOHQy7fqQyI377Licw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;margin:0;"><section style="display:block;padding:20px 15px;overflow:hidden;"><section style="float:left;font-size:48px;line-height:0.9;margin-top:4px;padding-right:8px;font-weight:bold;color:#e63946;font-family:Georgia,serif;">[这里只填一个极具冲击力的汉字，如“杀/欲/痛/爆/神”]</section><section style="font-size:16px;line-height:1.8;">[此处250字。**黄金开场**。不要概括剧情！直接描写片中最让你“头皮发麻”或“心脏骤停”的那个瞬间。用第一人称“我”来写。例如：“凌晨三点，我盯着屏幕不敢呼吸...”或者“刚看五分钟，我就知道这片子要封神。”]</section></section><section style="margin:0;padding:25px 15px;background-color:#1a1a1a;color:#fff;"><section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:15px;"><section><section style="font-size:22px;font-weight:bold;line-height:1.2;color:#fff;">[title]</section><section style="font-size:14px;color:#999;margin-top:4px;">[original_title]</section></section><section style="text-align:right;"><section style="font-size:28px;font-weight:bold;color:#e63946;line-height:1;font-family:Georgia;">[rating]</section><section style="font-size:10px;color:#666;letter-spacing:1px;">TMDB</section></section></section><section style="font-size:13px;line-height:1.8;color:#ccc;border-top:1px solid #333;padding-top:15px;"><p style="margin:0;"><strong>类型：</strong>[genres]</p><p style="margin:0;"><strong>导演：</strong>[director]</p><p style="margin:0;"><strong>主演：</strong>[actors]</p><p style="margin:0;"><strong>上映：</strong>[date]</p></section></section><section style="display:block;font-size:16px;line-height:1.8;padding:25px 15px;background-color:#fff;">[此处400字。**深度种草**。不要写流水账！聚焦于主角面临的**两难困境**或**极致欲望**。多用短句。结合 reviews 里的观众反馈，用“网友说”来增加可信度。告诉读者：为什么现在、立刻、马上要去浪费这2个小时看它？因为它解决了你的什么情绪需求？]</section><section style="margin:0;padding:30px 15px;background-color:#f4f4f4;border-left:8px solid #e63946;"><section style="font-size:20px;font-weight:bold;color:#111;line-height:1.4;padding-bottom:10px;">[一句只有看过片才懂的、细思极恐或极度浪漫的短评]</section><section style="font-size:16px;line-height:1.8;color:#555;">[此处300字。**高光时刻拉片**。选取一个具体的镜头（光影、配乐、台词），用显微镜级别的观察力去夸它。比如：“注意看第30分钟那个眼神，没有一句台词，但那种破碎感简直溢出屏幕...” 让读者觉得你很专业，品味很好。]</section></section><img src="[backdrop_url-这里必须填入我提供的完整图片链接]" style="width:100%;display:block;vertical-align:top;"><section style="margin:0;padding:30px 15px;background-color:#1a1a1a;"><section style="font-size:20px;font-weight:bold;color:#e63946;line-height:1.4;padding-bottom:10px;">[一句直击灵魂的拷问，如：我们终其一生在寻找什么？]</section><section style="font-size:16px;line-height:1.8;color:#bbb;">[此处350字。**价值升华**。聊聊片子背后的人性。联系现实生活：北上广的压力、原生家庭的痛、爱而不得的苦。最后给读者一个必须观看的理由：也许这部片子不能解决你的问题，但它能让你大哭一场。]</section></section><section style="display:block;text-align:center;padding:35px 15px;background-color:#fff;"><section style="width:20px;height:2px;background:#e63946;margin:0 auto 15px;"></section><section style="line-height:1.6;font-size:18px;font-weight:bold;color:#111;font-family:serif;">“[提取全片最扎心的一句金句台词]”</section><section style="width:20px;height:2px;background:#e63946;margin:15px auto 0;"></section></section><section style="display:block;text-align:center;padding:40px 15px 30px;background-color:#fff;"><section style="display:inline-block;margin:0 auto;"><span style="display:inline-block;padding:4px 12px;margin:4px;border:1px solid #e63946;color:#e63946;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签1:情绪]</span><span style="display:inline-block;padding:4px 12px;margin:4px;background-color:#f4f4f4;color:#666;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签2:看点]</span><span style="display:inline-block;padding:4px 12px;margin:4px;background-color:#f4f4f4;color:#666;font-size:12px;border-radius:50px;letter-spacing:1px;">#[生成标签3:类型]</span></section></section><img src="https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzk57DCmhVC16o9ILH0Tn1YPEiarfLRRQSVFN2mJdeYibGnBPialPIzvojw/0?wx_fmt=gif" style="width:100%;display:block;vertical-align:top;"></section>

## Input Data (Json):
{{input}}

## Final Output Format (Strict JSON):
{
   "title": "符合爆款逻辑的标题",
   "content": "填充完整的HTML代码"
}
"""

# ================= 辅助功能 (核心修改区域) =================

def setup_directories(reset=False):
    if reset:
        print("🔄 周一重置: 清理旧数据...")
        if os.path.exists(DATA_DIR):
            try:
                # 1. ⚠️ 重要：永远不要删除 history_ids.txt
                # 2. 清理图片
                for filename in os.listdir(IMAGES_DIR):
                    file_path = os.path.join(IMAGES_DIR, filename)
                    os.unlink(file_path)
            except: pass
        os.makedirs(IMAGES_DIR, exist_ok=True)
    
    if not os.path.exists(JSON_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

    # 🆕 创建历史账本文件 (如果不存在)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            pass # 创建空文件

def load_history():
    """
    🆕 加载永久历史记录 (Set 集合，查询速度快)
    格式： "movie_12345", "tv_67890"
    """
    history_set = set()
    
    # 1. 读取 history_ids.txt
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                clean_line = line.strip()
                if clean_line:
                    history_set.add(clean_line)
    
    # 2. (兼容性补丁) 如果 history 为空，但 json 里有数据，把 json 里的数据同步进去
    # 防止第一次运行新代码时重复抓取已有内容
    if not history_set and os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    # 假设 json 里只有 id，我们需要判断 type (原 json 可能有 type 字段)
                    media_type = "movie" if item.get("type") == "电影" else "tv"
                    unique_id = f"{media_type}_{item['id']}"
                    history_set.add(unique_id)
            
            # 同步回文件
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                for uid in history_set:
                    f.write(f"{uid}\n")
            print(f"📦 已从 JSON 迁移 {len(history_set)} 条历史记录。")
        except: pass
            
    return history_set

def save_to_history(new_id_list):
    """
    🆕 将新抓取的 ID 追加到历史文件
    """
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

# ================= LLM 生成逻辑 =================

def generate_llm_content(media_data, backdrop_filename):
    if not LLM_API_KEY: return None
    print(f"   🤖 请求 AI ({LLM_MODEL}) 生成文案: 《{media_data['title']}》...")
    
    full_backdrop_url = f"{CDN_PREFIX}{backdrop_filename}" if backdrop_filename else "https://via.placeholder.com/800x400"
    media_data["backdrop_url"] = full_backdrop_url

    input_json_str = json.dumps(media_data, ensure_ascii=False)
    final_prompt = WX_PROMPT_TEMPLATE.replace("{{input}}", input_json_str)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs strict JSON."},
            {"role": "user", "content": final_prompt}
        ],
        "temperature": 0.75,
        "response_format": {"type": "json_object"}
    }

    try:
        resp = requests.post(f"{LLM_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            result = resp.json()
            content_str = result['choices'][0]['message']['content']
            content_str = re.sub(r'^```json\s*', '', content_str)
            content_str = re.sub(r'\s*```$', '', content_str)
            return json.loads(content_str)
    except Exception as e:
        print(f"   ❌ LLM Request Failed: {e}")
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
        base_params["page"] = random.randint(1, 15) # 增加页码随机性

    else: 
        base_params["sort_by"] = "popularity.desc"
        base_params["page"] = random.randint(1, 30) # 热门内容翻到第30页

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
            # 🆕 唯一ID生成：例如 movie_12345
            unique_id = f"{media_type}_{item['id']}"
            
            # 🆕 核心查重：查的是 history_set，而不是 existing_ids (json)
            if unique_id not in history_set and item.get("overview") and len(item.get("overview")) > 5:
                target_item = item
                break
        
        if not target_item: return None, None, None

        # 获取详情
        detail_url = f"{BASE_URL}/{media_type}/{target_item['id']}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params={"language": "zh-CN"}, timeout=15)
        detail = detail_resp.json()
        
        credits = get_credits(media_type, detail["id"])
        reviews = get_reviews(media_type, detail["id"])

        poster_filename = f"{media_type}_{detail['id']}_p.jpg"
        backdrop_filename = f"{media_type}_{detail['id']}_b.jpg"
        
        download_image(f"{IMAGE_BASE_URL}{detail.get('poster_path')}", poster_filename)
        download_image(f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", backdrop_filename)

        raw_data = {
            "id": detail["id"],
            "unique_id": f"{media_type}_{detail['id']}", # 用于存入历史文件
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
    
    # 🆕 加载永久历史记录
    history_set = load_history()
    print(f"📚 已加载 {len(history_set)} 条历史记录。")
    
    new_items = []
    new_history_ids = [] # 待保存到 text 的新 ID

    tasks = [
        ("movie", "fresh", "🆕 最新电影"),
        ("movie", "trending", "🔥 热门电影"),
        ("tv", "fresh", "🆕 最新剧集"),
        ("tv", "hidden_gem", "💎 高分剧集"),
    ]

    for media_type, strategy, label in tasks:
        print(f"\n{label} 挖掘中...")
        # 传入 history_set 进行查重
        raw_data, poster_file, backdrop_file = fetch_content(media_type, history_set, strategy)
        
        if raw_data:
            print(f"   ✅ 捕获: 《{raw_data['title']}》")
            
            ai_content = generate_llm_content(raw_data, backdrop_file)
            
            final_item = raw_data.copy()
            final_item["update_date"] = datetime.now().strftime("%Y-%m-%d")
            final_item["poster_path"] = f"images/{poster_file}" if poster_file else ""
            final_item["backdrop_path"] = f"images/{backdrop_file}" if backdrop_file else ""
            
            if ai_content:
                final_item["wx_title"] = ai_content.get("title", f"推荐：{raw_data['title']}")
                final_item["wx_content"] = ai_content.get("content", "")
            else:
                final_item["wx_title"] = f"推荐：{raw_data['title']}"
                final_item["wx_content"] = "<p>文案生成失败。</p>"

            new_items.append(final_item)
            
            # 记录到本轮历史列表，防止本轮内部重复（虽然概率极低）
            history_set.add(raw_data["unique_id"])
            new_history_ids.append(raw_data["unique_id"])
        else:
            print("   ⚠️ 未找到符合条件的新内容。")

    # 保存结果
    print("\n💾 正在保存数据...")
    if new_items:
        # 1. 更新 JSON (只保留 50 条)
        current_data = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                try: current_data = json.load(f)
                except: current_data = []
        
        current_data = new_items + current_data
        current_data = current_data[:50]
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
            
        # 2. 🆕 更新 历史文件 (永久追加)
        save_to_history(new_history_ids)
        
        print(f"🎉 更新完成！新增 {len(new_items)} 条。")
    else:
        print("⚠️ 本次无内容更新。")

if __name__ == "__main__":
    main()
