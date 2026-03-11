# -*- coding: utf-8 -*-
"""
STDS Raporlar - Veritabanı Başlatma ve Şema Oluşturma
PostgreSQL 18 üzerinde stds_raporlar veritabanı kurulumu
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': '1234567'
}

DB_NAME = 'stds_raporlar'


def create_database():
    """stds_raporlar veritabanını oluştur"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Veritabanı var mı kontrol et
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"[INFO] '{DB_NAME}' veritabanı zaten mevcut.")
    else:
        cur.execute(f"CREATE DATABASE {DB_NAME} ENCODING 'UTF8'")
        print(f"[OK] '{DB_NAME}' veritabanı oluşturuldu.")

    cur.close()
    conn.close()


def create_tables():
    """Tablo şemalarını oluştur"""
    conn = psycopg2.connect(dbname=DB_NAME, **DB_CONFIG)
    cur = conn.cursor()

    # Referans Hastaneler Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referans_hastaneler (
            id SERIAL PRIMARY KEY,
            kurum_kodu INTEGER UNIQUE NOT NULL,
            il VARCHAR(100) NOT NULL,
            ilce VARCHAR(100) NOT NULL,
            kurum_adi TEXT NOT NULL,
            kurum_adi_normalized TEXT,
            eah VARCHAR(200),
            kurum_turu VARCHAR(50),
            tescil_unit_sayisi INTEGER,
            tescil_yatak_sayisi INTEGER,
            sinif VARCHAR(10),
            gruplar VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[OK] referans_hastaneler tablosu oluşturuldu.")

    # Gözlem Formları Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gozlem_formlari (
            id SERIAL PRIMARY KEY,
            kurum_kodu INTEGER REFERENCES referans_hastaneler(kurum_kodu) ON DELETE SET NULL,
            il VARCHAR(100) NOT NULL,
            ilce VARCHAR(100),
            hastane_adi TEXT NOT NULL,
            bolum VARCHAR(200) NOT NULL,
            soru_no INTEGER,
            soru TEXT,
            verilen_derece VARCHAR(50),
            notlar TEXT,
            kaynak_dosya TEXT,
            sheet_adi VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_gozlem_il ON gozlem_formlari(il);
        CREATE INDEX IF NOT EXISTS idx_gozlem_ilce ON gozlem_formlari(ilce);
        CREATE INDEX IF NOT EXISTS idx_gozlem_kurum ON gozlem_formlari(kurum_kodu);
        CREATE INDEX IF NOT EXISTS idx_gozlem_derece ON gozlem_formlari(verilen_derece);
    """)
    print("[OK] gozlem_formlari tablosu oluşturuldu.")

    # Komite/Komisyon Raporları Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS komite_raporlari (
            id SERIAL PRIMARY KEY,
            kurum_kodu INTEGER REFERENCES referans_hastaneler(kurum_kodu) ON DELETE SET NULL,
            il VARCHAR(100) NOT NULL,
            ilce VARCHAR(100),
            hastane_adi TEXT NOT NULL,
            rapor_tipi VARCHAR(20) NOT NULL,
            degerlendirme_tarihi DATE,
            degerlendirme_saati TIME,
            ekip_uyeleri TEXT,
            kaynak_dosya TEXT,
            dosya_formati VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_komite_il ON komite_raporlari(il);
        CREATE INDEX IF NOT EXISTS idx_komite_ilce ON komite_raporlari(ilce);
        CREATE INDEX IF NOT EXISTS idx_komite_kurum ON komite_raporlari(kurum_kodu);
        CREATE INDEX IF NOT EXISTS idx_komite_tip ON komite_raporlari(rapor_tipi);
    """)
    print("[OK] komite_raporlari tablosu oluşturuldu.")

    # Standart Değerlendirme Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standart_degerlendirmeler (
            id SERIAL PRIMARY KEY,
            rapor_id INTEGER REFERENCES komite_raporlari(id) ON DELETE CASCADE,
            standart_no VARCHAR(50),
            standart_adi TEXT,
            degerlendirme_olcutu TEXT,
            uygunluk_durumu VARCHAR(30),
            eksikler TEXT,
            sorumlu TEXT,
            planlanan_baslangic_tarihi DATE,
            planlanan_bitis_tarihi DATE,
            son_durum VARCHAR(30),
            aciklama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_standart_rapor ON standart_degerlendirmeler(rapor_id);
        CREATE INDEX IF NOT EXISTS idx_standart_uygunluk ON standart_degerlendirmeler(uygunluk_durumu);
        CREATE INDEX IF NOT EXISTS idx_standart_sondurum ON standart_degerlendirmeler(son_durum);
    """)
    print("[OK] standart_degerlendirmeler tablosu oluşturuldu.")

    # Komisyon Kararları Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS komisyon_kararlari (
            id SERIAL PRIMARY KEY,
            rapor_id INTEGER REFERENCES komite_raporlari(id) ON DELETE CASCADE,
            iyilestirme_alanlari TEXT,
            komisyon_karari TEXT,
            muafiyetler TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_karar_rapor ON komisyon_kararlari(rapor_id);
    """)
    print("[OK] komisyon_kararlari tablosu oluşturuldu.")

    # İşleme Durumu Tablosu (progress tracking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS isleme_durumu (
            id SERIAL PRIMARY KEY,
            dosya_yolu TEXT UNIQUE NOT NULL,
            dosya_tipi VARCHAR(20),
            durum VARCHAR(20) DEFAULT 'bekliyor',
            hata_mesaji TEXT,
            isleme_zamani TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[OK] isleme_durumu tablosu oluşturuldu.")

    # Gözlem Görselleri Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gozlem_gorselleri (
            id SERIAL PRIMARY KEY,
            il VARCHAR(100) NOT NULL,
            hastane_adi TEXT,
            dosya_yolu TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_gorsel_il ON gozlem_gorselleri(il);
    """)
    print("[OK] gozlem_gorselleri tablosu oluşturuldu.")

    conn.commit()
    cur.close()
    conn.close()
    print("\n[TAMAM] Tüm tablolar başarıyla oluşturuldu!")


if __name__ == '__main__':
    print("=" * 60)
    print("STDS Raporlar - Veritabanı Kurulumu")
    print("=" * 60)
    create_database()
    create_tables()
