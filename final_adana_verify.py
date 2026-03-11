import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

def final_verify():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM gelisim_planlari WHERE il = 'ADANA'")
    cnt = cur.fetchone()[0]
    print(f"ADANA TOTAL RECORDS: {cnt}")
    
    cur.execute("SELECT DISTINCT hastane_adi FROM gelisim_planlari WHERE il = 'ADANA'")
    hosps = [r[0] for r in cur.fetchall()]
    print(f"ADANA HOSPITALS ({len(hosps)}):")
    for h in hosps:
        print(f"  - {h}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    final_verify()
