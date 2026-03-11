import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari GROUP BY il ORDER BY il")
    rows = cur.fetchall()
    print("--- GELISIM IL STATS ---")
    for r in rows:
        print(f"'{r[0]}': {r[1]} (len: {len(r[0]) if r[0] else 0})")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
