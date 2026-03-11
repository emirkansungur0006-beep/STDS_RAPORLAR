import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

# Bu script tüm kilitleri kırar ve verileri düzeltir.
def kill_and_fix():
    # Kilitleri kırmak için önce 'postgres' veya default db'ye bağlanıp aktif query'leri kill etmemiz gerekebilir
    # ama genelde aynı db üzerinden de yapılabilir.
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Aktif kilitli oturumlar temizleniyor...")
        cur.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'stds_raporlar'
              AND pid <> pg_backend_pid();
        """)
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Bağlantı temizleme hatası (normal olabilir): {e}")

    # Şimdi temiz bir bağlantı ile işlemleri yap
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Veri düzeltme işlemi başlıyor...")
    # SQL v5 - En kapsamlı ve hızlı temizlik
    cur.execute("""
        -- 1. İl düzeltmeleri
        UPDATE gelisim_planlari SET il = 'İSTANBUL' WHERE il IN ('İSTANBUL KHB', 'İSTANBUL KHHB', 'ISTANBUL');
        UPDATE gelisim_planlari SET il = 'GİRESUN' WHERE il = 'GİRESUNN';
        UPDATE gelisim_planlari SET il = 'KOCAELİ' WHERE il = 'KOACAELİ';
        UPDATE gelisim_planlari SET il = 'ÇORUM' WHERE il = 'ÇORUM..';
        UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il IN ('81HYA', 'KÜYAHYA');
        UPDATE gelisim_planlari SET il = 'AFYONKARAHİSAR' WHERE il IN ('AFYIN', 'AFYON');
        
        -- SAMSUNKÜTAHYA
        UPDATE gelisim_planlari SET il = 'SAMSUN' WHERE il = 'SAMSUNKÜTAHYA' AND (sheet_adi ILIKE '%SAMSUN%' OR sheet_adi ILIKE '%SAM%');
        UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = 'SAMSUNKÜTAHYA';
        
        -- Multi-il dosyası
        UPDATE gelisim_planlari SET il = 'HAKKARİ' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND (sheet_adi ILIKE '%HAKK%' OR sheet_adi ILIKE '%HAK%');
        UPDATE gelisim_planlari SET il = 'İZMİR' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND (sheet_adi ILIKE '%İZMİR%' OR sheet_adi ILIKE '%IZM%');
        UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND (sheet_adi ILIKE '%KÜT%' OR sheet_adi ILIKE '%KUT%');
        UPDATE gelisim_planlari SET il = 'SAMSUN' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND (sheet_adi ILIKE '%SAM%');
        UPDATE gelisim_planlari SET il = 'ERZURUM' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN';
        
        -- 2. Tesis adları temizliği
        -- Sheet adı 'SAYFA' veya 'SHEET' değilse onu Tesis Adı yap
        UPDATE gelisim_planlari 
        SET hastane_adi = UPPER(TRIM(sheet_adi))
        WHERE (hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%' OR hastane_adi LIKE '%%SAĞLIK TESİSİ%%')
          AND sheet_adi IS NOT NULL 
          AND LENGTH(sheet_adi) > 3
          AND sheet_adi NOT ILIKE 'SAYFA%' 
          AND sheet_adi NOT ILIKE 'SHEET%';

        -- Kalanlar için İl Sağlık Müdürlüğü
        UPDATE gelisim_planlari 
        SET hastane_adi = il || ' İl Sağlık Müdürlüğü'
        WHERE (hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%' OR hastane_adi LIKE '%%SAĞLIK TESİSİ%%');
        
        -- 3. Gereksiz kayıt temizliği
        DELETE FROM gelisim_planlari WHERE il = 'EXCEL';
    """)
    conn.commit()
    print("Veritabanı başarıyla güncellendi.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    kill_and_fix()
