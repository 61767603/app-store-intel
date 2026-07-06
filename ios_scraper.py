#!/usr/bin/env python3
"""
iOS App Store 细分畅销榜情报采集器（仅 iPhone）
====================================================
抓取指定国家+分类的畅销榜 Top 100 + 免费榜 + 付费榜 + 总榜排名，
入库追踪排名变化，自动发现"闷声发财"的异常应用。

注意：仅采集 iPhone 应用数据，过滤掉 iPad-only 应用。
    iTunes RSS Feed 默认返回 iPhone + iPad 应用，
    Lookup API 返回结果中通过 wrapperType=software 过滤。

数据源：
  - iTunes RSS Feed（榜单排名，仅 iPhone 应用榜单）
  - iTunes Lookup API（补全评价数、评分、开发商等详情）

使用方式：
  python ios_scraper.py              # 全量抓取（默认美国+全部分类）
  python ios_scraper.py --analyze     # 只做分析
  python ios_scraper.py --full        # 抓取 + 分析
  python ios_scraper.py --export      # 导出 CSV
  python ios_scraper.py --countries us,jp --categories 6003,6007
"""

import requests
import sqlite3
import json
import time
import datetime
import argparse
import random
import sys
import os
import io
import csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)

import builtins
_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _print(*args, **kwargs)
builtins.print = print

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_intel.db")

# ================= 默认美国 =================
COUNTRIES = {
    "us": "美国", "jp": "日本", "gb": "英国", "de": "德国",
    "kr": "韩国", "sa": "沙特", "au": "澳洲", "ca": "加拿大",
    "fr": "法国", "br": "巴西", "tr": "土耳其", "id": "印尼",
}

# ================= 已验证的有效分类（22个） =================
CATEGORIES = {
    "6000": "商业", "6001": "天气", "6002": "工具", "6003": "教育",
    "6004": "社交", "6005": "娱乐", "6006": "财务", "6007": "健康健美",
    "6008": "音乐", "6009": "医疗", "6010": "导航", "6011": "新闻",
    "6012": "摄影与录像", "6013": "效率", "6014": "参考", "6015": "购物",
    "6016": "生活方式", "6017": "体育", "6018": "旅行",
    "6020": "图书", "6021": "美食佳饮", "6023": "杂志报纸",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-us",
})
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

CHART_NAMES = {
    "topgrossing": "topgrossingapplications",
    "topfree": "topfreeapplications",
    "toppaid": "toppaidapplications",
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 分类榜单排名（畅销榜为主表 + 各榜单排名单独存）
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_daily_rank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            country TEXT NOT NULL,
            category_id TEXT NOT NULL,
            category_name TEXT,
            app_id TEXT NOT NULL,
            app_name TEXT,
            developer_name TEXT,
            bundle_id TEXT,
            rank_category INTEGER,
            price TEXT,
            UNIQUE(date, country, category_id, app_id)
        )
    """)

    # 各榜单排名（总榜畅销/免费/付费 + 分类榜免费/付费）
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_chart_type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            country TEXT NOT NULL,
            category_id TEXT NOT NULL,
            app_id TEXT NOT NULL,
            chart_type TEXT NOT NULL,
            rank INTEGER,
            UNIQUE(date, country, category_id, app_id, chart_type)
        )
    """)

    # 应用详情
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_details (
            app_id TEXT PRIMARY KEY,
            app_name TEXT,
            developer_name TEXT,
            bundle_id TEXT,
            price TEXT,
            currency TEXT,
            rating_avg REAL,
            rating_count INTEGER,
            current_version_rating REAL,
            current_version_count INTEGER,
            genre TEXT,
            icon_url TEXT,
            release_date TEXT,
            updated_date TEXT,
            filesize TEXT,
            minimum_os TEXT,
            languages TEXT,
            last_updated TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS discovered_gems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            country TEXT NOT NULL,
            category_id TEXT,
            category_name TEXT,
            app_id TEXT NOT NULL,
            app_name TEXT,
            developer_name TEXT,
            rating_count INTEGER,
            rank_category INTEGER,
            rank_overall INTEGER,
            estimated_revenue_usd TEXT,
            discovery_type TEXT,
            notes TEXT,
            UNIQUE(date, country, app_id, discovery_type)
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_rank_date ON app_daily_rank(date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rank_country ON app_daily_rank(country)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rank_cat ON app_daily_rank(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rank_appid ON app_daily_rank(app_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_detail_appid ON app_details(app_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chart_appid ON app_chart_type(app_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chart_type ON app_chart_type(chart_type)")
    conn.commit()
    conn.close()


def fetch_rss_top_chart(country, category_id=None, chart_type="topgrossing", limit=200):
    """
    抓取 iTunes RSS 榜单数据（仅 iPhone 应用）。
    category_id=None 时抓总榜。
    注意: RSS Feed 返回 iPhone + 通用应用混合榜单，iPad-only 应用在 Lookup 阶段过滤。
    """
    chart_slug = CHART_NAMES.get(chart_type, "topgrossingapplications")
    if category_id:
        url = f"https://itunes.apple.com/{country}/rss/{chart_slug}/limit={limit}/genre={category_id}/json"
    else:
        url = f"https://itunes.apple.com/{country}/rss/{chart_slug}/limit={limit}/json"

    label = f"{country}/{category_id or 'overall'}"

    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"  [RSS] {label} HTTP {resp.status_code}, retry {attempt+1}")
                time.sleep(2 * (attempt + 1))
                continue

            data = resp.json()
            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                print(f"  [RSS] {label} 无数据")
                return []

            results = []
            for idx, entry in enumerate(entries, 1):
                app_id = entry.get("id", {}).get("attributes", {}).get("im:id", "")
                app_name = entry.get("im:name", {}).get("label", "")
                developer_name = entry.get("im:artist", {}).get("label", "")
                bundle_id = entry.get("id", {}).get("attributes", {}).get("im:bundleId", "")

                price_info = entry.get("im:price", {})
                if price_info and isinstance(price_info, dict):
                    price_label = price_info.get("label", "Free")
                    price_amount = price_info.get("attributes", {}).get("amount", "0.00")
                    price = f"${price_amount}" if price_amount and price_amount != "0.00" else price_label
                else:
                    price = "Free"

                if app_id:
                    results.append({
                        "rank": idx,
                        "app_id": app_id,
                        "app_name": app_name,
                        "developer_name": developer_name,
                        "bundle_id": bundle_id,
                        "price": price,
                        "icon_url": entry.get("im:image", [{}])[-1].get("label", "") if entry.get("im:image") else "",
                    })

            print(f"  [RSS] {label}/{chart_type} -> {len(results)} 条")
            return results

        except Exception as e:
            print(f"  [RSS] {label} 异常: {e}, retry {attempt+1}")
            time.sleep(3 * (attempt + 1))

    print(f"  [RSS] {label} 全部重试失败")
    return []


def fetch_batch_app_details(app_ids):
    """批量查询应用详情（每次最多100个）"""
    all_details = {}
    for i in range(0, len(app_ids), 100):
        batch = app_ids[i:i+100]
        ids_str = ",".join(batch)
        url = "https://itunes.apple.com/lookup"
        params = {"id": ids_str}

        for attempt in range(MAX_RETRIES):
            try:
                resp = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    time.sleep(2)
                    continue
                data = resp.json()
                for app in data.get("results", []):
                    if app.get("wrapperType") == "software" and app.get("kind") != "mac-software":
                        device_compat = app.get("supportedDevices", [])
                        is_ipad_only = False
                        if isinstance(device_compat, list) and len(device_compat) > 0:
                            has_iphone = any("iphone" in str(d).lower() or "ipod" in str(d).lower() for d in device_compat)
                            has_ipad = any("ipad" in str(d).lower() for d in device_compat)
                            if has_ipad and not has_iphone:
                                is_ipad_only = True
                        if is_ipad_only:
                            continue
                        aid = str(app.get("trackId", ""))
                        all_details[aid] = {
                            "app_id": aid,
                            "app_name": app.get("trackName", ""),
                            "developer_name": app.get("artistName", ""),
                            "bundle_id": app.get("bundleId", ""),
                            "price": str(app.get("price", 0)) if app.get("price") is not None else "0",
                            "currency": app.get("currency", ""),
                            "rating_avg": app.get("averageUserRating", 0),
                            "rating_count": app.get("userRatingCount", 0),
                            "current_version_rating": app.get("averageUserRatingForCurrentVersion", 0),
                            "current_version_count": app.get("userRatingCountForCurrentVersion", 0),
                            "genre": app.get("primaryGenreName", ""),
                            "icon_url": app.get("artworkUrl512", app.get("artworkUrl100", "")),
                            "release_date": app.get("releaseDate", ""),
                            "updated_date": app.get("currentVersionReleaseDate", ""),
                            "filesize": app.get("fileSizeBytes", ""),
                            "minimum_os": app.get("minimumOsVersion", ""),
                            "languages": ",".join(app.get("languageCodesISO2A", [])),
                        }
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"  [BatchLookup] 异常: {e}")
                time.sleep(2)

        time.sleep(0.5)

    return all_details


def save_ranks_to_db(date_str, country, category_id, category_name, apps):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    saved = 0
    for app in apps:
        try:
            c.execute("""
                INSERT OR REPLACE INTO app_daily_rank
                (date, country, category_id, category_name, app_id, app_name,
                 developer_name, bundle_id, rank_category, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str, country, category_id, category_name,
                app["app_id"], app["app_name"], app.get("developer_name", ""),
                app.get("bundle_id", ""), app["rank"], app.get("price", ""),
            ))
            saved += 1
        except Exception as e:
            print(f"  [DB] 保存失败 app_id={app.get('app_id')}: {e}")
    conn.commit()
    conn.close()
    return saved


def save_chart_ranks(date_str, country, category_id, chart_type, apps):
    """保存各榜单（总榜/免费榜/付费榜）排名"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for app in apps:
        try:
            c.execute("""
                INSERT OR REPLACE INTO app_chart_type
                (date, country, category_id, app_id, chart_type, rank)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date_str, country, category_id, app["app_id"], chart_type, app["rank"]))
        except Exception:
            pass
    conn.commit()
    conn.close()


def save_details_to_db(details_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    saved = 0
    for d in details_list:
        if not d:
            continue
        try:
            c.execute("""
                INSERT OR REPLACE INTO app_details
                (app_id, app_name, developer_name, bundle_id, price, currency,
                 rating_avg, rating_count, current_version_rating, current_version_count,
                 genre, icon_url, release_date, updated_date, filesize, minimum_os, languages, last_updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?, ?)
            """, (
                d["app_id"], d["app_name"], d["developer_name"], d["bundle_id"],
                d["price"], d["currency"], d["rating_avg"], d["rating_count"],
                d["current_version_rating"], d["current_version_count"],
                d["genre"], d.get("icon_url", ""), d["release_date"], d["updated_date"], d["filesize"],
                d["minimum_os"], d["languages"],
                datetime.date.today().isoformat(),
            ))
            saved += 1
        except Exception as e:
            print(f"  [DB] 保存详情失败: {e}")
    conn.commit()
    conn.close()
    return saved


def scrape_country(country, categories=None):
    """抓取单个国家的总榜 + 所有分类的畅销榜/免费榜/付费榜"""
    categories = categories or CATEGORIES
    date_str = datetime.date.today().isoformat()
    all_app_ids = set()

    # ==================== 1. 总榜（无分类） ====================
    print(f"\n{'='*60}")
    print(f"📡 抓取 {COUNTRIES.get(country, country)}({country}) 总榜")
    print(f"{'='*60}")

    for chart_type, chart_label in [("topgrossing", "畅销总榜"), ("topfree", "免费总榜"), ("toppaid", "付费总榜")]:
        apps = fetch_rss_top_chart(country, category_id=None, chart_type=chart_type)
        if apps:
            save_chart_ranks(date_str, country, "overall", f"overall_{chart_type}", apps)
            for app in apps:
                all_app_ids.add(app["app_id"])
        print(f"    {chart_label}: {len(apps)} 条")
        time.sleep(random.uniform(0.3, 0.8))

    # ==================== 2. 分类榜单 ====================
    total_cats = len(categories)
    for idx, (cat_id, cat_name) in enumerate(categories.items(), 1):
        print(f"\n  [{idx}/{total_cats}] {cat_name}({cat_id})")
        # 畅销榜 -> 存到主表
        grossing = fetch_rss_top_chart(country, category_id=cat_id, chart_type="topgrossing")
        if grossing:
            save_ranks_to_db(date_str, country, cat_id, cat_name, grossing)
            for app in grossing:
                all_app_ids.add(app["app_id"])
            save_chart_ranks(date_str, country, cat_id, "cat_grossing", grossing)
        time.sleep(random.uniform(0.3, 0.8))

        # 分类免费榜 + 付费榜
        free = fetch_rss_top_chart(country, category_id=cat_id, chart_type="topfree")
        if free:
            for app in free:
                all_app_ids.add(app["app_id"])
            save_chart_ranks(date_str, country, cat_id, "cat_free", free)
        time.sleep(random.uniform(0.3, 0.6))

        paid = fetch_rss_top_chart(country, category_id=cat_id, chart_type="toppaid")
        if paid:
            for app in paid:
                all_app_ids.add(app["app_id"])
            save_chart_ranks(date_str, country, cat_id, "cat_paid", paid)
        time.sleep(random.uniform(0.3, 0.6))

    return all_app_ids


def scrape_all(countries=None, categories=None):
    """全量抓取"""
    countries = countries or ["us"]
    categories = categories or CATEGORIES

    today = datetime.date.today().isoformat()
    all_app_ids = set()

    print(f"\n🚀 开始抓取 | 日期: {today} | 国家: {','.join(countries)} | 分类: {len(categories)}")
    print(f"    总任务: 总榜6条 + 分类{len(categories)}×3 = {6 + len(categories)*3} 条/国家")

    for country in countries:
        ids = scrape_country(country, categories)
        all_app_ids.update(ids)

    print(f"\n📊 抓取完成，共 {len(all_app_ids)} 个唯一应用，开始补全详情...")

    # 批量补全应用详情
    app_id_list = list(all_app_ids)
    details_list = []
    for i in range(0, len(app_id_list), 100):
        batch = app_id_list[i:i+100]
        print(f"  [详情] 批次 {i//100 + 1}/{(len(app_id_list)-1)//100 + 1} ({len(batch)} 个)")
        details = fetch_batch_app_details(batch)
        details_list.extend(details.values())
        time.sleep(random.uniform(1, 3))

    saved_details = save_details_to_db(details_list)
    print(f"\n✅ 详情补全完成，保存 {saved_details} 条")
    return len(all_app_ids)


def discover_gems():
    """发现异常应用：闷声型 / 火箭型 / 草根型"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    discovered = []

    # ==================== 1. 闷声型：分类畅销 Top50 + 评价 < 5000 ====================
    print("\n🔍 闷声型：分类畅销 Top50 + 评价 < 5000")
    print("-" * 60)

    # 查出每个app在总榜的排名
    c.execute("""
        SELECT r.date, r.country, r.category_id, r.category_name,
               r.app_id, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.rating_avg,
               d.price, d.genre, d.bundle_id,
               ct_overall.rank AS rank_overall
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct_overall ON r.app_id = ct_overall.app_id
            AND r.country = ct_overall.country
            AND ct_overall.category_id = 'overall'
            AND ct_overall.chart_type = 'overall_topgrossing'
            AND ct_overall.date = ?
        WHERE r.date = ?
          AND r.category_id != 'overall'
          AND r.rank_category <= 50
          AND (d.rating_count < 5000 OR d.rating_count IS NULL)
        ORDER BY r.rank_category ASC
    """, (today, today))

    quiet_gems = c.fetchall()
    for row in quiet_gems:
        rating_count = row[8] if row[8] else 0
        rating_avg = row[9] if row[9] else 0
        rank_overall = row[13] if row[13] else None
        est_downloads = rating_count * 80 if rating_count else 0
        estimated_revenue = f"${est_downloads * 0.03:.0f}-${est_downloads * 0.1:.0f}/月" if rating_count else "N/A"

        discovered.append({
            "date": row[0], "country": row[1], "category_id": row[2],
            "category_name": row[3], "app_id": row[4], "app_name": row[5],
            "developer_name": row[6], "rating_count": rating_count,
            "rank_category": row[7], "rank_overall": rank_overall,
            "estimated_revenue_usd": estimated_revenue,
            "discovery_type": "闷声型",
            "notes": f"分类#{row[7]}" + (f",总榜#{rank_overall}" if rank_overall else "") + f",评价{rating_count},评分{float(rating_avg):.1f}",
        })

    print(f"  发现 {len(quiet_gems)} 个闷声型应用")

    # ==================== 2. 火箭型：7天内排名飙升 ====================
    print("\n🔍 火箭型：7天内从 >50 外飙升至 Top20")
    print("-" * 60)

    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

    c.execute("""
        SELECT r1.date, r1.country, r1.category_id, r1.category_name,
               r1.app_id, r1.app_name, r1.developer_name,
               r1.rank_category AS rank_now,
               r2.rank_category AS rank_then,
               d.rating_count, d.rating_avg,
               ct.rank AS rank_overall
        FROM app_daily_rank r1
        JOIN app_daily_rank r2 ON r1.app_id = r2.app_id
            AND r1.country = r2.country
            AND r1.category_id = r2.category_id
            AND r2.date = ?
        LEFT JOIN app_details d ON r1.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r1.app_id = ct.app_id
            AND r1.country = ct.country
            AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing'
            AND ct.date = ?
        WHERE r1.date = ?
          AND r1.category_id != 'overall'
          AND r1.rank_category <= 20
          AND r2.rank_category > 50
        ORDER BY (r2.rank_category - r1.rank_category) DESC
    """, (week_ago, today, today))

    rocket_gems = c.fetchall()
    for row in rocket_gems:
        rank_now = row[7]
        rank_then = row[8]
        rating_count = row[10] if row[10] else 0
        rank_overall = row[12] if row[12] else None
        boost = rank_then - rank_now

        discovered.append({
            "date": row[0], "country": row[1], "category_id": row[2],
            "category_name": row[3], "app_id": row[4], "app_name": row[5],
            "developer_name": row[6], "rating_count": rating_count,
            "rank_category": rank_now, "rank_overall": rank_overall,
            "estimated_revenue_usd": "",
            "discovery_type": "火箭型",
            "notes": f"7天从#{rank_then}飙升至#{rank_now}(+{boost}),评价{rating_count}" + (f",总榜#{rank_overall}" if rank_overall else ""),
        })

    print(f"  发现 {len(rocket_gems)} 个火箭型应用")

    # ==================== 3. 草根型：非大厂 + 分类 Top30 ====================
    print("\n🔍 草根型：非大厂 + 分类 Top30")
    print("-" * 60)

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

    where_parts = " OR ".join([f"d.developer_name NOT LIKE ?" for _ in KNOWN_PUBLISHERS])
    c.execute(f"""
        SELECT r.date, r.country, r.category_id, r.category_name,
               r.app_id, r.app_name, r.developer_name,
               r.rank_category, d.rating_count, d.price, d.genre,
               ct.rank AS rank_overall
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct ON r.app_id = ct.app_id
            AND r.country = ct.country
            AND ct.category_id = 'overall'
            AND ct.chart_type = 'overall_topgrossing'
            AND ct.date = ?
        WHERE r.date = ?
          AND r.category_id != 'overall'
          AND r.rank_category <= 30
          AND ({where_parts} OR d.developer_name IS NULL)
        ORDER BY r.rank_category ASC
    """, (today, today, *[f"%{p}%" for p in KNOWN_PUBLISHERS]))

    indie_gems = c.fetchall()
    for row in indie_gems:
        rating_count = row[8] if row[8] else 0
        price = row[9] if row[9] else "Free"
        rank_overall = row[11] if row[11] else None
        revenue_note = ""
        if price and price not in ("Free", "Get", "0"):
            revenue_note = f"付费{price}+内购"
        elif rating_count and rating_count < 10000:
            revenue_note = "少评高价排名->高ARPU订阅"
        else:
            revenue_note = "免费+内购/广告"

        discovered.append({
            "date": row[0], "country": row[1], "category_id": row[2],
            "category_name": row[3], "app_id": row[4], "app_name": row[5],
            "developer_name": row[6], "rating_count": rating_count,
            "rank_category": row[7], "rank_overall": rank_overall,
            "estimated_revenue_usd": "",
            "discovery_type": "草根型",
            "notes": f"分类#{row[7]}" + (f",总榜#{rank_overall}" if rank_overall else "") + f",{row[6]},{revenue_note}",
        })

    print(f"  发现 {len(indie_gems)} 个草根型应用")

    # ==================== 入库 ====================
    for gem in discovered:
        try:
            c.execute("""
                INSERT OR REPLACE INTO discovered_gems
                (date, country, category_id, category_name, app_id, app_name,
                 developer_name, rating_count, rank_category, rank_overall,
                 estimated_revenue_usd, discovery_type, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                gem["date"], gem["country"], gem["category_id"], gem["category_name"],
                gem["app_id"], gem["app_name"], gem["developer_name"],
                gem["rating_count"], gem["rank_category"], gem["rank_overall"],
                gem["estimated_revenue_usd"], gem["discovery_type"], gem["notes"],
            ))
        except Exception as e:
            print(f"  写入失败: {e}")

    conn.commit()
    conn.close()

    print(f"\n{'='*70}")
    print(f"💎 发现报告 | {today}")
    print(f"{'='*70}")
    print(f"  闷声型: {len(quiet_gems)} 个")
    print(f"  火箭型: {len(rocket_gems)} 个")
    print(f"  草根型: {len(indie_gems)} 个")
    print(f"  合计:   {len(discovered)} 条情报")
    print(f"{'='*70}")

    return discovered


def export_to_csv():
    """导出 CSV"""
    conn = sqlite3.connect(DB_PATH)
    today = datetime.date.today().isoformat()
    output_dir = os.path.dirname(os.path.abspath(__file__))

    # 排名数据（含总榜排名）
    df_rank = conn.execute("""
        SELECT r.date, r.country, r.category_name, r.app_name, r.developer_name,
               r.rank_category AS rank_grossing,
               ct_free.rank AS rank_cat_free,
               ct_paid.rank AS rank_cat_paid,
               ct_overall.rank AS rank_overall_grossing,
               d.rating_count, d.rating_avg,
               d.price, d.genre, d.bundle_id
        FROM app_daily_rank r
        LEFT JOIN app_details d ON r.app_id = d.app_id
        LEFT JOIN app_chart_type ct_free ON r.app_id = ct_free.app_id
            AND r.country = ct_free.country AND r.category_id = ct_free.category_id
            AND r.date = ct_free.date AND ct_free.chart_type = 'cat_free'
        LEFT JOIN app_chart_type ct_paid ON r.app_id = ct_paid.app_id
            AND r.country = ct_paid.country AND r.category_id = ct_paid.category_id
            AND r.date = ct_paid.date AND ct_paid.chart_type = 'cat_paid'
        LEFT JOIN app_chart_type ct_overall ON r.app_id = ct_overall.app_id
            AND r.country = ct_overall.country AND ct_overall.category_id = 'overall'
            AND r.date = ct_overall.date AND ct_overall.chart_type = 'overall_topgrossing'
        WHERE r.date = ?
          AND r.category_id != 'overall'
        ORDER BY r.country, r.category_id, r.rank_category
    """, (today,)).fetchall()

    rank_file = os.path.join(output_dir, f"rank_{today}_v2.csv")
    with open(rank_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "国家", "分类", "应用名", "开发商",
                         "分类畅销榜排名", "分类免费榜排名", "分类付费榜排名", "总榜畅销排名",
                         "评价数", "评分", "价格", "类型", "Bundle ID"])
        writer.writerows(df_rank)

    # 发现报告
    df_gems = conn.execute("""
        SELECT date, country, category_name, app_name, developer_name,
               rank_category, rank_overall, rating_count,
               discovery_type, estimated_revenue_usd, notes
        FROM discovered_gems
        WHERE date = ?
        ORDER BY discovery_type, rank_category
    """, (today,)).fetchall()

    gems_file = os.path.join(output_dir, f"gems_{today}_v2.csv")
    with open(gems_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "国家", "分类", "应用名", "开发商",
                         "分类排名", "总榜排名", "评价数", "发现类型", "估价", "备注"])
        writer.writerows(df_gems)

    conn.close()
    print(f"\n📄 已导出:")
    print(f"  排名数据: {rank_file} ({len(df_rank)} 行)")
    print(f"  发现报告: {gems_file} ({len(df_gems)} 行)")


def show_top_gems(limit=20):
    """打印最有价值的发现"""
    conn = sqlite3.connect(DB_PATH)
    today = datetime.date.today().isoformat()

    c = conn.cursor()
    c.execute("""
        SELECT country, category_name, app_name, developer_name,
               rank_category, rank_overall, rating_count, discovery_type, notes
        FROM discovered_gems
        WHERE date = ?
        ORDER BY rank_category ASC
        LIMIT ?
    """, (today, limit))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print("暂无发现数据，请先运行 --full 或 --scrape + --analyze")
        return

    print(f"\n💎 Top {limit} 异常应用发现 | {today}")
    print("=" * 110)
    print(f"{'#':<3} {'国家':<6} {'分类':<10} {'应用名':<30} {'开发商':<22} {'分类#':<6} {'总榜#':<7} {'评价':<8} {'类型'}")
    print("-" * 110)

    for i, row in enumerate(rows, 1):
        country = COUNTRIES.get(row[0], row[0])
        app_name = (row[2] or "")[:28]
        dev_name = (row[3] or "")[:20]
        rank_cat = row[4] or "-"
        rank_overall = str(row[5]) if row[5] else "-"
        rating = str(row[6]) if row[6] else "N/A"
        dtype = row[7] or ""
        print(f"{i:<3} {country:<6} {row[1]:<10} {app_name:<30} {dev_name:<22} {rank_cat:<6} {rank_overall:<7} {rating:<8} {dtype}")


def get_scraping_stats():
    """数据库统计"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(DISTINCT date) FROM app_daily_rank")
    dates = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT app_id) FROM app_daily_rank")
    apps = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT country) FROM app_daily_rank")
    countries = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT category_id) FROM app_daily_rank WHERE category_id != 'overall'")
    cats = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM app_details")
    details = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM app_chart_type")
    charts = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM discovered_gems")
    gems = c.fetchone()[0]
    c.execute("SELECT DISTINCT date FROM app_daily_rank ORDER BY date DESC LIMIT 5")
    date_list = c.fetchall()

    conn.close()

    print(f"\n📊 数据库统计")
    print("=" * 50)
    print(f"  采集天数:     {dates}")
    print(f"  唯一应用数:   {apps}")
    print(f"  覆盖国家:     {countries}")
    print(f"  分类数:       {cats}")
    print(f"  详情条数:     {details}")
    print(f"  榜单记录:     {charts}")
    print(f"  发现条数:     {gems}")
    print(f"  最近日期:     {', '.join([d[0] for d in date_list])}")


def main():
    parser = argparse.ArgumentParser(description="iOS App Store 细分畅销榜情报采集器")
    parser.add_argument("--scrape", action="store_true", help="只抓取数据")
    parser.add_argument("--analyze", action="store_true", help="只做分析")
    parser.add_argument("--full", action="store_true", help="抓取 + 分析（默认）")
    parser.add_argument("--export", action="store_true", help="导出 CSV")
    parser.add_argument("--stats", action="store_true", help="数据库统计")
    parser.add_argument("--top", type=int, default=20, help="显示 Top N")
    parser.add_argument("--countries", type=str, default="us", help="国家，逗号分隔，默认us")
    parser.add_argument("--categories", type=str, default=None, help="分类ID，逗号分隔，如6000,6003")
    parser.add_argument("--skip-details", action="store_true", help="跳过详情补全")

    args = parser.parse_args()

    if not any([args.scrape, args.analyze, args.full, args.export, args.stats]):
        args.full = True

    # 处理旧数据库：增删字段
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("ALTER TABLE discovered_gems ADD COLUMN rank_overall INTEGER")
        try:
            c.execute("ALTER TABLE app_details ADD COLUMN icon_url TEXT")
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception:
        pass

    if args.stats:
        get_scraping_stats()
        return

    countries = args.countries.split(",") if args.countries else ["us"]
    categories = None
    if args.categories:
        cat_ids = args.categories.split(",")
        categories = {k: v for k, v in CATEGORIES.items() if k in cat_ids}

    if args.scrape or args.full:
        total = scrape_all(countries=countries, categories=categories)
        print(f"\n🎉 抓取完成！共 {total} 个应用")

    if args.analyze or args.full:
        gems = discover_gems()
        show_top_gems(limit=args.top)

    if args.export:
        export_to_csv()


if __name__ == "__main__":
    main()