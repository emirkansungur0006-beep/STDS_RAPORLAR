# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher, normalize_turkish

def fix_all_emergency_final():
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
        if not os.path.exists(path):
            print(f"! DOSYA YOK: {filename}")
            continue
            
        print(f"--- İŞLENİYOR: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        current_hosp_name = None
        current_hosp_code = None
        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row]
            if not any(cells): continue
            
            row_str = " ".join(cells).upper()
            
            # 1. TESPİT STRATEJİLERİ
            found_match = None
            
            # Pattern A: 'KURUM ADI:' etiketi
            if 'KURUM ADI:' in cells[0].upper() and len(cells) > 1 and len(cells[1]) > 5:
                found_match = matcher.match_by_name(cells[1], il=city_name, threshold=0.55)
            
            # Pattern B: 'HASTANE ADI:' etiketi
            elif 'HASTANE ADI:' in cells[0].upper() and len(cells) > 1 and len(cells[1]) > 5:
                found_match = matcher.match_by_name(cells[1], il=city_name, threshold=0.55)

            # Pattern C: Hücrede hastane ismi direkt geçiyorsa (Brute force cell 0-2)
            if not found_match:
                for ci in range(min(3, len(cells))):
                    c_val = cells[ci]
                    if len(c_val) > 10 and ('HASTANE' in c_val.upper() or 'MERKEZ' in c_val.upper()):
                        found_match = matcher.match_by_name(c_val, il=city_name, threshold=0.6)
                        if found_match: break
            
            # Pattern D: Kurum Kodu (Garanti)
            if not found_match and 'KURUM KODU:' in cells[0].upper() and len(cells) > 1:
                found_match = matcher.match_by_code(cells[1])

            if found_match:
                current_hosp_name = found_match['kurum_adi']
                current_hosp_code = found_match['kurum_kodu']
                # print(f"  L{i+1}: Matched -> {current_hosp_name}")
                continue

            # 2. VERİ KAYIT
            if current_hosp_name and len(cells[0]) > 20:
                val = cells[0]
                val_up = val.upper()
                # Başlıkları veya hastane ismini atla
                if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI', 'STRATEJİK']):
                    continue
                if val_up in current_hosp_name.upper():
                    continue

                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s, %s)
                """, (city_name, current_hosp_name, current_hosp_code, val, filename))
                city_count += 1

        print(f"  -> {city_count} kayıt yüklendi.")
        total_count += city_count
        wb.close()

    conn.commit()
    print(f"\nİŞLEM TAMAMLANDI. TOPLAM: {total_count}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_all_emergency_final()
