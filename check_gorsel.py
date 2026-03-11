import sqlite3

try:
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    print("--- GOZLEM GORSELLERI VERILERI ---")
    cur.execute("SELECT * FROM gozlem_gorselleri LIMIT 30")
    rows = cur.fetchall()
    for r in rows:
        print(r)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
