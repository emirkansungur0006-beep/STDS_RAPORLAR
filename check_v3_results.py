import sys
import os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM gelisim_planlari;")
    total = cur.fetchone()[0]
    print(f"TOTAL RECORDS: {total}")
    
    cur.execute("SELECT COUNT(DISTINCT il) FROM gelisim_planlari;")
    total_iller = cur.fetchone()[0]
    print(f"TOTAL PROVINCES: {total_iller}")

    cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari;")
    total_hastaneler = cur.fetchone()[0]
    print(f"TOTAL UNIQUE HOSPITALS: {total_hastaneler}")
    
    print("\n--- PROVINCE COUNTS ---")
    cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari GROUP BY il ORDER BY il;")
    for r in cur.fetchall():
        print(f"{r[0]}: {r[1]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
