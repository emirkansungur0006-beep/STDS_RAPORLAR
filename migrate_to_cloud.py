# -*- coding: utf-8 -*-
import sqlite3
import psycopg2
import os
from config import SQLITE_DB_PATH

def migrate():
    from config import DB_CONFIG
    target_url = os.environ.get('DATABASE_URL')
    
    if not target_url:
        print("HATA: DATABASE_URL çevre değişkeni bulunamadı!")
        return

    print(f"Taşıma işlemi başlıyor: Local PostgreSQL -> Cloud")
    
    src_conn = psycopg2.connect(**DB_CONFIG)
    src_cur = src_conn.cursor()
    
    tgt_conn = psycopg2.connect(target_url)
    tgt_cur = tgt_conn.cursor()

    tables = [
        'users', 
        'referans_hastaneler', 
        'gozlem_formlari', 
        'komite_raporlari', 
        'gelisim_planlari',
        'standart_degerlendirmeler',
        'gozlem_gorselleri'
    ]

    for table in tables:
        print(f"Tablo taşınıyor: {table}...")
        
        # Hedef tabloyu temizle
        tgt_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
        
        # Kaynak verileri al
        src_cur.execute(f"SELECT * FROM {table}")
        rows = src_cur.fetchall()
        
        if not rows:
            print(f"  {table} tablosunda veri yok, atlanıyor.")
            continue

        # Sütun isimlerini al
        src_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position")
        cols = [col[0] for col in src_cur.fetchall()]
        col_str = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        
        # Verileri aktar
        insert_query = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
        psycopg2.extras.execute_values(tgt_cur, insert_query, rows)
        
        print(f"  {len(rows)} kayıt aktarıldı.")

    tgt_conn.commit()
    print("MİGRASYON BAŞARIYLA TAMAMLANDI!")
    
    src_conn.close()
    tgt_conn.close()

if __name__ == "__main__":
    import psycopg2.extras
    migrate()
