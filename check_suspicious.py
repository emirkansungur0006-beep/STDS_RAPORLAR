import sys
import os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # "BİLİNMEYEN" veya "GELİŞİM PLANI" içeren hastane adlarını bul
    cur.execute("""
        SELECT il, hastane_adi, kaynak_dosya, COUNT(*) 
        FROM gelisim_planlari 
        WHERE hastane_adi LIKE '%BİLİNMEYEN%' 
           OR hastane_adi LIKE '%GELİŞİM%' 
           OR hastane_adi LIKE '% - %'
        GROUP BY il, hastane_adi, kaynak_dosya 
        ORDER BY il;
    """)
    rows = cur.fetchall()
    print("SUSPICIOUS HOSPITAL NAMES:")
    for r in rows:
        print(f"IL: {r[0]} | NAME: {r[1]} | FILE: {r[2]} | COUNT: {r[3]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
