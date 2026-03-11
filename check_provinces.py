import sys
import os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT il FROM gelisim_planlari ORDER BY il;")
    iller = [r[0] for r in cur.fetchall()]
    print("DISTINCT PROVINCES IN DB:")
    print(iller)
    
    # Hatalı olanları temizle (Eğer varsa)
    # Örn: '81HYA' -> 'KÜTAHYA' gibi bir durum varsa manuel düzeltme veya parser'da fix
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
