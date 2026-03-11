# -*- coding: utf-8 -*-
import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

def fix():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("1. İl isimleri düzeltiliyor...")
    # Temel yazım hataları
    cur.execute("UPDATE gelisim_planlari SET il = 'İSTANBUL' WHERE il IN ('İSTANBUL KHB', 'İSTANBUL KHHB', 'ISTANBUL')")
    cur.execute("UPDATE gelisim_planlari SET il = 'GİRESUN' WHERE il = 'GİRESUNN'")
    cur.execute("UPDATE gelisim_planlari SET il = 'KOCAELİ' WHERE il = 'KOACAELİ'")
    cur.execute("UPDATE gelisim_planlari SET il = 'ÇORUM' WHERE il = 'ÇORUM..'")
    cur.execute("UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = '81HYA'")
    cur.execute("UPDATE gelisim_planlari SET il = 'AFYONKARAHİSAR' WHERE il = 'AFYIN'") # Kullanıcı afyın demiş
    
    # SAMSUNKÜTAHYA ayrıştırma
    cur.execute("UPDATE gelisim_planlari SET il = 'SAMSUN' WHERE il = 'SAMSUNKÜTAHYA' AND (sheet_adi ILIKE '%SAMSUN%' OR sheet_adi ILIKE '%SAM%')")
    cur.execute("UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = 'SAMSUNKÜTAHYA'")
    
    # Multi-il dosyası ayrıştırma
    multi_il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN'
    cur.execute(f"UPDATE gelisim_planlari SET il = 'HAKKARİ' WHERE il = '{multi_il}' AND sheet_adi ILIKE '%HAKK%'")
    cur.execute(f"UPDATE gelisim_planlari SET il = 'İZMİR' WHERE il = '{multi_il}' AND sheet_adi ILIKE '%İZMİR%'")
    cur.execute(f"UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = '{multi_il}' AND sheet_adi ILIKE '%KÜT%'")
    cur.execute(f"UPDATE gelisim_planlari SET il = 'SAMSUN' WHERE il = '{multi_il}' AND sheet_adi ILIKE '%SAM%'")
    cur.execute(f"UPDATE gelisim_planlari SET il = 'ERZURUM' WHERE il = '{multi_il}'")

    print("2. Tesis adları temizleniyor...")
    # 'İL - SAYFA' formatındaki tesis adlarını sheet_adi ile güncelle (daha anlamlı)
    cur.execute("""
        UPDATE gelisim_planlari 
        SET hastane_adi = UPPER(TRIM(sheet_adi))
        WHERE (hastane_adi LIKE '% - %' OR hastane_adi LIKE '%BİLİNMEYEN%' OR hastane_adi LIKE '%SAĞLIK TESİSİ%')
          AND sheet_adi IS NOT NULL 
          AND LENGTH(sheet_adi) > 3
          AND sheet_adi NOT ILIKE 'SAYFA%' 
          AND sheet_adi NOT ILIKE 'SHEET%'
    """)
    
    # Kalanlar için İl Sağlık Müdürlüğü varsayılanı (Eğer sheet_adi tanımsızsa)
    cur.execute("""
        UPDATE gelisim_planlari 
        SET hastane_adi = il || ' İl Sağlık Müdürlüğü'
        WHERE (hastane_adi LIKE '% - %' OR hastane_adi LIKE '%BİLİNMEYEN%' OR hastane_adi LIKE '%SAĞLIK TESİSİ%')
    """)

    conn.commit()
    print("Düzeltme tamamlandı.")
    
    cur.execute("SELECT il, COUNT(*), COUNT(DISTINCT hastane_adi) FROM gelisim_planlari GROUP BY il ORDER BY il")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} kayıt, {r[2]} tesis")

    cur.close()
    conn.close()

if __name__ == "__main__":
    fix()
