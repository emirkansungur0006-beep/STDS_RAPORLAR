import sqlite3
import time

tables = ['referans_hastaneler', 'gozlem_formlari', 'komite_raporlari', 'standart_degerlendirmeler', 'komisyon_kararlari', 'gelisim_planlari', 'gozlem_gorselleri']

with open('db_progress.txt', 'w', encoding='utf-8') as f:
    try:
        conn = sqlite3.connect('stds.db')
        cur = conn.cursor()
        f.write("--- SQLITE ROW COUNTS ---\n")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            f.write(f"{t}: {count}\n")
        
        f.write("\n--- GELISIM_PLANLARI İL DAĞILIMI ---\n")
        cur.execute("SELECT il, COUNT(*) FROM gelisim_planlari GROUP BY il ORDER BY count(*) DESC")
        rows = cur.fetchall()
        for r in rows:
            f.write(f"{r[0]}: {r[1]}\n")
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")
