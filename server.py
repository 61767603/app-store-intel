#!/usr/bin/env python3
"""
iOS 细分畅销榜情报 - Web 服务端
=================================
提供 JSON API 供前端动态加载，无需每次重新生成 HTML。

启动方式：
  python server.py              # 默认 8500 端口
  python server.py -p 3000      # 指定端口
"""

import http.server
import json
import sqlite3
import os
import sys
import io
import urllib.parse
import argparse
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_intel.db")
GP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gp_intel.db")
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

CATEGORIES = {
    "6000": "商业", "6001": "天气", "6002": "工具", "6003": "教育",
    "6004": "社交", "6005": "娱乐", "6006": "财务", "6007": "健康健美",
    "6008": "音乐", "6009": "医疗", "6010": "导航", "6011": "新闻",
    "6012": "摄影与录像", "6013": "效率", "6014": "参考", "6015": "购物",
    "6016": "生活方式", "6017": "体育", "6018": "旅行",
    "6020": "图书", "6021": "美食佳饮", "6023": "杂志报纸",
}

COUNTRY_NAMES = {
    "us": "🇺🇸 美国", "jp": "🇯🇵 日本", "gb": "🇬🇧 英国", "de": "🇩🇪 德国",
    "kr": "🇰🇷 韩国", "sa": "🇸🇦 沙特", "au": "🇦🇺 澳洲", "ca": "🇨🇦 加拿大",
    "fr": "🇫🇷 法国", "br": "🇧🇷 巴西", "tr": "🇹🇷 土耳其", "id": "🇮🇩 印尼",
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
    "Anthropic", "Match", "Bumble",
]

COUNTRY_PARAM_MAP = {
    "us": "us", "jp": "jp", "gb": "gb", "de": "de",
    "kr": "kr", "sa": "sa", "au": "au", "ca": "ca",
    "fr": "fr", "br": "br", "tr": "tr", "id": "id",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== 下载量预估模型（仅 iPhone） ====================
# 核心公式: daily = BASE × rank^(-b) × country_factor × cat_factor
#
# 七麦数据校准 (2026-07-05):
#   总榜#1 ChatGPT ≈ 174,882/天, #5 ≈ 190,150, #10 ≈ 25,016
#   拟合: a=366,878  b=1.1681  R²=0.777

OVERALL_BASE = 366878        # 美国非游戏总榜#1日下载量 (七麦校准 2026-07-05)
POWER_ALPHA = 1.1681         # power law 衰减指数 (七麦校准 2026-07-05)
GAME_POWER_ALPHA = 0.55      # 游戏榜头部集中度更高
GAME_BASE = 93000            # 美国游戏总榜#1日下载量中位数

# 国家因子: 基于 App Store 各市场相对规模 (下载量+收入综合)
# 同一排名在不同国家的绝对下载量差异巨大
COUNTRY_FACTOR = {
    "us": 1.00, "jp": 0.25, "gb": 0.10, "de": 0.08,
    "kr": 0.06, "fr": 0.05, "ca": 0.04, "au": 0.04,
    "br": 0.03, "sa": 0.02, "tr": 0.02, "id": 0.02,
}

# 分类渗透因子: 分类#1的日下载量 ≈ 总榜#K的日下载量，K = cat_factor 反推的排名
# 即 cat_factor = K^(-b)，表示该分类头部相当于总榜多深的渗透
# Tier 1 (头部品类): 社交/娱乐/摄影/音乐/购物  → #1 ≈ 总榜#6-16
# Tier 2 (中型品类): 商业/教育/财务/新闻/工具/效率/体育/旅行/生活  → #1 ≈ 总榜#25-65
# Tier 3 (小型品类): 健康/图书/美食/天气/医疗/导航/参考/杂志  → #1 ≈ 总榜#100-280
CATEGORY_FACTOR = {
    "6004": 0.40,  # 社交 - 头部品类, cat#1 ≈ 总榜#6
    "6005": 0.35,  # 娱乐
    "6012": 0.30,  # 摄影与录像
    "6008": 0.28,  # 音乐
    "6015": 0.25,  # 购物
    "6000": 0.20,  # 商业 - 中型品类
    "6003": 0.18,  # 教育
    "6006": 0.18,  # 财务
    "6011": 0.17,  # 新闻
    "6002": 0.15,  # 工具
    "6013": 0.15,  # 效率
    "6017": 0.14,  # 体育
    "6018": 0.14,  # 旅行
    "6016": 0.13,  # 生活方式
    "6007": 0.11,  # 健康健美 - 小型品类
    "6020": 0.09,  # 图书
    "6021": 0.09,  # 美食佳饮
    "6001": 0.08,  # 天气
    "6009": 0.07,  # 医疗
    "6010": 0.07,  # 导航
    "6014": 0.06,  # 参考
    "6023": 0.06,  # 杂志报纸
}


def estimate_downloads(rank, country="us", category_id=None, is_game=False):
    """
    估算月下载量（仅 iPhone），基于幂律曲线 power law。

    锚点: 七麦 2026-07-05 校准
      - 非游戏#1 ≈ 174,882/天, b ≈ 1.1681
      - 游戏#1 ≈ 93,000/天, b ≈ 0.55 (头部更集中)

    总榜:   monthly = OVERALL_BASE × rank^(-b) × country × 30
    分类榜: monthly = OVERALL_BASE × cat_factor × rank^(-b) × country × 30

    重要: 分类排名必须传入 category_id，否则会当作总榜排名导致严重高估。
    """
    if not rank or rank <= 0:
        return 0
    import math
    cf = COUNTRY_FACTOR.get(country, 0.03)

    if category_id and category_id != "overall":
        cat_f = CATEGORY_FACTOR.get(category_id, 0.10)
        # 游戏分类使用专用参数
        b = GAME_POWER_ALPHA if is_game else POWER_ALPHA
        base = (GAME_BASE if is_game else OVERALL_BASE) * cat_f
    else:
        b = GAME_POWER_ALPHA if is_game else POWER_ALPHA
        base = GAME_BASE if is_game else OVERALL_BASE

    daily = base * math.pow(rank, -b) * cf
    return int(max(1, daily * 30))


def estimate_monthly_revenue(monthly_downloads, price=None):
    """
    估算月收入。
    免费 App：ARPU $0.03-$0.10/下载
    付费 App：下载量 × 价格 × 0.7（苹果抽30%）
    """
    if not monthly_downloads or monthly_downloads <= 0:
        return 0, 0
    is_free = price is None or str(price).lower() in ("free", "get", "0", "0.00", "")
    if is_free:
        low = int(monthly_downloads * 0.03)
        high = int(monthly_downloads * 0.10)
    else:
        try:
            p = float(str(price).replace("$", "").replace("€", "").replace("£", ""))
        except ValueError:
            p = 0
        if p <= 0:
            low = int(monthly_downloads * 0.03)
            high = int(monthly_downloads * 0.10)
        else:
            low = int(monthly_downloads * p * 0.50)
            high = int(monthly_downloads * p * 0.80)
    return low, high


def calc_arpu_potential(cat_rank, overall_rank, rating_avg):
    """
    潜力 = 下载小但收入高 = 高ARPU
    畅销排名靠前说明能赚钱，总榜不入/低排名说明下载少
    评分低说明用户不満 = 需求未満足 = 有机会
    """
    if not cat_rank:
        return 0
    score = 0

    if cat_rank <= 3:
        score += 40
    elif cat_rank <= 10:
        score += 32
    elif cat_rank <= 20:
        score += 22
    elif cat_rank <= 30:
        score += 12
    else:
        score += 4

    if not overall_rank:
        score += 35
    elif overall_rank > 200:
        score += 30
    elif overall_rank > 100:
        score += 22
    elif overall_rank > 50:
        score += 12
    elif overall_rank > 20:
        score += 3
    else:
        score += 0

    if rating_avg and rating_avg < 3.0:
        score += 20
    elif rating_avg and rating_avg < 3.5:
        score += 12
    elif rating_avg and rating_avg < 4.0:
        score += 3

    return min(100, score)


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def api_overview(params):
    country = params.get("country", "us")
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    latest = c.execute("SELECT MAX(date) FROM app_daily_rank").fetchone()[0]
    if latest:
        today = latest

    cat_count = c.execute("SELECT COUNT(DISTINCT category_id) FROM app_daily_rank WHERE category_id != 'overall' AND date=? AND country=?", (today, country)).fetchone()[0]
    app_count = c.execute("SELECT COUNT(DISTINCT app_id) FROM app_daily_rank WHERE date=? AND country=?", (today, country)).fetchone()[0]
    detail_count = c.execute("SELECT COUNT(*) FROM app_details").fetchone()[0]
    quiet_count = c.execute("SELECT COUNT(*) FROM discovered_gems WHERE date=? AND country=? AND discovery_type='闷声型'", (today, country)).fetchone()[0]
    indie_count = c.execute("SELECT COUNT(*) FROM discovered_gems WHERE date=? AND country=? AND discovery_type='草根型'", (today, country)).fetchone()[0]
    low_rat_count = c.execute("""
        SELECT COUNT(*) FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        WHERE r.date=? AND r.country=? AND r.category_id != 'overall'
          AND r.rank_category <= 200
          AND d.rating_avg IS NOT NULL AND d.rating_avg > 0 AND d.rating_avg < 3.5
          AND d.rating_count >= 100
    """, (today, country)).fetchone()[0]

    countries = [dict(row) for row in c.execute("SELECT DISTINCT country FROM app_daily_rank WHERE date=?", (today,)).fetchall()]

    conn.close()

    return {
        "date": today,
        "country": country,
        "categories": cat_count,
        "apps": app_count,
        "details": detail_count,
        "quiet_count": quiet_count,
        "indie_count": indie_count,
        "low_rat_count": low_rat_count,
        "countries": [r["country"] for r in countries],
    }


def api_overall_top(params):
    country = params.get("country", "us")
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    rows = c.execute("""
        SELECT ct.rank, ct.app_id, d.app_name, d.developer_name,
               d.rating_count, d.rating_avg, d.price, d.genre, d.icon_url, ct.country
        FROM app_chart_type ct
        LEFT JOIN app_details d ON ct.app_id = d.app_id
        WHERE ct.category_id = 'overall'
          AND ct.chart_type = 'overall_topgrossing'
          AND ct.date = (SELECT MAX(date) FROM app_daily_rank)
          AND ct.country = ?
        ORDER BY ct.rank ASC LIMIT 50
    """, (country,)).fetchall()

    result = []
    for r in rows:
        dl = estimate_downloads(r["rank"], country)
        result.append({
            "rank": r["rank"], "app_id": r["app_id"],
            "app_name": r["app_name"], "developer_name": r["developer_name"],
            "rating_count": r["rating_count"], "rating_avg": r["rating_avg"],
            "price": r["price"], "genre": r["genre"], "icon_url": r["icon_url"],
            "est_downloads": dl,
            "est_revenue_low": round(dl * 0.03) if dl else 0,
            "est_revenue_high": round(dl * 0.10) if dl else 0,
            "country": r["country"],
        })
    conn.close()
    return result


def api_quiet_gems(params):
    country = params.get("country", "us")
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 100))
    offset = (page - 1) * per_page
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    rows = c.execute("""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               d.bundle_id,
               COALESCE(ct.rank, ctf.rank) as overall_rank,
               r.app_id, d.icon_url,
               d.release_date
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        LEFT JOIN app_chart_type ctf ON r.app_id = ctf.app_id
            AND r.country = ctf.country AND ctf.category_id = 'overall'
            AND ctf.chart_type = 'overall_topfree' AND ctf.date = ?
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 50
          AND (d.rating_count < 5000 OR d.rating_count IS NULL)
        ORDER BY r.rank_category ASC, d.rating_count ASC
        LIMIT ? OFFSET ?
    """, (today, today, today, country, per_page, offset)).fetchall()

    total = c.execute("""
        SELECT COUNT(*) FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 50
          AND (d.rating_count < 5000 OR d.rating_count IS NULL)
    """, (today, country)).fetchone()[0]

    result = []
    for r in rows:
        overall_rank = r["overall_rank"]
        cat_rank = r["rank_category"]
        if overall_rank:
            dl = estimate_downloads(overall_rank, country)
        else:
            dl = estimate_downloads(cat_rank, country, category_id=r["category_id"])
        pot = calc_arpu_potential(cat_rank, overall_rank, r["rating_avg"] if "rating_avg" in r.keys() else None)
        result.append({
            "country": r["country"], "category_id": r["category_id"],
            "category_name": r["category_name"], "app_id": r["app_id"],
            "app_name": r["app_name"], "developer_name": r["developer_name"],
            "rank_category": cat_rank, "overall_rank": overall_rank,
            "rating_count": r["rating_count"], "rating_avg": r["rating_avg"],
            "price": r["price"], "genre": r["genre"], "icon_url": r["icon_url"],
            "release_date": r["release_date"],
            "est_downloads": dl,
            "est_revenue_low": round(dl * 0.03) if dl else 0,
            "est_revenue_high": round(dl * 0.10) if dl else 0,
            "potential": pot,
        })
    conn.close()
    return {"total": total, "page": page, "per_page": per_page, "data": result}


def api_indie_gems(params):
    country = params.get("country", "us")
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 100))
    offset = (page - 1) * per_page
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    where_parts = " OR ".join([f"d.developer_name NOT LIKE ?" for _ in KNOWN_PUBLISHERS])
    rows = c.execute(f"""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               d.bundle_id,
               COALESCE(ct.rank, ctf.rank) as overall_rank,
               r.app_id, d.icon_url, d.release_date
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        LEFT JOIN app_chart_type ctf ON r.app_id = ctf.app_id
            AND r.country = ctf.country AND ctf.category_id = 'overall'
            AND ctf.chart_type = 'overall_topfree' AND ctf.date = ?
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 30
          AND ({where_parts} OR d.developer_name IS NULL)
        ORDER BY r.rank_category ASC
        LIMIT ? OFFSET ?
    """, (today, today, today, country, *[f"%{p}%" for p in KNOWN_PUBLISHERS], per_page, offset)).fetchall()

    total = c.execute(f"""
        SELECT COUNT(*) FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 30
          AND ({where_parts} OR d.developer_name IS NULL)
    """, (today, country, *[f"%{p}%" for p in KNOWN_PUBLISHERS])).fetchone()[0]

    result = []
    for r in rows:
        overall_rank = r["overall_rank"]
        cat_rank = r["rank_category"]
        if overall_rank:
            dl = estimate_downloads(overall_rank, country)
        else:
            dl = estimate_downloads(cat_rank, country, category_id=r["category_id"])
        pot = calc_arpu_potential(cat_rank, overall_rank, r["rating_avg"] if "rating_avg" in r.keys() else None)
        price = r["price"]
        if price and price not in ("Free", "Get", "0", "0.00"):
            rev_type = "付费+内购"
        elif r["rating_count"] and r["rating_count"] < 10000:
            rev_type = "高ARPU订阅"
        else:
            rev_type = "免费+内购/广告"
        result.append({
            "country": r["country"], "category_id": r["category_id"],
            "category_name": r["category_name"], "app_id": r["app_id"],
            "app_name": r["app_name"], "developer_name": r["developer_name"],
            "rank_category": cat_rank, "overall_rank": overall_rank,
            "rating_count": r["rating_count"], "rating_avg": r["rating_avg"],
            "price": price, "genre": r["genre"], "icon_url": r["icon_url"],
            "release_date": r["release_date"],
            "est_downloads": dl,
            "est_revenue_low": round(dl * 0.03) if dl else 0,
            "est_revenue_high": round(dl * 0.10) if dl else 0,
            "potential": pot, "rev_type": rev_type,
        })
    conn.close()
    return {"total": total, "page": page, "per_page": per_page, "data": result}


def api_low_rating(params):
    country = params.get("country", "us")
    category_id = params.get("category_id", "")
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 200))
    offset = (page - 1) * per_page
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    cat_filter = ""
    cat_params = []
    if category_id:
        cat_filter = "AND r.category_id = ?"
        cat_params = [category_id]

    rows = c.execute(f"""
        SELECT r.country, r.category_id, r.category_name, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg, d.price, d.genre,
               r.app_id,
               COALESCE(ct.rank, ctf.rank) as overall_rank,
               d.icon_url,
               d.release_date, d.current_version_rating, d.current_version_count
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        LEFT JOIN app_chart_type ctf ON r.app_id = ctf.app_id
            AND r.country = ctf.country AND ctf.category_id = 'overall'
            AND ctf.chart_type = 'overall_topfree' AND ctf.date = ?
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 200
          AND d.rating_avg IS NOT NULL AND d.rating_avg > 0 AND d.rating_avg < 4.0
          AND d.rating_count >= 50
          {cat_filter}
        ORDER BY r.rank_category ASC
        LIMIT ? OFFSET ?
    """, (today, today, today, country, *cat_params, per_page, offset)).fetchall()

    total = c.execute(f"""
        SELECT COUNT(*) FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        WHERE r.date = ? AND r.country = ? AND r.category_id != 'overall'
          AND r.rank_category <= 200
          AND d.rating_avg IS NOT NULL AND d.rating_avg > 0 AND d.rating_avg < 4.0
          AND d.rating_count >= 50
          {cat_filter}
    """, (today, country, *cat_params)).fetchone()[0]

    result = []
    for r in rows:
        overall_rank = r["overall_rank"]
        cat_rank = r["rank_category"]
        if overall_rank:
            dl = estimate_downloads(overall_rank, country)
        else:
            dl = estimate_downloads(cat_rank, country, category_id=r["category_id"])
        pot = calc_arpu_potential(cat_rank, overall_rank, float(r["rating_avg"]) if r["rating_avg"] else None)
        result.append({
            "country": r["country"], "category_id": r["category_id"],
            "category_name": r["category_name"], "app_id": r["app_id"],
            "app_name": r["app_name"], "developer_name": r["developer_name"],
            "rank_category": cat_rank, "overall_rank": overall_rank,
            "rating_count": r["rating_count"], "rating_avg": float(r["rating_avg"]) if r["rating_avg"] else None,
            "price": r["price"], "genre": r["genre"], "icon_url": r["icon_url"],
            "release_date": r["release_date"],
            "current_version_rating": r["current_version_rating"],
            "current_version_count": r["current_version_count"],
            "est_downloads": dl,
            "est_revenue_low": round(dl * 0.03) if dl else 0,
            "est_revenue_high": round(dl * 0.10) if dl else 0,
            "potential": pot,
        })
    conn.close()
    return {"total": total, "page": page, "per_page": per_page, "data": result}


def api_categories(params):
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    result = []
    for cat_id, cat_name in CATEGORIES.items():
        cnt = c.execute("SELECT COUNT(*) FROM app_daily_rank WHERE date=? AND category_id=? AND category_id != 'overall'", (today, cat_id)).fetchone()[0]
        result.append({"id": cat_id, "name": cat_name, "count": cnt})
    conn.close()
    return result


def api_category_top(params):
    category_id = params.get("category_id", "6003")
    country = params.get("country", "us")
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()

    rows = c.execute("""
        SELECT r.rank_category, r.app_id, r.app_name, r.developer_name,
               d.rating_count, d.rating_avg, d.price, d.genre, d.icon_url,
               COALESCE(ct.rank, ctf.rank) as overall_rank
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing' AND ct.date = ?
        LEFT JOIN app_chart_type ctf ON r.app_id = ctf.app_id
            AND r.country = ctf.country AND ctf.category_id = 'overall'
            AND ctf.chart_type = 'overall_topfree' AND ctf.date = ?
        WHERE r.date = ? AND r.country = ? AND r.category_id = ?
        ORDER BY r.rank_category ASC
        LIMIT 20
    """, (today, today, today, country, category_id)).fetchall()

    result = []
    for r in rows:
        if r["overall_rank"]:
            dl = estimate_downloads(r["overall_rank"], country)
        else:
            dl = estimate_downloads(r["rank_category"], country, category_id=category_id)
        result.append({
            "rank": r["rank_category"], "app_id": r["app_id"],
            "app_name": r["app_name"], "developer_name": r["developer_name"],
            "rating_count": r["rating_count"], "rating_avg": r["rating_avg"],
            "price": r["price"], "genre": r["genre"], "icon_url": r["icon_url"],
            "overall_rank": r["overall_rank"],
            "est_downloads": dl,
            "potential": calc_arpu_potential(r["rank_category"], r["overall_rank"], float(r["rating_avg"]) if r["rating_avg"] else None),
        })
    conn.close()
    return result


# ==================== Google Play API ====================

def api_gp_new_apps(params):
    country = params.get("country", "us")
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 50))
    offset = (page - 1) * per_page
    conn = sqlite3.connect(GP_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    total = c.execute(
        "SELECT COUNT(*) FROM gp_seen_apps WHERE country = ?",
        (country,)
    ).fetchone()[0]

    rows = c.execute("""
        SELECT s.app_id, s.first_seen_date, d.title, d.developer,
               d.genre, d.score, d.installs, d.price, d.free,
               d.icon_url, d.url
        FROM gp_seen_apps s
        LEFT JOIN gp_app_details d ON s.app_id = d.app_id
        WHERE s.country = ?
        ORDER BY s.first_seen_date DESC, s.app_id ASC
        LIMIT ? OFFSET ?
    """, (country, per_page, offset)).fetchall()

    data = [{
        "app_id": r["app_id"], "first_seen_date": r["first_seen_date"],
        "title": r["title"] or r["app_id"],
        "developer": r["developer"] or "",
        "genre": r["genre"] or "",
        "score": r["score"],
        "installs": r["installs"] or "",
        "price": r["price"],
        "free": bool(r["free"]),
        "icon_url": r["icon_url"] or "",
        "url": r["url"] or f"https://play.google.com/store/apps/details?id={r['app_id']}",
    } for r in rows]

    conn.close()
    return {"total": total, "page": page, "per_page": per_page, "data": data}


def api_gp_top_free(params):
    country = params.get("country", "us")
    conn = sqlite3.connect(GP_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    today = date.today().isoformat()

    latest_date = c.execute(
        "SELECT MAX(date) FROM gp_daily_index WHERE country = ?",
        (country,)
    ).fetchone()[0] or today

    rows = c.execute("""
        SELECT d.app_id, d.title, d.rank, c.category_id,
               det.developer, det.genre, det.score, det.installs,
               det.price, det.free, det.icon_url
        FROM gp_daily_index d
        LEFT JOIN gp_app_details det ON d.app_id = det.app_id
        LEFT JOIN (SELECT DISTINCT app_id, category_id FROM gp_daily_index
                    WHERE date = ? AND country = ?) c ON d.app_id = c.app_id
        WHERE d.date = ? AND d.country = ? AND d.collection = 'TOP_FREE'
        ORDER BY d.rank ASC LIMIT 100
    """, (latest_date, country, latest_date, country)).fetchall()

    data = [{
        "rank": r["rank"], "app_id": r["app_id"],
        "title": r["title"] or r["app_id"],
        "category_id": r["category_id"] or "",
        "developer": r["developer"] or "",
        "genre": r["genre"] or "",
        "score": r["score"],
        "installs": r["installs"] or "",
        "price": r["price"],
        "free": bool(r["free"]),
        "icon_url": r["icon_url"] or "",
    } for r in rows]

    conn.close()
    return data


API_ROUTES = {
    "/api/overview": api_overview,
    "/api/overall_top": api_overall_top,
    "/api/quiet_gems": api_quiet_gems,
    "/api/indie_gems": api_indie_gems,
    "/api/low_rating": api_low_rating,
    "/api/categories": api_categories,
    "/api/category_top": api_category_top,
    # Google Play API
    "/api/gp/new_apps": api_gp_new_apps,
    "/api/gp/top_free": api_gp_top_free,
}


class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if path in API_ROUTES:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = API_ROUTES[path](params)
                self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
        elif path == "/" or path == "/index.html":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="iOS 细分畅销榜情报 Web 服务")
    parser.add_argument("-p", "--port", type=int, default=8500, help="端口号，默认 8500")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    args = parser.parse_args()

    print(f"🚀 iOS 细分畅销榜情报服务启动")
    print(f"   数据库: {DB_PATH}")
    print(f"   访问地址: http://localhost:{args.port}")
    print(f"   按 Ctrl+C 停止")

    server = http.server.HTTPServer((args.host, args.port), APIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()