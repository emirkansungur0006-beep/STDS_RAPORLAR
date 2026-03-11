import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

def debug_adana():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, hastane_adi, kurum_hedefleri FROM gelisim_planlari WHERE il = 'ADANA' LIMIT 10;")
    rows = cur.fetchall()
    print("DEBUG ADANA ROWS:")
    for r in rows:
        print(f"ID: {r[0]} | Hosp: {r[1][:50]}... | Goal: {r[2][:50]}...")
    cur.close()
    conn.close()

if __name__ == "__main__":
    debug_adana()
