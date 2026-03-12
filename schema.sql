CREATE TABLE referans_hastaneler (
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
        );

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE gozlem_formlari (
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
        );

CREATE TABLE komite_raporlari (
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
        );

CREATE TABLE standart_degerlendirmeler (
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
        );

CREATE TABLE komisyon_kararlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rapor_id INTEGER,
            iyilestirme_alanlari TEXT,
            komisyon_karari TEXT,
            muafiyetler TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE gozlem_gorselleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            il TEXT NOT NULL,
            hastane_adi TEXT,
            dosya_yolu TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE gelisim_planlari (
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
        );

