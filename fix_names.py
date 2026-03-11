# -*- coding: utf-8 -*-
"""
Hatalı tesis adlarını doğrudan veritabanında düzeltir.
'İL - SAYFA ADI' formatındakileri referans hastanelerle eşleştirir.
"""
import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG
from reference_matcher import ReferenceMatcher

matcher = ReferenceMatcher()
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# 1. Hatalı isimleri bul (İL - SAYFA ADI formatında olanlar)
cur.execute("""
    SELECT DISTINCT il, hastane_adi, sheet_adi, kaynak_dosya
    FROM gelisim_planlari 
    WHERE hastane_adi LIKE '%% - %%'
       OR hastane_adi LIKE '%%BİLİNMEYEN%%'
    ORDER BY il
""")
suspicious = cur.fetchall()
print(f"Düzeltilecek {len(suspicious)} benzersiz hatalı isim bulundu.\n")

fixed = 0
for il, bad_name, sheet_adi, dosya in suspicious:
    # Strateji: Sheet adını referansla eşleştir
    match = None
    
    # 1. Sheet adını dene
    if sheet_adi and len(sheet_adi) > 3:
        match = matcher.match_by_name(sheet_adi, il=il, threshold=0.65)
    
    # 2. Hatalı ismin ' - ' sonrasını dene
    if not match and ' - ' in bad_name:
        part = bad_name.split(' - ', 1)[1].strip()
        if len(part) > 3:
            match = matcher.match_by_name(part, il=il, threshold=0.65)
    
    if match:
        new_name = match['kurum_adi']
        new_code = match['kurum_kodu']
        cur.execute("""
            UPDATE gelisim_planlari 
            SET hastane_adi = %s, kurum_kodu = %s
            WHERE il = %s AND hastane_adi = %s
        """, (new_name, new_code, il, bad_name))
        print(f"  ✓ {il}: '{bad_name}' → '{new_name}'")
        fixed += 1
    else:
        print(f"  ✗ {il}: '{bad_name}' (eşleşme bulunamadı, sheet: {sheet_adi})")

conn.commit()

# 2. Sonuç raporu
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE hastane_adi NOT LIKE '%% - %%' AND hastane_adi NOT LIKE '%%BİLİNMEYEN%%'")
clean = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%'")
still_bad = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM gelisim_planlari")
total = cur.fetchone()[0]

print(f"\n{'='*50}")
print(f"SONUÇ: {fixed} isim düzeltildi")
print(f"Temiz tesis: {clean} | Hala hatalı: {still_bad} | Toplam kayıt: {total}")
print(f"{'='*50}")

cur.close()
conn.close()
