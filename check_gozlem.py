import sqlite3

try:
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    print("--- GOZLEM FORMLARI İL DAĞILIMI ---")
    cur.execute("SELECT il, COUNT(*) FROM gozlem_formlari GROUP BY il ORDER BY count(*) DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"{r[0]}: {r[1]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
