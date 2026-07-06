#!/usr/bin/env python3
"""
Google Play 榜单采集器
========================
每天拉 TOP_FREE 榜单索引，对比"已见"表发现新冲榜 App，
仅对新 App 补全详情。支持多国家、多分类。

用法:
  python3 gp_scraper.py                          # 默认 us,jp,de + 全分类
  python3 gp_scraper.py --countries us,jp --categories GAME_SOCIAL,PRODUCTIVITY
  python3 gp_scraper.py --collection TOP_FREE     # 默认 TOP_FREE
"""

import sys
import os
import sqlite3
import time
import random
import argparse
from datetime import date

from gplay_scraper import GPlayScraper

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gp_intel.db")

# Google Play 分类 ID 映射 (非游戏 36 个)
GP_CATEGORIES = {
    "APPLICATION":          "应用(综合)",
    "ANDROID_WEAR":         "Android Wear",
    "ART_AND_DESIGN":       "艺术与设计",
    "AUTO_AND_VEHICLES":    "汽车与车辆",
    "BEAUTY":               "美容",
    "BOOKS_AND_REFERENCE":  "图书与参考",
    "BUSINESS":             "商业",
    "COMICS":               "漫画",
    "COMMUNICATION":        "通讯",
    "DATING":               "约会",
    "EDUCATION":            "教育",
    "ENTERTAINMENT":        "娱乐",
    "EVENTS":               "活动",
    "FINANCE":              "财务",
    "FOOD_AND_DRINK":       "美食佳饮",
    "HEALTH_AND_FITNESS":   "健康与健身",
    "HOUSE_AND_HOME":       "家居",
    "LIBRARIES_AND_DEMO":   "库与演示",
    "LIFESTYLE":            "生活方式",
    "MAPS_AND_NAVIGATION":  "地图与导航",
    "MEDICAL":              "医疗",
    "MUSIC_AND_AUDIO":      "音乐与音频",
    "NEWS_AND_MAGAZINES":   "新闻与杂志",
    "PARENTING":            "育儿",
    "PERSONALIZATION":      "个性化",
    "PHOTOGRAPHY":          "摄影",
    "PRODUCTIVITY":         "效率",
    "SHOPPING":             "购物",
    "SOCIAL":               "社交",
    "SPORTS":               "体育",
    "TOOLS":                "工具",
    "TRAVEL_AND_LOCAL":     "旅游与本地",
    "VIDEO_PLAYERS":        "视频播放器",
    "WEATHER":              "天气",
}

COUNTRIES = {"us": "美国", "jp": "日本", "de": "德国", "br": "巴西", "id": "印尼"}
COLLECTION = "TOP_FREE"
COUNT_PER_CAT = 120
DELAY_MIN, DELAY_MAX = 1.5, 3.0


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表：索引表 + 已见表 + 详情表 + 快照表"""
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS gp_daily_index (
            date       TEXT NOT NULL,
            country    TEXT NOT NULL,
            category_id TEXT NOT NULL,
            collection TEXT NOT NULL,
            app_id     TEXT NOT NULL,
            title      TEXT NOT NULL,
            rank       INTEGER NOT NULL,
            UNIQUE(date, country, category_id, collection, app_id)
        );

        CREATE TABLE IF NOT EXISTS gp_seen_apps (
            country         TEXT NOT NULL,
            app_id          TEXT NOT NULL,
            first_seen_date TEXT NOT NULL,
            PRIMARY KEY (country, app_id)
        );

        CREATE TABLE IF NOT EXISTS gp_app_details (
            app_id      TEXT PRIMARY KEY,
            title       TEXT,
            developer   TEXT,
            genre       TEXT,
            score       REAL,
            installs    TEXT,
            price       REAL,
            free        INTEGER,
            icon_url    TEXT,
            url         TEXT,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gp_app_snapshots (
            app_id   TEXT NOT NULL,
            date     TEXT NOT NULL,
            country  TEXT NOT NULL,
            rank     INTEGER,
            installs TEXT,
            score    REAL,
            PRIMARY KEY (app_id, date, country)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_country_date
            ON gp_daily_index(country, date);
        CREATE INDEX IF NOT EXISTS idx_seen_country
            ON gp_seen_apps(country);
    """)
    conn.commit()
    conn.close()


def scrape_index(scraper, country, cat_id, cat_name, collection):
    """拉单个分类的榜单索引，返回 [{app_id, title, rank}]"""
    try:
        apps = scraper.list_get_fields(
            collection=collection,
            category=cat_id,
            count=COUNT_PER_CAT,
            country=country, lang="en",
            fields=["appId", "title"],
        )
        results = []
        for rank, a in enumerate(apps, 1):
            if a.get("appId"):
                results.append({"app_id": a["appId"], "title": a.get("title", ""), "rank": rank})
        return results
    except Exception as e:
        print(f"    ⚠️ {cat_name}({cat_id}): {e}")
        return []


def save_index(today, country, cat_id, collection, apps):
    """写入 gp_daily_index（唯一约束跳过重复）"""
    if not apps:
        return 0
    conn = get_db()
    c = conn.cursor()
    count = 0
    for a in apps:
        try:
            c.execute(
                "INSERT OR IGNORE INTO gp_daily_index VALUES (?,?,?,?,?,?,?)",
                (today, country, cat_id, collection, a["app_id"], a["title"], a["rank"]),
            )
            count += c.rowcount
        except Exception:
            pass
    conn.commit()
    conn.close()
    return count


def diff_new_apps(today, country):
    """跟 gp_seen_apps 反连接，找出当前国家的新 app_id"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT d.app_id, d.title
        FROM gp_daily_index d
        WHERE d.date = ? AND d.country = ?
          AND d.app_id NOT IN (SELECT app_id FROM gp_seen_apps WHERE country = ?)
    """, (today, country, country))
    new = c.fetchall()
    conn.close()
    # 立刻标记为已见
    if new:
        conn = get_db()
        c = conn.cursor()
        c.executemany(
            "INSERT OR IGNORE INTO gp_seen_apps VALUES (?,?,?)",
            [(country, r["app_id"], today) for r in new],
        )
        conn.commit()
        conn.close()
    return new


def fetch_app_detail(scraper, app_id, country):
    """拉单个 App 详情"""
    try:
        detail = scraper.app_get_fields(
            app_id,
            fields=["appId","title","developer","genre","score",
                    "installs","price","free","icon","url"],
            country=country, lang="en",
        )
        return {
            "app_id": detail.get("appId", app_id),
            "title": detail.get("title", ""),
            "developer": detail.get("developer", ""),
            "genre": detail.get("genre", ""),
            "score": detail.get("score"),
            "installs": detail.get("installs", ""),
            "price": detail.get("price", 0),
            "free": 1 if detail.get("free") else 0,
            "icon_url": detail.get("icon", ""),
            "url": detail.get("url", ""),
        }
    except Exception as e:
        print(f"      ⚠️ {app_id}: {e}")
        return None


def save_details_and_snapshot(app_id, country, detail, today):
    """存详情 + 当天快照"""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT OR REPLACE INTO gp_app_details VALUES
               (?,?,?,?,?,?,?,?,?,?,?)""",
            (detail["app_id"], detail["title"], detail["developer"],
             detail["genre"], detail["score"], detail["installs"],
             detail["price"], detail["free"], detail["icon_url"],
             detail["url"], today),
        )
        conn.commit()
    except Exception as e:
        print(f"      ⚠️ 存详情失败 {app_id}: {e}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Google Play 榜单采集")
    parser.add_argument("--countries", type=str, default="us,jp,de",
                        help="国家代码，逗号分隔")
    parser.add_argument("--categories", type=str, default="",
                        help="分类 ID 逗号分隔，默认全部")
    parser.add_argument("--collection", type=str, default="TOP_FREE",
                        help="榜单类型: TOP_FREE/TOP_PAID/TOP_GROSSING")
    args = parser.parse_args()

    country_list = [c.strip() for c in args.countries.split(",") if c.strip()]
    if args.categories:
        cat_list = [(cid, GP_CATEGORIES.get(cid, cid))
                    for cid in args.categories.split(",")]
    else:
        cat_list = list(GP_CATEGORIES.items())

    today = date.today().isoformat()
    collection = args.collection

    init_db()
    scraper = GPlayScraper(http_client="requests")

    total_cats = len(country_list) * len(cat_list)
    print(f"🚀 GP 榜单采集 | {today} | {collection}")
    print(f"   国家: {', '.join(country_list)}")
    print(f"   分类: {len(cat_list)} 个 | 总任务: {total_cats} 次\n")

    # ── Phase 1: 拉索引 ──
    total_new_apps = 0
    task_idx = 0
    for country in country_list:
        cn = COUNTRIES.get(country, country)
        print(f"📡 {cn}({country})")

        for cat_id, cat_name in cat_list:
            task_idx += 1
            print(f"  [{task_idx}/{total_cats}] {cat_name} ... ", end="", flush=True)
            apps = scrape_index(scraper, country, cat_id, cat_name, collection)
            saved = save_index(today, country, cat_id, collection, apps)
            print(f"{len(apps)} 条 → 入库 {saved} 条")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        # ── Phase 2: diff 找新 App ──
        print(f"\n🔍 {cn} 增量对比...")
        new_apps = diff_new_apps(today, country)
        print(f"   新发现: {len(new_apps)} 个")
        total_new_apps += len(new_apps)

        # ── Phase 3: 新 App 拉详情 ──
        if new_apps:
            detail_count = 0
            for i, na in enumerate(new_apps):
                aid = na["app_id"]
                print(f"  [{detail_count+1}/{len(new_apps)}] {aid[:40]} ... ", end="", flush=True)
                detail = fetch_app_detail(scraper, aid, country)
                if detail:
                    save_details_and_snapshot(aid, country, detail, today)
                    detail_count += 1
                    print("✓")
                else:
                    print("✗")
                time.sleep(random.uniform(0.3, 0.8))
            print(f"  详情补全: {detail_count}/{len(new_apps)}")
        print()

    print(f"✅ 完成 | 总新发现: {total_new_apps} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
