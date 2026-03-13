import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Veritabanı Yapılandırması
DB_URL_ENV = os.environ.get('DATABASE_URL')
USE_SQLITE = False if DB_URL_ENV else True

# PostgreSQL Ayarları (PostgreSQL kullanılacaksa bu kısım DATABASE_URL'den ezilir)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': '1234567',
    'dbname': 'stds_raporlar'
}

# SQLite Ayarları
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'stds.db')

# Klasör Yapısı (Göreceli Yollar)
RAPORLAR_DIR = os.path.join(BASE_DIR, 'RAPORLAR')
GOZLEM_DIR = os.path.join(RAPORLAR_DIR, 'GÖZLEM FORMLARI')
KOMITE_DIR = os.path.join(RAPORLAR_DIR, 'KOMİTE KOMİSYON RAPORLARI')
REFERANS_DIR = os.path.join(RAPORLAR_DIR, 'REFERANS')
REFERANS_FILE = os.path.join(REFERANS_DIR, 'hastaneler_referans.xlsx')

# Görsel Klasörü
GÖZLEM_GÖRSELLER_DIR = os.path.join(GOZLEM_DIR, 'İL GÖRSELLERİ')

# Uygulama Güvenliği
SECRET_KEY = os.environ.get('SECRET_KEY', 'stds-saglik-bakanligi-secure-key-2024')

# Supabase Storage Ayarları
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://casbkhujugmibpybhmvm.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_secret_kkqvW8fy_qwGEeTSUjPVeA_9V1KxGh3')
BUCKET_RAPORLAR = 'stds_raporlar'
BUCKET_GORSELLER = 'stds_gorseller'
