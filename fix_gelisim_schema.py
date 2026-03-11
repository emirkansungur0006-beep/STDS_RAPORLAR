import sqlite3

def fix_schema():
    conn = sqlite3.connect('stds.db')
    cur = conn.cursor()
    
    # Drop existing table
    print("Dropping old gelisim_planlari table...")
    cur.execute("DROP TABLE IF EXISTS gelisim_planlari")
    
    # Recreate with correct schema
    print("Creating new gelisim_planlari table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gelisim_planlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kurum_kodu INTEGER,
            il TEXT NOT NULL,
            ilce TEXT,
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
            sheet_adi TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Schema fixed successfully.")

if __name__ == '__main__':
    fix_schema()
