import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Hala sorunlu olanları listele
cur.execute("""
    SELECT il, hastane_adi, COUNT(*) 
    FROM gelisim_planlari 
    WHERE hastane_adi LIKE '%% - %%'
       OR hastane_adi LIKE '%%BİLİNMEYEN%%'
    GROUP BY il, hastane_adi
    ORDER BY il
""")
rows = cur.fetchall()
print(f"KALAN SORUNLU TESİS ADLARI: {len(rows)}")
for r in rows:
    print(f"  {r[0]}: '{r[1]}' ({r[2]} kayıt)")

print()
# Toplam temiz kayıtlar
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE hastane_adi NOT LIKE '%% - %%' AND hastane_adi NOT LIKE '%%BİLİNMEYEN%%'")
print(f"Temiz hastane: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM gelisim_planlari")
print(f"Toplam kayıt: {cur.fetchone()[0]}")

cur.close()
conn.close()
