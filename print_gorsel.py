import sqlite3
import json

try:
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    cur.execute("SELECT hastane_adi, dosya_yolu FROM gozlem_gorselleri LIMIT 10")
    rows = [{"hastane": r[0], "yol": r[1]} for r in cur.fetchall()]
    with open('gorsel_out.json', 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
