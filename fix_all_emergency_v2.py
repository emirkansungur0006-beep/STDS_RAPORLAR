# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher

def fix_all_emergency_v2():
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
            
            # PATTERN 1: "KURUM ADI:" (Istanbul style)
            if 'KURUM ADI:' in cells[0].upper() and len(cells) > 1 and len(cells[1]) > 5:
                potential = cells[1]
                match = matcher.match_by_name(potential, il=city_name, threshold=0.7)
                if match:
                    current_hosp_name = match['kurum_adi']
                    current_hosp_code = match['kurum_kodu']
                    # print(f"  L{i+1}: {current_hosp_name}")
                    continue

            # PATTERN 2: Direct Match in Cell 0 (Adana/General style)
            val = cells[0]
            if len(val) > 10 and ('HASTANE' in val.upper() or 'MERKEZ' in val.upper()):
                # Başlıkları atla
                if any(kw in val.upper() for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ']):
                    pass
                else:
                    match = matcher.match_by_name(val, il=city_name, threshold=0.7)
                    if match:
                        current_hosp_name = match['kurum_adi']
                        current_hosp_code = match['kurum_kodu']
                        # print(f"  L{i+1}: {current_hosp_name}")
                        continue

            # PATTERN 3: Kurum Kodu (Garanti)
            if 'KURUM KODU:' in cells[0].upper() and len(cells) > 1:
                match = matcher.match_by_code(cells[1])
                if match:
                    current_hosp_name = match['kurum_adi']
                    current_hosp_code = match['kurum_kodu']
                    continue

            # VERİ KAYIT
            if current_hosp_name and len(cells[0]) > 20:
                val = cells[0]
                val_up = val.upper()
                if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI']):
                    continue
                if val_up in current_hosp_name.upper():
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
    fix_all_emergency_v2()
