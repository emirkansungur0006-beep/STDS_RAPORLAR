import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE il = 'ANKARA'")
ankara_hospitals = cur.fetchone()[0]
print(f"ANKARA DISTINCT HOSPITALS: {ankara_hospitals}")
cur.close()
conn.close()
