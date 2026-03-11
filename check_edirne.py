import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari WHERE il ILIKE '%ED%RN%' GROUP BY il")
    rows = cur.fetchall()
    with open('edirne_result.txt', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(f"IL: {r[0]} | COUNT: {r[1]}\n")
    cur.close()
    conn.close()
    print("Done. Check edirne_result.txt")
except Exception as e:
    print(f"Error: {e}")
