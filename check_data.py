import sqlite3, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\Desktop\工具包\app-store-intel\app_intel.db')
c = conn.cursor()

# count per category
c.execute("SELECT category_name, COUNT(*) FROM app_daily_rank WHERE date='2026-04-23' AND category_id != 'overall' GROUP BY category_id")
print("=== Category counts ===")
for row in c.fetchall():
    print(row)

print()
c.execute("SELECT discovery_type, COUNT(*) FROM discovered_gems GROUP BY discovery_type")
print("=== Discovery type counts ===")
for row in c.fetchall():
    print(row)

print()
c.execute("""
SELECT d.app_name, r.category_name, r.rank_category, det.rating_count, det.rating_avg, det.price, det.genre, ct.rank as overall_rank
FROM discovered_gems d
JOIN app_daily_rank r ON d.app_id = r.app_id AND d.date = r.date AND d.country = r.country AND d.category_id = r.category_id
LEFT JOIN app_details det ON d.app_id = det.app_id
LEFT JOIN app_chart_type ct ON d.app_id = ct.app_id AND d.country = ct.country AND ct.category_id = 'overall' AND ct.chart_type = 'overall_topgrossing' AND ct.date = d.date
WHERE d.date='2026-04-23' AND d.country='us' AND d.discovery_type='闷声型'
ORDER BY d.rank_category ASC LIMIT 10
""")
print("=== Top quiet gems US ===")
for row in c.fetchall():
    print(row)

print()
c.execute("SELECT chart_type, COUNT(*) FROM app_chart_type GROUP BY chart_type")
print("=== Chart type counts ===")
for row in c.fetchall():
    print(row)

print()
c.execute("SELECT COUNT(DISTINCT app_id) FROM app_daily_rank WHERE date='2026-04-23' AND category_id != 'overall'")
print("Total unique apps in categories:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM app_chart_type WHERE date='2026-04-23' AND category_id='overall'")
print("Total overall chart records:", c.fetchone()[0])

conn.close()