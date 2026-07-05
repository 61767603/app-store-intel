#!/usr/bin/env python3
"""
七麦数据校准脚本 — 本地版
==========================
从七麦抓取锚点应用「昨日下载量」，拟合幂律曲线，输出校准参数。

用法:
  pip install playwright && python3 -m playwright install chromium
  python3 calibrate_qimai.py                    # 抓取 + 拟合 + 输出参数
  python3 calibrate_qimai.py --apply            # 抓取 + 写入 server.py
  python3 calibrate_qimai.py --json result.json  # 抓取 + 存结果 JSON

每周跑一次，保持模型跟真实下载数据对齐。
"""

import sys
import os
import math
import re
import time
import json
import argparse
from datetime import date
from playwright.sync_api import sync_playwright, TimeoutError

# ==================== 15 个校准锚点 ====================
# 覆盖总榜各档 + 三个分类各三档
BENCHMARKS = [
    # (标签, app_id, 说明)
    ("总榜#1",   "6448311069", "ChatGPT"),
    ("总榜#5",   "1508186374", "Peacock TV"),
    ("总榜#10",  "1666653815", "HBO Max"),
    ("总榜#20",  "6739554056", "Kingshot"),
    ("总榜#50",  "1308415878", "GameChanger"),
    ("总榜#100", "6740043080", "Screwdom"),
    ("社交#1",   "1308415878", "GameChanger"),
    ("社交#10",  "1541535971", "Card Ladder"),
    ("社交#30",  "641992398",  "WNBA Scores"),
    ("天气#1",   "295646461",  "Weather Channel"),
    ("天气#10",  "6473724440", "NOAA Radar"),
    ("天气#30",  "1673731295", "Weather Nav"),
    ("教育#1",   "547436543",  "Disney Experience"),
    ("教育#10",  "1022164656", "Disneyland"),
    ("教育#30",  "6740247064", "Airclub"),
]


def fetch_all_downloads(benchmarks):
    """用 Playwright 逐个抓取七麦「昨日下载量」"""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,           # 非 headless，避免检测
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        for label, app_id, name in benchmarks:
            url = f"https://www.qimai.cn/app/rank/appid/{app_id}/country/us"
            print(f"  [{label}] {name} ... ", end="", flush=True)

            dl = None
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)

                # 提取可见文本，找「昨日下载量」后面的数字
                text = page.evaluate("() => document.body.innerText")
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if "昨日下载量" in line:
                        # 数字可能在本行或下一行
                        candidates = [line] + (
                            [lines[i + 1]] if i + 1 < len(lines) else []
                        )
                        for c in candidates:
                            m = re.search(r"([\d,]+)", c.replace("昨日下载量", ""))
                            if m:
                                dl = int(m.group(1).replace(",", ""))
                                break
                        if dl:
                            break

                if dl:
                    print(f"{dl:,}")
                    results.append((label, app_id, dl))
                else:
                    print("未提取到")
                    page.screenshot(path="/tmp/qimai_debug.png")
                    print("     (截图保存 /tmp/qimai_debug.png)")
            except TimeoutError:
                print("超时")
            except Exception as e:
                print(f"出错: {e}")

        browser.close()
    return results


def fit_power_law(ranks, downloads):
    """
    对数空间线性回归: download = a × rank^(-b)
    log(dl) = log(a) - b × log(rank)

    返回 (a, b, r_squared)
    """
    n = len(ranks)
    log_r = [math.log(r) for r in ranks]
    log_d = [math.log(d) for d in downloads]

    mean_x = sum(log_r) / n
    mean_y = sum(log_d) / n

    num = sum((log_r[i] - mean_x) * (log_d[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in log_r)

    if den < 1e-12:
        return 0, 0, 0

    b = -num / den
    log_a = mean_y + b * mean_x
    a = math.exp(log_a)

    ss_res = sum((log_d[i] - (log_a - b * log_r[i])) ** 2 for i in range(n))
    ss_tot = sum((y - mean_y) ** 2 for y in log_d)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0

    return round(a), round(b, 4), round(r2, 4)


def apply_constants(file_path, base, alpha):
    """更新 server.py 中 OVERALL_BASE 和 POWER_ALPHA"""
    with open(file_path, "r") as f:
        content = f.read()
    content = re.sub(r"OVERALL_BASE = \d+", f"OVERALL_BASE = {base}", content)
    content = re.sub(
        r"POWER_ALPHA = [\d.]+", f"POWER_ALPHA = {alpha}", content
    )
    with open(file_path, "w") as f:
        f.write(content)
    print(f"✅ 已更新 {file_path}")


def main():
    parser = argparse.ArgumentParser(description="七麦数据校准")
    parser.add_argument("--apply", action="store_true", help="写入 server.py")
    parser.add_argument("--json", type=str, help="输出结果 JSON 文件路径")
    args = parser.parse_args()

    today = date.today().isoformat()
    print(f"🔧 七麦数据校准 | {today}")
    print(f"   锚点数: {len(BENCHMARKS)}\n")

    # ── 1. 抓取 ──
    print("📡 抓取中...")
    data = fetch_all_downloads(BENCHMARKS)

    if len(data) < 3:
        print("\n❌ 数据点不足（需 ≥3），无法拟合")
        return 1

    print(f"\n✅ 获取 {len(data)} 个有效点")

    # ── 2. 分离总榜 / 分类数据 ──
    overall_ranks, overall_dl = [], []
    cat_ranks, cat_dl = [], []
    for label, app_id, dl in data:
        if label.startswith("总榜"):
            rank = int(re.search(r"(\d+)", label).group(1))
            overall_ranks.append(rank)
            overall_dl.append(dl)

    # ── 3. 拟合 ──
    print("\n📈 幂律拟合（download = a × rank^(-b)）")
    a, b, r2 = fit_power_law(overall_ranks, overall_dl)
    print(f"   总榜: a={a:,}  b={b}  R²={r2}")

    # ── 4. 验证 ──
    print("\n🔍 验证（vs 实际值）:")
    print(f"   {'Rank':<6} {'预测/日':>10} {'预测/月':>12} {'实际/日':>10}")
    for rank, dl in sorted(zip(overall_ranks, overall_dl)):
        pred = int(a * (rank ** -b))
        print(f"   #{rank:<5} {pred:>10,} {pred*30:>12,} {dl:>10,}")

    # ── 5. 输出 ──
    result = {
        "date": today,
        "base": a,
        "alpha": b,
        "r_squared": r2,
        "overall_points": len(overall_ranks),
        "data": [
            {"label": l, "app_id": aid, "downloads": dl}
            for l, aid, dl in data
        ],
    }

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 已保存: {args.json}")

    # 找到 server.py
    server_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    if not os.path.isfile(server_py):
        server_py = input("\nserver.py 路径: ").strip()

    if args.apply and os.path.isfile(server_py):
        apply_constants(server_py, a, b)
        print(f"   OVERALL_BASE = {a}")
        print(f"   POWER_ALPHA = {b}")
    else:
        print(f"\n{'─' * 50}")
        print(f"  适用参数（可手动更新 server.py）:")
        print(f"  OVERALL_BASE = {a}")
        print(f"  POWER_ALPHA = {b}")
        print(f"  R² = {r2}")
        print(f"{'─' * 50}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
