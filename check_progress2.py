import sqlite3

try:
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    tables = ['gozlem_formlari', 'komite_raporlari', 'standart_degerlendirmeler', 'komisyon_kararlari', 'gelisim_planlari', 'gozlem_gorselleri']
    with open('final_stats.txt', 'w', encoding='utf-8') as f:
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            f.write(f"{t}: {count}\n")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
