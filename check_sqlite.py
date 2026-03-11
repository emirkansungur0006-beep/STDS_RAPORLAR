import sqlite3
import time

tables = ['referans_hastaneler', 'gozlem_formlari', 'komite_raporlari', 'standart_degerlendirmeler', 'gelisim_planlari', 'gozlem_gorselleri']

try:
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    print("--- SQLITE ROW COUNTS ---")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"{t}: {count}")
    
    # check gelisim_planlari distribution
    print("\n--- GELISIM_PLANLARI İL DAĞILIMI ---")
    cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari GROUP BY il ORDER BY count(*) DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"{r[0]}: {r[1]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
