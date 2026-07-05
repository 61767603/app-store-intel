#!/usr/bin/env python3
"""
iOS App Store 细分畅销榜情报报告 - HTML 报告生成器
===================================================
从 app_intel.db 读取数据，生成暗色主题的自包含 HTML 报告。
"""

import sqlite3
import os
import sys
import io
import datetime
import html
import math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_intel.db")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.html")

CATEGORIES = {
    "6000": "商业", "6001": "天气", "6002": "工具", "6003": "教育",
    "6004": "社交", "6005": "娱乐", "6006": "财务", "6007": "健康健美",
    "6008": "音乐", "6009": "医疗", "6010": "导航", "6011": "新闻",
    "6012": "摄影与录像", "6013": "效率", "6014": "参考", "6015": "购物",
    "6016": "生活方式", "6017": "体育", "6018": "旅行",
    "6020": "图书", "6021": "美食佳饮", "6023": "杂志报纸",
}

COUNTRIES = {
    "us": "美国", "jp": "日本", "gb": "英国", "de": "德国",
    "kr": "韩国", "sa": "沙特", "au": "澳洲", "ca": "加拿大",
    "fr": "法国", "br": "巴西", "tr": "土耳其", "id": "印尼",
}

KNOWN_PUBLISHERS = [
    "Tencent", "NetEase", "Voodoo", "Supercell", "King", "Niantic",
    "Electronic Arts", "Activision", "Zynga", "Garena", "Lilith",
    "IGG", "FunPlus", "Playrix", "Microsoft", "Google", "Apple",
    "Meta", "Amazon", "ByteDance", "WhatsApp", "Square", "PayPal",
    "Netflix", "Spotify", "Disney", "Samsung", "Huawei", "Xiaomi",
    "Alibaba", "Meituan", "DiDi", "Baidu", "JD", "Uber", "Airbnb",
    "Snap", "Pinterest", "Twitter", "Line", "Kakao", "Sony",
    "Nintendo", "Bandai", "SEGA", "Square Enix", "Capcom", "OpenAI",
    "Anthropic", "Match", "Bumble", "Airbnb",
]


OVERALL_BASE = 156000        # US non-game #1 daily (Sensor Tower 2022)
POWER_ALPHA = 0.48           # b ≈ 0.477 → 0.48 (derived from #1=156k, #10=52k)
GAME_POWER_ALPHA = 0.55
GAME_BASE = 93000

COUNTRY_FACTOR = {
    "us": 1.00, "jp": 0.25, "gb": 0.10, "de": 0.08,
    "kr": 0.06, "fr": 0.05, "ca": 0.04, "au": 0.04,
    "br": 0.03, "sa": 0.02, "tr": 0.02, "id": 0.02,
}

CATEGORY_FACTOR = {
    "6004": 0.40, "6005": 0.35, "6012": 0.30, "6008": 0.28, "6015": 0.25,
    "6000": 0.20, "6003": 0.18, "6006": 0.18, "6011": 0.17, "6002": 0.15,
    "6013": 0.15, "6017": 0.14, "6018": 0.14, "6016": 0.13, "6007": 0.11,
    "6020": 0.09, "6021": 0.09, "6001": 0.08, "6009": 0.07, "6010": 0.07,
    "6014": 0.06, "6023": 0.06,
}


def estimate_downloads(rank, country="us", category_id=None, is_game=False):
    if rank is None or rank <= 0:
        return 0
    cf = COUNTRY_FACTOR.get(country, 0.03)
    if category_id and category_id != "overall":
        cat_f = CATEGORY_FACTOR.get(category_id, 0.10)
        b = GAME_POWER_ALPHA if is_game else POWER_ALPHA
        base = (GAME_BASE if is_game else OVERALL_BASE) * cat_f
    else:
        b = GAME_POWER_ALPHA if is_game else POWER_ALPHA
        base = GAME_BASE if is_game else OVERALL_BASE
    daily = base * math.pow(rank, -b) * cf
    return int(max(1, daily * 30))


def format_downloads(monthly):
    if monthly is None or monthly <= 0:
        return "N/A"
    if monthly >= 10000:
        return f"{monthly / 10000:.1f}万/月"
    return f"{monthly / 1000:.0f}千/月"


def format_revenue_from_downloads(monthly_downloads, price):
    if monthly_downloads is None or monthly_downloads <= 0:
        return "N/A"
    is_free = price is None or str(price).lower().strip() in ("free", "get", "0", "0.00", "")
    if is_free:
        low = monthly_downloads * 0.03
        high = monthly_downloads * 0.10
    else:
        low = monthly_downloads * 0.10
        high = monthly_downloads * 0.30

    def fmt(v):
        if v >= 10000:
            return f"${v / 10000:.1f}万"
        elif v >= 1000:
            return f"${v / 1000:.0f}千"
        else:
            return f"${v:.0f}"

    return f"{fmt(low)}-{fmt(high)}/月"


def format_revenue(rating_count):
    if not rating_count or rating_count == 0:
        return "N/A"
    low = rating_count * 80 * 0.03
    high = rating_count * 80 * 0.1

    def fmt(v):
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        if v >= 1000:
            return f"${v / 1000:.1f}K"
        return f"${v:.0f}"

    return f"{fmt(low)}-{fmt(high)}/月"


def format_monetization_prediction(price, rating_count):
    if price and price not in ("Free", "Get", "0", "0.00", ""):
        return f"付费{price}+内购"
    if rating_count and rating_count < 10000:
        return "少评高价排名→高ARPU订阅"
    return "免费+内购/广告"


def calc_potential(rank_category, rating_count, category_id=None):
    """潜力指数：基于下载量/收入（排名越靠前=下载越大=潜力越高），和评价数无关"""
    if rank_category is None:
        return None
    dl = estimate_downloads(rank_category, category_id=category_id)
    if dl <= 0:
        return 0
    if dl >= 500000:
        return min(100, 95)
    elif dl >= 100000:
        return min(100, 70 + (dl - 100000) / 400000 * 25)
    elif dl >= 30000:
        return 40 + (dl - 30000) / 70000 * 30
    elif dl >= 10000:
        return 20 + (dl - 10000) / 20000 * 20
    else:
        return max(5, dl / 10000 * 20)


def potential_score_html(score):
    if score is None:
        return '<span style="color:#64748b">N/A</span>'
    s = round(score)
    if s >= 70:
        color = "#ef4444"
    elif s >= 40:
        color = "#f97316"
    else:
        color = "#64748b"
    return (
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="width:50px;height:8px;background:#0f172a;border-radius:4px;overflow:hidden;">'
        f'<div style="width:{s}%;height:100%;background:{color};border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-size:11px;font-weight:700;color:{color};">{s}</span>'
        f'</div>'
    )


def rating_stars(rating_avg):
    if rating_avg is None:
        return '<span style="color:#64748b">N/A</span>'
    full = int(rating_avg)
    half = 1 if rating_avg - full >= 0.5 else 0
    empty = 5 - full - half
    stars = "★" * full + ("½" if half else "") + "☆" * empty
    if rating_avg >= 4.5:
        color = "#22c55e"
    elif rating_avg >= 4.0:
        color = "#a3e635"
    elif rating_avg >= 3.0:
        color = "#facc15"
    else:
        color = "#f87171"
    return f'<span style="color:{color}" title="{rating_avg:.1f}">{stars} {rating_avg:.1f}</span>'


def format_rating_count(count):
    if count is None:
        return "N/A"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1000:
        return f"{count / 1000:.1f}K"
    return str(count)


def format_price(price):
    if price is None or price in ("Free", "Get", "0", "0.00", ""):
        return '<span style="color:#22c55e;font-weight:600">Free</span>'
    return f'<span style="color:#fbbf24;font-weight:600">{html.escape(str(price))}</span>'


def overall_rank_badge(rank):
    if rank is None:
        return '<span style="color:#64748b">-</span>'
    if rank <= 10:
        bg, color = "#dc2626", "#fff"
    elif rank <= 50:
        bg, color = "#ea580c", "#fff"
    elif rank <= 100:
        bg, color = "#6366f1", "#fff"
    elif rank <= 200:
        bg, color = "#1e293b", "#e2e8f0"
    else:
        bg, color = "#1e293b", "#94a3b8"
    return f'<span style="background:{bg};color:{color};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600">#{rank}</span>'


def category_rank_badge(rank):
    if rank is None:
        return '<span style="color:#64748b">-</span>'
    if rank <= 5:
        bg, color = "#16a34a", "#fff"
    elif rank <= 10:
        bg, color = "#22c55e", "#fff"
    elif rank <= 20:
        bg, color = "#6366f1", "#fff"
    elif rank <= 30:
        bg, color = "#1e293b", "#e2e8f0"
    else:
        bg, color = "#1e293b", "#94a3b8"
    return f'<span style="background:{bg};color:{color};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600">#{rank}</span>'


def esc(text):
    if text is None:
        return ""
    return html.escape(str(text))


def app_icon_html(icon_url, app_name):
    first_letter = esc((app_name or "?")[0]).upper()
    if icon_url:
        return (
            f'<span class="app-icon-wrap">'
            f'<img src="{esc(icon_url)}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'" loading="lazy">'
            f'<span class="app-icon-letter" style="display:none">{first_letter}</span>'
            f'</span>'
        )
    return f'<span class="app-icon-wrap"><span class="app-icon-letter">{first_letter}</span></span>'


def app_name_with_icon(icon_url, app_name, app_id):
    icon = app_icon_html(icon_url, app_name)
    name_escaped = esc(app_name or "未知")
    link = f'<a class="app-link" href="https://apps.apple.com/app/id{esc(app_id)}" target="_blank">{name_escaped}</a>'
    return f'<div style="display:flex;align-items:center;gap:8px;">{icon}{link}</div>'


def generate_report():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    latest_date_row = c.execute("SELECT MAX(date) FROM app_daily_rank").fetchone()
    report_date = latest_date_row[0] if latest_date_row and latest_date_row[0] else datetime.date.today().isoformat()

    stats_categories = c.execute("SELECT COUNT(DISTINCT category_id) FROM app_daily_rank WHERE category_id != 'overall' AND date=?", (report_date,)).fetchone()[0]
    stats_unique_apps = c.execute("SELECT COUNT(DISTINCT app_id) FROM app_daily_rank WHERE date=?", (report_date,)).fetchone()[0]
    stats_details = c.execute("SELECT COUNT(*) FROM app_details").fetchone()[0]
    stats_quiet = c.execute("SELECT COUNT(*) FROM discovered_gems WHERE discovery_type='闷声型' AND date=?", (report_date,)).fetchone()[0]
    stats_indie = c.execute("SELECT COUNT(*) FROM discovered_gems WHERE discovery_type='草根型' AND date=?", (report_date,)).fetchone()[0]
    stats_total_gems = c.execute("SELECT COUNT(*) FROM discovered_gems WHERE date=?", (report_date,)).fetchone()[0]

    # 获取所有国家
    countries_in_db = [row[0] for row in c.execute("SELECT DISTINCT country FROM app_daily_rank WHERE date=? ORDER BY country", (report_date,)).fetchall()]
    country_options = ""
    for cc in countries_in_db:
        cname = COUNTRIES.get(cc, cc.upper())
        country_options += f'<option value="{cc}">{cname} ({cc.upper()})</option>\n'

    overall_top20 = c.execute("""
        SELECT ct.rank, ct.app_id, d.app_name, d.developer_name,
               d.rating_count, d.rating_avg, d.price, d.icon_url, ct.country
        FROM app_chart_type ct
        LEFT JOIN app_details d ON ct.app_id = d.app_id
        WHERE ct.category_id = 'overall'
          AND ct.chart_type = 'overall_topgrossing'
          AND ct.date = ?
        ORDER BY ct.rank ASC
        LIMIT 20
    """, (report_date,)).fetchall()

    quiet_rows = c.execute("""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               d.bundle_id, ct.rank as overall_rank, r.app_id,
               d.current_version_rating, d.current_version_count,
               d.release_date, d.updated_date, d.languages, d.icon_url
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        WHERE r.date = ? AND r.category_id != 'overall'
          AND r.rank_category <= 50
          AND (d.rating_count < 5000 OR d.rating_count IS NULL)
        ORDER BY r.rank_category ASC, d.rating_count ASC
    """, (report_date, report_date)).fetchall()

    where_parts = " OR ".join([f"d.developer_name NOT LIKE ?" for _ in KNOWN_PUBLISHERS])
    indie_rows = c.execute(f"""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               d.bundle_id, ct.rank as overall_rank, r.app_id, d.icon_url
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        WHERE r.date = ?
          AND r.category_id != 'overall'
          AND r.rank_category <= 30
          AND ({where_parts} OR d.developer_name IS NULL)
        ORDER BY r.rank_category ASC
    """, (report_date, report_date, *[f"%{p}%" for p in KNOWN_PUBLISHERS])).fetchall()

    # 低分高收型：评分低(<3.5)但畅销排名靠前(<=30)，说明用户花钱但不满意=机会
    low_rating_gems = c.execute("""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               d.bundle_id, ct.rank as overall_rank, r.app_id,
               d.current_version_rating, d.current_version_count,
               d.release_date, d.updated_date, d.languages, d.icon_url
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        WHERE r.date = ? AND r.category_id != 'overall'
          AND r.rank_category <= 30
          AND (d.rating_avg IS NOT NULL AND d.rating_avg > 0 AND d.rating_avg < 3.5)
          AND d.rating_count >= 100
        ORDER BY d.rating_avg ASC, r.rank_category ASC
    """, (report_date, report_date)).fetchall()

    cat_top10_sections = []
    for cat_id, cat_name in CATEGORIES.items():
        rows = c.execute("""
            SELECT r.rank_category, r.app_id, r.app_name, r.developer_name,
                   d.rating_count, d.rating_avg, d.price, d.icon_url,
                   (SELECT MIN(ct2.rank) FROM app_chart_type ct2
                    WHERE ct2.app_id = r.app_id
                      AND ct2.category_id = 'overall'
                      AND ct2.chart_type = 'overall_topgrossing'
                      AND ct2.date = r.date) as overall_rank
            FROM app_daily_rank r
            LEFT JOIN app_details d ON r.app_id = d.app_id
            WHERE r.date = ? AND r.category_id = ?
            ORDER BY r.rank_category ASC
            LIMIT 10
        """, (report_date, cat_id)).fetchall()
        cat_top10_sections.append((cat_id, cat_name, rows))

    cat_overview_data = []
    for cat_id, cat_name in CATEGORIES.items():
        cnt = c.execute("SELECT COUNT(*) FROM app_daily_rank WHERE date=? AND category_id=?", (report_date, cat_id)).fetchone()[0]
        cat_overview_data.append((cat_id, cat_name, cnt))

    conn.close()

    total_est_downloads = sum(estimate_downloads(r['rank'], r['country'] if r['country'] else 'us') for r in overall_top20 if r['rank'])
    avg_potential_quiet = 0
    quiet_potentials = [calc_potential(r['rank_category'], r['rating_count'], category_id=r['category_id']) for r in quiet_rows if r['rank_category'] is not None]
    if quiet_potentials:
        avg_potential_quiet = sum(quiet_potentials) / len(quiet_potentials)

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>iOS 细分畅销榜情报报告 - {esc(report_date)}</title>
<style>
:root {{
  --bg: #0f172a;
  --card: #1e293b;
  --card-hover: #263548;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --accent: #6366f1;
  --accent-light: #818cf8;
  --accent-glow: rgba(99,102,241,0.25);
  --green: #22c55e;
  --red: #ef4444;
  --amber: #fbbf24;
  --border: #334155;
  --radius: 12px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  line-height: 1.6;
  min-height: 100vh;
}}
.container {{ max-width:1440px; margin:0 auto; padding:20px; }}

.banner {{
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  border-radius: var(--radius);
  padding: 44px 36px;
  margin-bottom: 28px;
  position: relative;
  overflow: hidden;
}}
.banner::before {{
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
  border-radius: 50%;
}}
.banner::after {{
  content: '';
  position: absolute;
  bottom: -30%; left: -5%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
  border-radius: 50%;
}}
.banner h1 {{ font-size:30px; color:#fff; font-weight:800; position:relative; letter-spacing:-0.5px; }}
.banner .subtitle {{ font-size:15px; color:rgba(255,255,255,0.88); margin-top:10px; position:relative; }}
.banner .date-badge {{
  display:inline-block; background:rgba(255,255,255,0.2); padding:5px 16px;
  border-radius:20px; font-size:13px; color:#fff; margin-top:14px; position:relative;
  backdrop-filter:blur(4px);
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}}
.stat-card {{
  background: var(--card);
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
  border: 1px solid var(--border);
  transition: transform 0.2s, box-shadow 0.2s;
}}
.stat-card:hover {{ transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.3); }}
.stat-card .stat-value {{
  font-size:28px; font-weight:700; color:var(--accent-light);
}}
.stat-card .stat-label {{ font-size:12px; color:var(--text-muted); margin-top:4px; text-transform:uppercase; letter-spacing:0.5px; }}
.stat-card.accent .stat-value {{ color: #22c55e; }}
.stat-card.warn .stat-value {{ color: #fbbf24; }}
.stat-card.info .stat-value {{ color: #38bdf8; }}

.section {{ margin-bottom: 36px; }}
.section-title {{
  font-size:20px; font-weight:700; margin-bottom:18px;
  padding-bottom:10px; border-bottom:2px solid var(--accent);
  display:flex; align-items:center; gap:10px;
}}
.section-title .icon {{ font-size:24px; }}
.section-title .decor {{
  display:inline-block; width:8px; height:8px;
  background:var(--accent); border-radius:2px;
  transform:rotate(45deg); margin-left:4px; opacity:0.6;
}}

.cat-grid {{
  display:grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap:12px;
  margin-bottom:32px;
}}
.cat-item {{
  background:var(--card); border-radius:var(--radius); padding:16px 12px;
  text-align:center; border:1px solid var(--border);
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
  cursor:pointer;
}}
.cat-item:hover {{ transform:translateY(-2px); border-color:var(--accent); box-shadow:0 4px 16px var(--accent-glow); }}
.cat-item .cat-name {{ font-size:15px; font-weight:600; margin-bottom:4px; }}
.cat-item .cat-count {{ font-size:13px; color:var(--accent-light); }}

.table-wrap {{
  overflow-x:auto;
  border-radius:var(--radius);
  border:1px solid var(--border);
  margin-bottom:24px;
}}
table {{
  width:100%; border-collapse:collapse; font-size:13px;
}}
thead {{ background:#1a2744; }}
th {{
  padding:12px 14px; text-align:left; font-weight:600;
  color:var(--accent-light); border-bottom:2px solid var(--accent);
  white-space:nowrap;
}}
td {{ padding:10px 14px; border-bottom:1px solid var(--border); }}
tbody tr {{ transition: background 0.15s; }}
tbody tr:hover {{ background:var(--card-hover); }}
tbody tr.highlight-low {{ background:rgba(239,68,68,0.08); }}
tbody tr.highlight-low:hover {{ background:rgba(239,68,68,0.15); }}

a.app-link {{ color:var(--accent-light); text-decoration:none; white-space:nowrap; }}
a.app-link:hover {{ text-decoration:underline; }}

.app-icon-wrap {{
  display:inline-flex; width:40px; height:40px; border-radius:10px;
  overflow:hidden; background:var(--accent); flex-shrink:0;
  align-items:center; justify-content:center; vertical-align:middle;
}}
.app-icon-wrap img {{
  width:40px; height:40px; object-fit:cover; border-radius:10px;
}}
.app-icon-letter {{
  color:#fff; font-size:18px; font-weight:700;
  display:flex; width:100%; height:100%; align-items:center;
  justify-content:center;
}}

.filter-bar {{
  display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; align-items:center;
}}
.filter-bar select, .filter-bar input {{
  background:var(--card); color:var(--text); border:1px solid var(--border);
  border-radius:8px; padding:8px 12px; font-size:13px;
  outline:none; transition:border-color 0.2s;
}}
.filter-bar select:focus, .filter-bar input:focus {{ border-color:var(--accent); }}
.filter-bar input {{ min-width:200px; }}

.top10-grid {{
  display:grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap:20px;
  margin-bottom:32px;
}}
.top10-card {{
  background:var(--card);
  border-radius:var(--radius);
  border:1px solid var(--border);
  overflow:hidden;
  transition:box-shadow 0.2s;
}}
.top10-card:hover {{ box-shadow:0 4px 20px var(--accent-glow); }}
.top10-card-header {{
  background:linear-gradient(135deg,var(--accent),#8b5cf6);
  padding:14px 18px; font-size:16px; font-weight:700; color:#fff;
  display:flex; align-items:center; gap:8px;
}}
.top10-card table {{ width:100%; border-collapse:collapse; }}
.top10-card td {{ padding:7px 10px; border-bottom:1px solid var(--border); font-size:12px; }}
.top10-card td:first-child {{
  width:30px; text-align:center; font-weight:700; color:var(--accent-light);
}}

.scroll-top {{
  position:fixed; bottom:24px; right:24px; width:44px; height:44px;
  background:var(--accent); color:#fff; border:none; border-radius:50%;
  font-size:20px; cursor:pointer; display:none; z-index:1000;
  box-shadow:0 4px 12px rgba(99,102,241,0.4); transition:opacity 0.3s;
}}
.scroll-top:hover {{ background:var(--accent-light); }}

@media (max-width:768px) {{
  .container {{ padding:12px; }}
  .banner h1 {{ font-size:20px; }}
  .banner {{ padding:28px 20px; }}
  .stats-grid {{ grid-template-columns:repeat(3,1fr); gap:8px; }}
  .stat-card {{ padding:12px; }}
  .stat-card .stat-value {{ font-size:20px; }}
  .top10-grid {{ grid-template-columns:1fr; }}
  .cat-grid {{ grid-template-columns:repeat(3,1fr); }}
}}
</style>
</head>
<body>
<div class="container">

<div class="banner">
  <h1>📱 iOS 细分畅销榜情报报告</h1>
  <div class="subtitle">✦ 基于 App Store 22 个细分品类畅销榜数据，自动发现闷声型 & 草根型机会 ✦</div>
  <div class="date-badge">📅 {esc(report_date)}</div>
  <div style="margin-top:12px;position:relative;">
    <label style="color:rgba(255,255,255,0.7);font-size:13px;margin-right:8px;">🌍 选择国家：</label>
    <select id="country-select" style="background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.3);border-radius:8px;padding:6px 14px;font-size:14px;cursor:pointer;">
{country_options}    </select>
  </div>
</div>

<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-value">{stats_categories}</div>
    <div class="stat-label">品类覆盖</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{stats_unique_apps}</div>
    <div class="stat-label">唯一应用</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{stats_details}</div>
    <div class="stat-label">详情条数</div>
  </div>
  <div class="stat-card accent">
    <div class="stat-value">{stats_quiet}</div>
    <div class="stat-label">🤫 闷声型</div>
  </div>
  <div class="stat-card warn">
    <div class="stat-value">{stats_indie}</div>
    <div class="stat-label">🌱 草根型</div>
  </div>
  <div class="stat-card" style="background:#1e293b;border-color:#ef4444">
    <div class="stat-value" style="color:#ef4444">{len(low_rating_gems)}</div>
    <div class="stat-label">🔥 低分高收型</div>
  </div>
  <div class="stat-card info">
    <div class="stat-value">{stats_total_gems}</div>
    <div class="stat-label">💎 总发现数</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{format_downloads(total_est_downloads)}</div>
    <div class="stat-label">📊 Top20下载预估</div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 品类覆盖 <span class="decor"></span></div>
  <div class="cat-grid">
"""

    for cat_id, cat_name, cnt in cat_overview_data:
        page += f"""    <div class="cat-item" onclick="document.getElementById('cat-{cat_id}').scrollIntoView({{behavior:'smooth'}})">
      <div class="cat-name">{esc(cat_name)}</div>
      <div class="cat-count">{cnt} 个应用</div>
    </div>
"""

    page += """  </div>
</div>

"""

    page += """<!-- Overall Top 20 -->
<div class="section">
  <div class="section-title"><span class="icon">🏆</span> 畅销总榜 Top 20 <span class="decor"></span></div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>排名</th>
          <th>应用</th>
          <th>开发商</th>
          <th>评价数</th>
          <th>评分</th>
          <th>价格</th>
          <th>下载量预估</th>
          <th>月收入预估</th>
        </tr>
      </thead>
      <tbody>
"""
    for row in overall_top20:
        rank = row['rank']
        app_id = row['app_id'] or ""
        app_name = row['app_name'] or ""
        dev_name = esc(row['developer_name'] or "")
        rating_count = row['rating_count']
        rating_avg = row['rating_avg']
        price = row['price']
        icon_url = row['icon_url']
        country = row['country'] or "us"
        dl = estimate_downloads(rank, country)
        rev = format_revenue_from_downloads(dl, price)
        page += f"""        <tr data-country="{esc(country)}">
          <td>{overall_rank_badge(rank)}</td>
          <td>{app_name_with_icon(icon_url, app_name, app_id)}</td>
          <td>{dev_name}</td>
          <td>{format_rating_count(rating_count)}</td>
          <td>{rating_stars(rating_avg)}</td>
          <td>{format_price(price)}</td>
          <td>{format_downloads(dl)}</td>
          <td>{rev}</td>
        </tr>
"""

    page += """      </tbody>
    </table>
  </div>
</div>

"""

    page += """<!-- 闷声型发现 -->
<div class="section">
  <div class="section-title"><span class="icon">🤫</span> 闷声型发现 <span style="font-size:14px;color:var(--text-muted);font-weight:400">（分类 Top50 + 评价 &lt; 5,000）</span> <span class="decor"></span></div>
  <div class="filter-bar">
    <select id="quiet-cat-filter">
      <option value="">全部分类</option>
"""
    for cid, cname in CATEGORIES.items():
        page += f'      <option value="{esc(cname)}">{esc(cname)}</option>\n'
    page += """    </select>
    <select id="quiet-sort">
      <option value="rank">按分类排名</option>
      <option value="rating">按评价数</option>
      <option value="overall">按总榜排名</option>
      <option value="potential">按潜力指数</option>
    </select>
    <input type="text" id="quiet-search" placeholder="🔍 搜索应用名/开发商...">
  </div>
  <div class="table-wrap">
    <table id="quiet-table">
      <thead>
        <tr>
          <th>分类排名</th>
          <th>总榜</th>
          <th>分类</th>
          <th>应用</th>
          <th>开发商</th>
          <th>评价数</th>
          <th>评分</th>
          <th>价格</th>
          <th>下载量预估</th>
          <th>月收入预估</th>
          <th>潜力指数</th>
        </tr>
      </thead>
      <tbody>
"""
    for row in quiet_rows:
        cat_rank = row['rank_category']
        overall_rank = row['overall_rank']
        cat_name = esc(row['category_name'] or "")
        app_id = row['app_id'] or ""
        app_name = row['app_name'] or ""
        dev_name = esc(row['developer_name'] or "")
        rating_count = row['rating_count']
        rating_avg = row['rating_avg']
        price = row['price']
        icon_url = row['icon_url']
        is_low = rating_count is not None and rating_count < 500
        tr_class = ' class="highlight-low"' if is_low else ""
        if overall_rank:
            dl = estimate_downloads(overall_rank, row['country'] if row['country'] else 'us')
        else:
            dl = estimate_downloads(cat_rank, row['country'] if row['country'] else 'us', category_id=row['category_id'])
        rev = format_revenue_from_downloads(dl, price)
        pot = calc_potential(cat_rank, rating_count, category_id=row['category_id'])

        page += f"""        <tr{tr_class} data-cat="{esc(row['category_name'] or '')}" data-country="{esc(row['country'] or '')}" data-rating="{rating_count or 0}" data-overall="{overall_rank or 9999}" data-potential="{int(pot) if pot is not None else 0}" data-search="{esc((row['app_name'] or '').lower() + ' ' + (row['developer_name'] or '').lower())}">
          <td>{category_rank_badge(cat_rank)}</td>
          <td>{overall_rank_badge(overall_rank)}</td>
          <td>{cat_name}</td>
          <td>{app_name_with_icon(icon_url, app_name, app_id)}</td>
          <td>{dev_name}</td>
          <td>{format_rating_count(rating_count)}</td>
          <td>{rating_stars(rating_avg)}</td>
          <td>{format_price(price)}</td>
          <td>{format_downloads(dl)}</td>
          <td>{rev}</td>
          <td>{potential_score_html(pot)}</td>
        </tr>
"""

    page += """      </tbody>
    </table>
  </div>
</div>

"""

    page += """<!-- 草根型发现 -->
<div class="section">
  <div class="section-title"><span class="icon">🌱</span> 草根型发现 <span style="font-size:14px;color:var(--text-muted);font-weight:400">（分类 Top30 + 非知名开发商）</span> <span class="decor"></span></div>
  <div class="filter-bar">
    <select id="indie-cat-filter">
      <option value="">全部分类</option>
"""
    for cid, cname in CATEGORIES.items():
        page += f'      <option value="{esc(cname)}">{esc(cname)}</option>\n'
    page += """    </select>
    <select id="indie-sort">
      <option value="rank">按分类排名</option>
      <option value="potential">按潜力指数</option>
    </select>
    <input type="text" id="indie-search" placeholder="🔍 搜索应用名/开发商...">
  </div>
  <div class="table-wrap">
    <table id="indie-table">
      <thead>
        <tr>
          <th>分类排名</th>
          <th>总榜</th>
          <th>分类</th>
          <th>应用</th>
          <th>开发商</th>
          <th>评价数</th>
          <th>评分</th>
          <th>价格</th>
          <th>下载量预估</th>
          <th>月收入预估</th>
          <th>潜力指数</th>
        </tr>
      </thead>
      <tbody>
"""
    for row in indie_rows:
        cat_rank = row['rank_category']
        overall_rank = row['overall_rank']
        cat_name = esc(row['category_name'] or "")
        app_id = row['app_id'] or ""
        app_name = row['app_name'] or ""
        dev_name = esc(row['developer_name'] or "")
        rating_count = row['rating_count']
        rating_avg = row['rating_avg']
        price = row['price']
        icon_url = row['icon_url']
        is_low = rating_count is not None and rating_count < 500
        tr_class = ' class="highlight-low"' if is_low else ""
        if overall_rank:
            dl = estimate_downloads(overall_rank, row['country'] if row['country'] else 'us')
        else:
            dl = estimate_downloads(cat_rank, row['country'] if row['country'] else 'us', category_id=row['category_id'])
        rev = format_revenue_from_downloads(dl, price)
        pot = calc_potential(cat_rank, rating_count, category_id=row['category_id'])

        page += f"""        <tr{tr_class} data-cat="{esc(row['category_name'] or '')}" data-country="{esc(row['country'] or '')}" data-potential="{int(pot) if pot is not None else 0}" data-search="{esc((row['app_name'] or '').lower() + ' ' + (row['developer_name'] or '').lower())}">
          <td>{category_rank_badge(cat_rank)}</td>
          <td>{overall_rank_badge(overall_rank)}</td>
          <td>{cat_name}</td>
          <td>{app_name_with_icon(icon_url, app_name, app_id)}</td>
          <td>{dev_name}</td>
          <td>{format_rating_count(rating_count)}</td>
          <td>{rating_stars(rating_avg)}</td>
          <td>{format_price(price)}</td>
          <td>{format_downloads(dl)}</td>
          <td>{rev}</td>
          <td>{potential_score_html(pot)}</td>
        </tr>
"""

    page += """      </tbody>
    </table>
  </div>
</div>

"""

    # ==================== 低分高收型 ====================
    page += """<!-- 低分高收型发现 -->
<div class="section">
  <div class="section-title"><span class="icon">🔥</span> 低分高收型 <span style="font-size:14px;color:var(--text-muted);font-weight:400">（评分 &lt; 3.5 + 畅销 Top30 → 需求未被满足=机会）</span> <span class="decor"></span></div>
  <div class="filter-bar">
    <select id="lowrat-cat-filter">
      <option value="">全部分类</option>
"""
    for cid, cname in CATEGORIES.items():
        page += f'      <option value="{esc(cname)}">{esc(cname)}</option>\n'
    page += """    </select>
    <input type="text" id="lowrat-search" placeholder="🔍 搜索应用名/开发商..." style="width:220px">
  </div>
  <div class="table-wrap">
    <table id="lowrat-table">
      <thead>
        <tr>
          <th>分类排名</th>
          <th>总榜</th>
          <th>分类</th>
          <th>应用</th>
          <th>开发商</th>
          <th>评价数</th>
          <th>评分</th>
          <th>价格</th>
          <th>下载量预估</th>
          <th>月收入预估</th>
          <th>潜力指数</th>
        </tr>
      </thead>
      <tbody>
"""
    for row in low_rating_gems:
        cat_rank = row['rank_category']
        overall_rank = row['overall_rank']
        cat_name = esc(row['category_name'] or "")
        app_id = row['app_id'] or ""
        app_name = row['app_name'] or ""
        dev_name = esc(row['developer_name'] or "")
        rating_count = row['rating_count']
        rating_avg = row['rating_avg']
        price = row['price']
        icon_url = row['icon_url']
        country = row['country'] or "us"
        if overall_rank:
            dl = estimate_downloads(overall_rank, country)
        else:
            dl = estimate_downloads(cat_rank, country, category_id=row['category_id'])
        rev = format_revenue_from_downloads(dl, price)
        pot = calc_potential(cat_rank, rating_count, category_id=row['category_id'])

        # 低分高收型高亮
        tr_class = ' class="highlight-low"'

        page += f"""        <tr{tr_class} data-cat="{esc(row['category_name'] or '')}" data-country="{esc(country)}" data-potential="{int(pot) if pot is not None else 0}" data-search="{esc((row['app_name'] or '').lower() + ' ' + (row['developer_name'] or '').lower())}">
          <td>{category_rank_badge(cat_rank)}</td>
          <td>{overall_rank_badge(overall_rank)}</td>
          <td>{cat_name}</td>
          <td>{app_name_with_icon(icon_url, app_name, app_id)}</td>
          <td>{dev_name}</td>
          <td>{format_rating_count(rating_count)}</td>
          <td>{rating_stars(rating_avg)}</td>
          <td>{format_price(price)}</td>
          <td>{format_downloads(dl)}</td>
          <td>{rev}</td>
          <td>{potential_score_html(pot)}</td>
        </tr>
"""

    page += """      </tbody>
    </table>
  </div>
</div>

"""

    page += """<!-- Category Top 10 -->
<div class="section">
  <div class="section-title"><span class="icon">🔥</span> 各品类 Top 10 <span class="decor"></span></div>
  <div class="top10-grid">
"""
    for cat_id, cat_name, rows in cat_top10_sections:
        if not rows:
            continue
        page += f"""    <div class="top10-card" id="cat-{cat_id}">
      <div class="top10-card-header">📱 {esc(cat_name)} Top 10</div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>应用</th>
            <th>评价</th>
            <th>评分</th>
            <th>价格</th>
            <th>下载量预估</th>
            <th>潜力</th>
          </tr>
        </thead>
        <tbody>
"""
        for row in rows:
            rank = row['rank_category']
            app_id = row['app_id'] or ""
            app_name = row['app_name'] or ""
            dev_name_escaped = esc(row['developer_name'] or "")
            rating_count = row['rating_count']
            rating_avg = row['rating_avg']
            price = row['price']
            icon_url = row['icon_url']
            overall_rank_val = row['overall_rank']
            if overall_rank_val:
                dl = estimate_downloads(overall_rank_val)
            else:
                dl = estimate_downloads(rank, category_id=cat_id)
            pot = calc_potential(rank, rating_count, category_id=cat_id)
            page += f"""          <tr>
            <td>{category_rank_badge(rank)}</td>
            <td>{app_name_with_icon(icon_url, app_name, app_id)}</td>
            <td>{format_rating_count(rating_count)}</td>
            <td>{rating_stars(rating_avg)}</td>
            <td>{format_price(price)}</td>
            <td>{format_downloads(dl)}</td>
            <td>{potential_score_html(pot)}</td>
          </tr>
"""
        page += """        </tbody>
      </table>
    </div>
"""

    page += """  </div>
</div>

</div>

<button class="scroll-top" id="scrollTopBtn" onclick="window.scrollTo({top:0,behavior:'smooth'})">&#8679;</button>

<script>
window.onscroll = function() {
  document.getElementById('scrollTopBtn').style.display = window.scrollY > 400 ? 'block' : 'none';
};

function filterTable(tableId, catFilterId, searchId, sortId) {
  var table = document.getElementById(tableId);
  if (!table) return;
  var rows = table.querySelectorAll('tbody tr');
  var catVal = catFilterId ? document.getElementById(catFilterId).value : '';
  var searchVal = searchId ? document.getElementById(searchId).value.toLowerCase() : '';
  var sortVal = sortId ? document.getElementById(sortId).value : 'rank';
  var countryVal = document.getElementById('country-select') ? document.getElementById('country-select').value : '';

  var filtered = [];
  rows.forEach(function(row) {
    var cat = row.getAttribute('data-cat') || '';
    var search = row.getAttribute('data-search') || '';
    var country = row.getAttribute('data-country') || '';
    var catMatch = !catVal || cat === catVal;
    var searchMatch = !searchVal || search.indexOf(searchVal) !== -1;
    var countryMatch = !countryVal || country === countryVal;
    if (catMatch && searchMatch && countryMatch) {
      row.style.display = '';
      filtered.push(row);
    } else {
      row.style.display = 'none';
    }
  });

  if (sortVal === 'rating') {
    filtered.sort(function(a, b) {
      return parseFloat(a.getAttribute('data-rating')) - parseFloat(b.getAttribute('data-rating'));
    });
  } else if (sortVal === 'overall') {
    filtered.sort(function(a, b) {
      return parseFloat(a.getAttribute('data-overall')) - parseFloat(b.getAttribute('data-overall'));
    });
  } else if (sortVal === 'potential') {
    filtered.sort(function(a, b) {
      return parseFloat(b.getAttribute('data-potential')) - parseFloat(a.getAttribute('data-potential'));
    });
  } else {
    filtered.sort(function(a, b) {
      return parseFloat(a.getAttribute('data-rating')) > 0
        ? parseFloat(a.getAttribute('data-rating')) - parseFloat(b.getAttribute('data-rating'))
        : 0;
    });
  }

  var tbody = table.querySelector('tbody');
  filtered.forEach(function(row) { tbody.appendChild(row); });
}

function filterAllTables() {
  filterTable('quiet-table', 'quiet-cat-filter', 'quiet-search', 'quiet-sort');
  filterTable('indie-table', 'indie-cat-filter', 'indie-search', 'indie-sort');
  filterTable('lowrat-table', 'lowrat-cat-filter', 'lowrat-search', null);
}

document.getElementById('quiet-cat-filter').addEventListener('change', filterAllTables);
document.getElementById('quiet-sort').addEventListener('change', filterAllTables);
document.getElementById('quiet-search').addEventListener('input', filterAllTables);
document.getElementById('indie-cat-filter').addEventListener('change', filterAllTables);
document.getElementById('indie-sort').addEventListener('change', filterAllTables);
document.getElementById('indie-search').addEventListener('input', filterAllTables);
document.getElementById('lowrat-cat-filter').addEventListener('change', filterAllTables);
document.getElementById('lowrat-search').addEventListener('input', filterAllTables);
document.getElementById('country-select').addEventListener('change', filterAllTables);

filterAllTables();
</script>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"✅ 报告已生成: {OUTPUT_PATH}")
    print(f"   闷声型: {len(quiet_rows)} 条")
    print(f"   草根型: {len(indie_rows)} 条")
    print(f"   低分高收型: {len(low_rating_gems)} 条")
    print(f"   总榜 Top20: {len(overall_top20)} 条")
    print(f"   品类 Top10: {len(cat_top10_sections)} 个分类")


if __name__ == "__main__":
    generate_report()