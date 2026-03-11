# -*- coding: utf-8 -*-
import psycopg2
from config import DB_CONFIG

def create_gelisim_table():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("gelisim_planlari tablosu oluşturuluyor...")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gelisim_planlari (
            id SERIAL PRIMARY KEY,
            kurum_kodu INTEGER REFERENCES referans_hastaneler(kurum_kodu) ON DELETE SET NULL,
            il VARCHAR(100) NOT NULL,
            ilce VARCHAR(100),
            hastane_adi TEXT NOT NULL,
            kurum_hedefleri TEXT,
            gerceklesme_suresi TEXT,
            mevcut_durum TEXT,
            cozum_secenekleri TEXT,
            etki_analizi TEXT,
            uygun_secenek TEXT,
            isbirligi_plani TEXT,
            uygulama_takvimi TEXT,
            kaynak_dosya TEXT,
            sheet_adi VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_gelisim_il ON gelisim_planlari(il);
        CREATE INDEX IF NOT EXISTS idx_gelisim_ilce ON gelisim_planlari(ilce);
        CREATE INDEX IF NOT EXISTS idx_gelisim_hastane ON gelisim_planlari(hastane_adi);
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("[OK] gelisim_planlari tablosu başarıyla oluşturuldu.")

if __name__ == "__main__":
    create_gelisim_table()
