import sys
import os

# Add current directory to path so config can be imported
sys.path.append(os.getcwd())

import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari GROUP BY il ORDER BY il;")
    rows = cur.fetchall()
    print("PROVINCE RECORD COUNTS:")
    for r in rows:
        print(f"{r[0]}: {r[1]}")
    
    cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari;")
    hosp_count = cur.fetchone()[0]
    print(f"\nTOTAL UNIQUE HOSPITALS: {hosp_count}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
