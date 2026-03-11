import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

def check_adana():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("--- ADANA TESİS ADLARI ---")
    cur.execute("""
        SELECT DISTINCT hastane_adi, sheet_adi, kaynak_dosya 
        FROM gelisim_planlari 
        WHERE il = 'ADANA'
        ORDER BY hastane_adi;
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"Hosp: {r[0]} | Sheet: {r[1]} | File: {r[2]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_adana()
