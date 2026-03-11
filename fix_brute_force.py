# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher, normalize_turkish

def fix_brute_force():
    problem_files = {
        'ADANA.xlsx': 'ADANA',
        'AFYONKARAHİSAR.xlsx': 'AFYONKARAHİSAR',
        'BARTIN.xlsx': 'BARTIN',
        'BALIKESİR.xlsx': 'BALIKESİR',
        'BURDUR.xlsx': 'BURDUR',
        'KIRIKKALE.xlsx': 'KIRIKKALE',
        'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx': 'İSTANBUL'
    }
    
    matcher = ReferenceMatcher()
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_count = 0
    
    for filename, city_name in problem_files.items():
        path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', filename)
        if not os.path.exists(path): continue
            
        print(f"--- BRUTE FORCE: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        current_hosp_name = None
        current_hosp_code = None
        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row if c is not None]
            if not any(cells): continue
            
            # HASTANE TESPİTİ (Brute force: Her hücreye bak)
            found_hosp = False
            for cell in cells[:3]: # Genelde ilk 3 sütundadır
                if len(cell) > 10:
                    # İl kısıtlaması olmadan eşleştir (Çünkü dosya içindeki isim il içermeyebilir)
                    m = matcher.match_by_name(cell, il=city_name, threshold=0.8)
                    if m:
                        current_hosp_name = m['kurum_adi']
                        current_hosp_code = m['kurum_kodu']
                        found_hosp = True
                        break
            
            if found_hosp: continue

            # VERİ KAYIT
            if current_hosp_name:
                val = cells[0] if len(cells) > 0 else ""
                val_up = val.upper()
                if len(val) > 20:
                    if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', 'STRATEJİK']):
                        continue
                    if val_up in current_hosp_name.upper() or current_hosp_name.upper() in val_up:
                         continue
                         
                    cur.execute("""
                        INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, kaynak_dosya)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (city_name, current_hosp_name, current_hosp_code, val, filename))
                    city_count += 1

        print(f"  -> {city_count} kayıt.")
        total_count += city_count
        wb.close()

    conn.commit()
    print(f"\nBİTTİ. TOPLAM: {total_count}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_brute_force()
