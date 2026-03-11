import psycopg2
from config import DB_CONFIG

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    tables = [
        'gozlem_formlari',
        'komite_raporlari',
        'standart_degerlendirmeler',
        'komisyon_kararlari',
        'gelisim_planlari',
        'gozlem_gorselleri',
        'referans_hastaneler'
    ]
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cur.fetchone()[0]
            print(f"{table}: {cnt}")
        except Exception as e:
            print(f"{table}: ERROR {e}")
            conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
