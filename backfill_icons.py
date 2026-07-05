#!/usr/bin/env python3
"""为已有数据补抓 icon_url"""
import sqlite3, requests, time, sys, io, os, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_intel.db")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-us",
})

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT app_id FROM app_details WHERE icon_url IS NULL OR icon_url = ''")
missing = c.fetchall()
print(f"需要补抓 icon_url: {len(missing)} 个")

batch_size = 100
updated = 0
for i in range(0, len(missing), batch_size):
    batch = [row[0] for row in missing[i:i+batch_size]]
    ids_str = ",".join(batch)
    try:
        resp = SESSION.get("https://itunes.apple.com/lookup", params={"id": ids_str}, timeout=30)
        data = resp.json()
        for app in data.get("results", []):
            if app.get("wrapperType") == "software":
                aid = str(app.get("trackId", ""))
                icon = app.get("artworkUrl512", app.get("artworkUrl100", ""))
                if aid and icon:
                    c.execute("UPDATE app_details SET icon_url = ? WHERE app_id = ?", (icon, aid))
                    updated += 1
        conn.commit()
        print(f"  批次 {i//batch_size+1}/{(len(missing)-1)//batch_size+1}: 更新 {updated} 个")
    except Exception as e:
        print(f"  批次异常: {e}")
    time.sleep(random.uniform(0.5, 1.5))

conn.commit()
conn.close()
print(f"完成，共更新 {updated} 个 icon_url")