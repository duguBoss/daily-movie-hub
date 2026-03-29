import json
import os
import random
import re
import shutil
import sys
from datetime import datetime, timedelta

import requests


TMDB_TOKEN = os.environ.get("TMDB_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

GITHUB_REPO = os.environ.get("GITHUB_REPO", "duguBoss/daily-movie-hub")
CDN_PREFIX = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@main/data/images/"
TOP_GIF = "https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzXgUR7FJnf11qGIo8nmKt6RxibXrb5s4RFb9UZ9UOHQy7fqQyI377Licw/0?wx_fmt=gif"
BOTTOM_GIF = "https://mmbiz.qpic.cn/mmbiz_gif/3hAJnwuyZuicicZkgJBUCCaricdibomDBrTzk57DCmhVC16o9ILH0Tn1YPEiarfLRRQSVFN2mJdeYibGnBPialPIzvojw/0?wx_fmt=gif"

if not TMDB_TOKEN or not GEMINI_API_KEY:
    print("错误: TMDB_API_KEY 或 GEMINI_API_KEY 未配置")
    sys.exit(1)

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_TOKEN}",
}

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

DATA_DIR = "data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "weekly_updates.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history_ids.txt")

BLOCKED_GENRES = "27,10752"
SENSITIVE_KEYWORDS = ["伦理", "禁忌", "乱伦", "色情", "肉欲", "情色", "禁片", "尺度大"]
SUMMARY_MAX_LENGTH = 100

WX_PROMPT_TEMPLATE = """
# Role
你是中文影视公众号里最会写推荐稿的资深编辑，文风像真实作者，不像 AI。

## 目标
基于给定影视信息，写一篇适合公众号分发的推荐内容：
- 总篇幅约 1500 字，允许上下浮动，但必须明显比普通简介更扎实。
- 文案要有真实观影感、画面感和情绪推进，不要空泛夸张，不要模板口号。
- 优先写“为什么值得看”，不是重复剧情梗概。
- 禁止剧透结局，禁止低俗擦边，禁止伦理禁忌和色情暗示。

## 写作要求
1. 标题 18-28 字，要有传播力，但不要标题党。
2. 摘要 60-100 字，单段，适合放在列表页；必须是自然中文，不要口号腔。
3. 摘要必须兼顾 SEO 和曝光：
- 尽量自然包含片名、类型或题材、核心看点、情绪关键词。
- 让用户一眼知道“这是什么片、适合谁看、为什么值得点开”。
- 禁止关键词堆砌，禁止生硬罗列标签，读起来必须像真人编辑写的导语。
- 优先使用用户真实会搜索或会被平台识别的表达，如“剧情解析、口碑、推荐、看点、演员表现、后劲”等，但要自然融入。
4. 正文风格要去掉 AI 味：
- 少用“这部作品不仅…更…”“值得一提的是…”“总的来说…”这类套话。
- 多用具体场景、情绪转折、人物处境来带动阅读。
- 允许有节奏变化，句子长短交替，像真人编辑写稿。
- 不要频繁用“封神、炸裂、神作、必看”等廉价热词。
5. 正文结构必须严格对应下面的 HTML 模板字段：
- [lead_intro]：开篇导语，先用电影信息卡片承接，再写约 500 字介绍，突出人物处境、故事钩子、观看门槛和推荐理由。
- [deep_recommend]：约 650 字，展开影片真正迷人的地方，可以写表演、叙事、主题、情绪后劲，但不剧透。
- [short_review]：约 220-300 字，写成编辑短评，语言利落，有判断，有记忆点。
- [quote]：提炼一句适合收尾的金句，16-32 字。
- [first_char]：填一个有力量的单字，适合作为首字下沉。
6. HTML 必须输出成单行字符串，直接可嵌入 JSON。

## HTML 模板
<section style="margin:0;padding:0;background:#f5f1e8;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1f1f1f;text-align:justify;"><section style="padding:18px 14px 10px;"><section style="background:linear-gradient(135deg,#16181d 0%,#20242c 55%,#3a2e25 100%);border-radius:24px;overflow:hidden;box-shadow:0 12px 36px rgba(36,31,25,0.16);"><img src="[backdrop_url]" style="width:100%;display:block;vertical-align:top;max-height:360px;object-fit:cover;"><section style="padding:18px 16px 20px;"><section style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;"><section style="flex:1;min-width:0;"><section style="font-size:24px;line-height:1.35;font-weight:800;color:#fff;">[title]</section><section style="margin-top:6px;font-size:13px;color:rgba(255,255,255,0.64);">[original_title]</section></section><section style="min-width:72px;padding:10px 12px;border-radius:16px;background:rgba(255,255,255,0.08);text-align:center;"><section style="font-size:26px;line-height:1;font-weight:800;color:#f5c16c;">[rating]</section><section style="margin-top:4px;font-size:10px;letter-spacing:1px;color:rgba(255,255,255,0.5);">TMDB</section></section></section><section style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px;"><section style="padding:12px 12px;border-radius:16px;background:rgba(255,255,255,0.06);"><section style="font-size:11px;color:rgba(255,255,255,0.5);">类型</section><section style="margin-top:4px;font-size:14px;line-height:1.6;color:#fff;">[genres]</section></section><section style="padding:12px 12px;border-radius:16px;background:rgba(255,255,255,0.06);"><section style="font-size:11px;color:rgba(255,255,255,0.5);">上映日期</section><section style="margin-top:4px;font-size:14px;line-height:1.6;color:#fff;">[date]</section></section><section style="padding:12px 12px;border-radius:16px;background:rgba(255,255,255,0.06);"><section style="font-size:11px;color:rgba(255,255,255,0.5);">导演</section><section style="margin-top:4px;font-size:14px;line-height:1.6;color:#fff;">[director]</section></section><section style="padding:12px 12px;border-radius:16px;background:rgba(255,255,255,0.06);"><section style="font-size:11px;color:rgba(255,255,255,0.5);">主演</section><section style="margin-top:4px;font-size:14px;line-height:1.6;color:#fff;">[actors]</section></section></section></section></section></section><section style="padding:18px 14px 8px;"><section style="background:#fff;border-radius:22px;padding:20px 16px;box-shadow:0 10px 26px rgba(70,58,43,0.08);"><section style="overflow:hidden;"><section style="float:left;font-size:50px;line-height:0.9;font-weight:800;color:#c45b3c;padding-right:8px;font-family:Georgia,serif;">[first_char]</section><section style="font-size:16px;line-height:1.95;color:#2f2a26;">[lead_intro]</section></section></section></section><section style="padding:8px 14px;"><section style="background:linear-gradient(180deg,#fff8ef 0%,#f8efe2 100%);border-radius:22px;padding:22px 16px;box-shadow:0 10px 26px rgba(70,58,43,0.08);"><section style="font-size:20px;line-height:1.4;font-weight:800;color:#2c241f;">为什么它会留下后劲</section><section style="margin-top:12px;font-size:16px;line-height:1.95;color:#403630;">[deep_recommend]</section></section></section><section style="padding:8px 14px 18px;"><section style="background:#1d1f23;border-radius:22px;padding:22px 16px;"><section style="font-size:18px;line-height:1.4;font-weight:800;color:#f7d18a;">编辑短评</section><section style="margin-top:12px;font-size:15px;line-height:1.9;color:rgba(255,255,255,0.82);">[short_review]</section><section style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08);font-size:18px;line-height:1.8;color:#fff;font-weight:700;text-align:center;">“[quote]”</section></section></section></section>

## 输出格式
只返回 JSON，不要加解释，不要加 Markdown 代码块：
{
  "title": "标题",
  "summary": "100字以内摘要",
  "content": "压缩成一行的HTML"
}

## 输入数据
{{input}}
"""

SUMMARY_RETRY_PROMPT = """
请把下面这段影视摘要压缩重写为 60 到 100 个中文字符以内。
要求：
- 保留推荐重点和情绪吸引力
- 保证 SEO 友好，自然带出片名、题材或类型、核心看点
- 提升列表点击欲，但不要标题党，不要关键词堆砌
- 不要标题党
- 不要换行
- 只输出 JSON

输出格式：
{"summary":"..."}

原摘要：
{{summary}}
"""


def setup_directories(reset=False):
    if reset and os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, "a", encoding="utf-8").close()


def load_history():
    history_set = set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            uid = line.strip()
            if uid:
                history_set.add(uid)
    return history_set


def save_to_history(new_id_list):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for uid in new_id_list:
            f.write(f"{uid}\n")


def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def extract_json_text(content_text):
    text = clean_text(content_text)
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content_text or "", flags=re.S | re.I)
    if fenced:
        return fenced.group(1).strip()
    return text


def safe_join(items, fallback="暂无"):
    values = [clean_text(item) for item in (items or []) if clean_text(item)]
    return " / ".join(values) if values else fallback


def sanitize_html(html):
    return re.sub(r"\s+", " ", str(html or "")).strip()


def wrap_with_guide_banners(html_content):
    body = sanitize_html(html_content)
    has_top = TOP_GIF in body
    has_bottom = BOTTOM_GIF in body
    if has_top and has_bottom:
        return body

    wrapped = (
        '<section style="margin:0;padding:0;background:#ffffff;">'
        f'<img src="{TOP_GIF}" style="width:100%;display:block;">'
        f'<section style="padding:0;margin:0;">{body}</section>'
        f'<img src="{BOTTOM_GIF}" style="width:100%;display:block;">'
        "</section>"
    )
    return sanitize_html(wrapped)


def download_image(url, filename):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
                f.write(resp.content)
            return filename
    except requests.RequestException:
        return None
    return None


def call_gemini_json(prompt, temperature=0.85):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": temperature,
        },
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=120)
    resp.raise_for_status()
    res_json = resp.json()
    content_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(extract_json_text(content_text))


def regenerate_summary(summary):
    prompt = SUMMARY_RETRY_PROMPT.replace("{{summary}}", clean_text(summary))
    try:
        data = call_gemini_json(prompt, temperature=0.4)
        fixed = clean_text(data.get("summary", ""))
        if fixed and len(fixed) <= SUMMARY_MAX_LENGTH:
            return fixed
    except Exception:
        pass
    return clean_text(summary)[:SUMMARY_MAX_LENGTH]


def normalize_ai_result(ai_res):
    title = clean_text(ai_res.get("title", ""))
    summary = clean_text(ai_res.get("summary", ""))
    content = sanitize_html(ai_res.get("content", ""))

    if summary and len(summary) > SUMMARY_MAX_LENGTH:
        summary = regenerate_summary(summary)

    return {
        "title": title,
        "summary": summary,
        "content": content,
    }


def generate_gemini_content(media_data, image_filename):
    print(f"   Gemini 撰写中: 《{media_data['title']}》")
    prompt_data = dict(media_data)
    prompt_data["genres"] = safe_join(prompt_data.get("genres"))
    prompt_data["director"] = safe_join(prompt_data.get("director"))
    prompt_data["actors"] = safe_join(prompt_data.get("actors"))
    prompt_data["backdrop_url"] = f"{CDN_PREFIX}{image_filename}" if image_filename else ""

    final_prompt = WX_PROMPT_TEMPLATE.replace(
        "{{input}}", json.dumps(prompt_data, ensure_ascii=False)
    )

    try:
        ai_res = call_gemini_json(final_prompt)
        normalized = normalize_ai_result(ai_res)
        if normalized["title"] and normalized["summary"] and normalized["content"]:
            return normalized
    except Exception:
        return None
    return None


def fetch_content(media_type, history_set, strategy="trending"):
    today = datetime.now()
    params = {
        "language": "zh-CN",
        "include_adult": "false",
        "without_genres": BLOCKED_GENRES,
        "vote_count.gte": 50,
    }

    if strategy == "fresh":
        params["sort_by"] = "popularity.desc"
        target_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        if media_type == "movie":
            params["primary_release_date.gte"] = target_date
        else:
            params["first_air_date.gte"] = target_date
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
        resp = requests.get(
            f"{BASE_URL}/discover/{media_type}",
            headers=HEADERS,
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        random.shuffle(results)

        target = None
        for item in results:
            uid = f"{media_type}_{item['id']}"
            overview = clean_text(item.get("overview", ""))
            if uid in history_set or len(overview) <= 10:
                continue
            if any(word in overview for word in SENSITIVE_KEYWORDS):
                continue
            target = item
            break

        if not target:
            return None, None

        detail = requests.get(
            f"{BASE_URL}/{media_type}/{target['id']}",
            headers=HEADERS,
            params={"language": "zh-CN"},
            timeout=20,
        ).json()
        credits = requests.get(
            f"{BASE_URL}/{media_type}/{target['id']}/credits",
            headers=HEADERS,
            params={"language": "zh-CN"},
            timeout=20,
        ).json()
        reviews_raw = requests.get(
            f"{BASE_URL}/{media_type}/{target['id']}/reviews",
            headers=HEADERS,
            timeout=20,
        ).json().get("results", [])

        backdrop_fn = f"{media_type}_{detail['id']}_b.jpg"
        backdrop_file = download_image(
            f"{BACKDROP_BASE_URL}{detail.get('backdrop_path')}", backdrop_fn
        )
        poster_fn = f"{media_type}_{detail['id']}_p.jpg"
        poster_file = download_image(
            f"{IMAGE_BASE_URL}{detail.get('poster_path')}", poster_fn
        )

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
            "overview": clean_text(detail.get("overview", "")),
            "reviews": [clean_text(r["content"][:240]) for r in reviews_raw[:3]],
            "backdrop_url": f"{CDN_PREFIX}{backdrop_file}" if backdrop_file else "",
            "poster_url": f"{CDN_PREFIX}{poster_file}" if poster_file else "",
        }
        return raw_data, backdrop_file
    except Exception:
        return None, None


def build_fallback_content(raw_data, backdrop_file):
    backdrop_url = f"{CDN_PREFIX}{backdrop_file}" if backdrop_file else ""
    genres = safe_join(raw_data.get("genres"))
    director = safe_join(raw_data.get("director"))
    actors = safe_join(raw_data.get("actors"))
    overview = clean_text(raw_data.get("overview"))
    summary = overview[:SUMMARY_MAX_LENGTH]
    html = (
        '<section style="margin:0;padding:0;background:#f5f1e8;font-family:-apple-system,BlinkMacSystemFont,'
        "'PingFang SC','Microsoft YaHei',sans-serif;color:#1f1f1f;\">"
        '<section style="padding:18px 14px;"><section style="background:#1d1f23;border-radius:24px;overflow:hidden;">'
        f'<img src="{backdrop_url}" style="width:100%;display:block;vertical-align:top;max-height:360px;object-fit:cover;">'
        '<section style="padding:18px 16px 20px;">'
        f'<section style="font-size:24px;line-height:1.35;font-weight:800;color:#fff;">{raw_data["title"]}</section>'
        f'<section style="margin-top:6px;font-size:13px;color:rgba(255,255,255,0.64);">{raw_data.get("original_title","")}</section>'
        f'<section style="margin-top:14px;font-size:14px;line-height:1.8;color:#fff;">类型：{genres}<br>导演：{director}<br>主演：{actors}<br>日期：{raw_data.get("date","")}</section>'
        "</section></section></section>"
        f'<section style="padding:0 14px 18px;"><section style="background:#fff;border-radius:22px;padding:20px 16px;font-size:16px;line-height:1.95;color:#2f2a26;">{overview}</section></section>'
        "</section>"
    )
    return {
        "title": f"今日精选：{raw_data['title']}",
        "summary": summary,
        "content": sanitize_html(html),
    }


def main():
    print(f"任务启动: {datetime.now().strftime('%Y-%m-%d')}")
    setup_directories(reset=(datetime.today().weekday() == 0))

    history_set = load_history()
    new_items = []
    new_history_ids = []

    tasks = [
        ("movie", "fresh", "最新电影"),
        ("movie", "trending", "热门电影"),
        ("tv", "fresh", "最新剧集"),
        ("tv", "hidden_gem", "高分剧集"),
    ]

    for m_type, strategy, label in tasks:
        print(f"\n{label} 探索中...")
        raw_data, backdrop_file = fetch_content(m_type, history_set, strategy)

        if not raw_data:
            print("   未发现合适内容")
            continue

        ai_res = generate_gemini_content(raw_data, backdrop_file)
        final_ai = ai_res or build_fallback_content(raw_data, backdrop_file)
        final_ai["content"] = wrap_with_guide_banners(final_ai.get("content", ""))

        final_item = raw_data.copy()
        final_item["update_date"] = datetime.now().strftime("%Y-%m-%d")
        final_item["backdrop_path"] = f"images/{backdrop_file}" if backdrop_file else ""
        final_item["wx_title"] = final_ai["title"]
        final_item["summary"] = final_ai["summary"]
        final_item["wx_content"] = final_ai["content"]

        new_items.append(final_item)
        new_history_ids.append(f"{m_type}_{raw_data['id']}")

    if new_items:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(new_items, f, ensure_ascii=False, indent=2)
        save_to_history(new_history_ids)
        print(f"\n运行成功，当日 {len(new_items)} 条内容已覆盖更新")
    else:
        print("\n本次运行无新内容")


if __name__ == "__main__":
    main()
