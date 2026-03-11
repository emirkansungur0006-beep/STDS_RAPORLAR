# -*- coding: utf-8 -*-
"""
STDS Raporlar - SQLite Veritabanı Başlatma
"""
import sqlite3
import os
from config import SQLITE_DB_PATH

def init_sqlite():
    """SQLite veritabanını ve tablolarını oluştur"""
    print(f"SQLite veritabanı oluşturuluyor: {SQLITE_DB_PATH}")
    
    # Eskisini sil (temiz başlangıç için opsiyonel, ama manuel güncelleme için gerekli)
    if os.path.exists(SQLITE_DB_PATH):
        try:
            os.remove(SQLITE_DB_PATH)
            print("Eski veritabanı dosyası silindi.")
        except:
            print("UYARI: Eski veritabanı dosyası silinemedi, üzerine yazılacak.")

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()

    # Tablo şemaları (PostgreSQL ile uyumlu)
    
    # Referans Hastaneler
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referans_hastaneler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kurum_kodu INTEGER UNIQUE NOT NULL,
            il TEXT NOT NULL,
            ilce TEXT NOT NULL,
            kurum_adi TEXT NOT NULL,
            kurum_adi_normalized TEXT,
            eah TEXT,
            kurum_turu TEXT,
            tescil_unit_sayisi INTEGER,
            tescil_yatak_sayisi INTEGER,
            sinif TEXT,
            gruplar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Gözlem Formları
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gozlem_formlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kurum_kodu INTEGER,
            il TEXT NOT NULL,
            ilce TEXT,
            hastane_adi TEXT NOT NULL,
            bolum TEXT NOT NULL,
            soru_no INTEGER,
            soru TEXT,
            verilen_derece TEXT,
            notlar TEXT,
            kaynak_dosya TEXT,
            sheet_adi TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Komite Raporları
    cur.execute("""
        CREATE TABLE IF NOT EXISTS komite_raporlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kurum_kodu INTEGER,
            il TEXT NOT NULL,
            ilce TEXT,
            hastane_adi TEXT NOT NULL,
            rapor_tipi TEXT NOT NULL,
            degerlendirme_tarihi DATE,
            degerlendirme_saati TIME,
            ekip_uyeleri TEXT,
            kaynak_dosya TEXT,
            dosya_formati TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Standart Değerlendirmeler
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standart_degerlendirmeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rapor_id INTEGER,
            standart_no TEXT,
            standart_adi TEXT,
            degerlendirme_olcutu TEXT,
            uygunluk_durumu TEXT,
            eksikler TEXT,
            sorumlu TEXT,
            planlanan_baslangic_tarihi DATE,
            planlanan_bitis_tarihi DATE,
            son_durum TEXT,
            aciklama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Komisyon Kararları
    cur.execute("""
        CREATE TABLE IF NOT EXISTS komisyon_kararlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rapor_id INTEGER,
            iyilestirme_alanlari TEXT,
            komisyon_karari TEXT,
            muafiyetler TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Gelişim Planları
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

    # Gözlem Görselleri
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gozlem_gorselleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            il TEXT NOT NULL,
            hastane_adi TEXT,
            dosya_yolu TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Kullanıcılar (Giriş Sistemi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indeksler
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gozlem_il ON gozlem_formlari(il)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_komite_il ON komite_raporlari(il)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gorsel_hastane ON gozlem_gorselleri(hastane_adi)")

    conn.commit()
    conn.close()
    print("[OK] SQLite şeması hazır.")

if __name__ == "__main__":
    init_sqlite()
