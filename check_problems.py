import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

def check_problematic_cities():
    cities = ['ADANA', 'AFYONKARAHİSAR', 'BARTIN', 'BALIKESİR', 'BURDUR', 'KIRIKKALE', 'İSTANBUL']
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    for city in cities:
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE il = %s", (city,))
        cnt, hosp_cnt = cur.fetchone()
        print(f"{city}: {cnt} records, {hosp_cnt} hospitals")
        if hosp_cnt > 0:
            cur.execute("SELECT DISTINCT hastane_adi FROM gelisim_planlari WHERE il = %s LIMIT 3", (city,))
            hosps = [r[0] for r in cur.fetchall()]
            print(f"  Examples: {hosps}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_problematic_cities()
