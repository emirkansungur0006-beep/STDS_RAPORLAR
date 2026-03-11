import sys, os
sys.path.append(os.getcwd())
import psycopg2, openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher

matcher = ReferenceMatcher()
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
GELISIM_DIR = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller')

# Hala sorunlu olanları getir
cur.execute("""
    SELECT DISTINCT il, hastane_adi, sheet_adi, kaynak_dosya
    FROM gelisim_planlari 
    WHERE hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%'
    ORDER BY il
""")
suspicious = cur.fetchall()
print(f"İkinci tur: {len(suspicious)} kayıt düzeltilecek.\n")

fixed = 0
for il, bad_name, sheet_adi, dosya in suspicious:
    # Excel dosyasından hastane adını direkt oku
    filepath = os.path.join(GELISIM_DIR, dosya)
    if not os.path.exists(filepath):
        print(f"  ✗ Dosya yok: {dosya}")
        continue
    
    match = None
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        if sheet_adi in wb.sheetnames:
            ws = wb[sheet_adi]
            # İlk 20 satırdaki her hücreyi kontrol et
            for i, row in enumerate(ws.iter_rows(values_only=True, max_row=20)):
                if match: break
                for cell in row:
                    if not cell: continue
                    c = str(cell).strip()
                    if len(c) < 8: continue
                    # ADI: kalıbını temizle
                    if 'ADI:' in c.upper():
                        c = c.upper().split('ADI:')[-1].strip()
                    m = matcher.match_by_name(c, il=il, threshold=0.6)
                    if m and len(m['kurum_adi']) > 10:
                        match = m
                        break
        wb.close()
    except:
        pass
    
    if match:
        cur.execute("""
            UPDATE gelisim_planlari 
            SET hastane_adi = %s, kurum_kodu = %s
            WHERE il = %s AND hastane_adi = %s AND sheet_adi = %s
        """, (match['kurum_adi'], match['kurum_kodu'], il, bad_name, sheet_adi))
        print(f"  ✓ {il}: '{bad_name}' → '{match['kurum_adi']}'")
        fixed += 1
    else:
        # Son çare: Sheet adını temiz bir şekilde kullan
        clean_name = sheet_adi.strip().upper() if sheet_adi else bad_name
        # "Sayfa1" vb. kalıpları filtrele
        if clean_name.startswith('SAYFA') or clean_name.startswith('SHEET') or len(clean_name) < 5:
            # dosya adından il çıkar ve sadece il bazlı bırak
            clean_name = f"{il} SAĞLIK TESİSİ"
        cur.execute("""
            UPDATE gelisim_planlari
            SET hastane_adi = %s
            WHERE il = %s AND hastane_adi = %s AND sheet_adi = %s
        """, (clean_name, il, bad_name, sheet_adi))
        print(f"  ~ {il}: '{bad_name}' → '{clean_name}' (sheet fallback)")
        fixed += 1

conn.commit()

# Sonuç
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari")
total_hosp = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM gelisim_planlari")
total_rec = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%'")
still_bad = cur.fetchone()[0]

print(f"\n{'='*50}")
print(f"SONUÇ: {fixed} isim düzeltildi")
print(f"Toplam benzersiz tesis: {total_hosp}")
print(f"Toplam kayıt: {total_rec}")
print(f"Hala sorunlu: {still_bad}")
print(f"{'='*50}")

cur.close()
conn.close()
