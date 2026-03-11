import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM gelisim_planlari WHERE hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%'")
bad = cur.fetchone()[0]
print(f"BAD NAMES REMAINING: {bad}")
cur.close()
conn.close()
