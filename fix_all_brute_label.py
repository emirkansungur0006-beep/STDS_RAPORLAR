# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def fix_all_brute_label():
    problem_files = {
        'ADANA.xlsx': 'ADANA',
        'AFYONKARAHİSAR.xlsx': 'AFYONKARAHİSAR',
        'BARTIN.xlsx': 'BARTIN',
        'BALIKESİR.xlsx': 'BALIKESİR',
        'BURDUR.xlsx': 'BURDUR',
        'KIRIKKALE.xlsx': 'KIRIKKALE',
        'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx': 'İSTANBUL'
    }
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_count = 0
    
    for filename, city_name in problem_files.items():
        path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', filename)
        if not os.path.exists(path): continue
            
        print(f"--- BRUTE LABEL: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        current_hosp_name = None
        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row if c is not None]
            if not any(cells): continue
            
            # 1. HASTANE TESPİTİ (Etiket bazlı - Çok esnek)
            val0 = cells[0].upper()
            if any(label in val0 for label in ['KURUM ADI', 'HASTANE ADI', 'TESİS ADI']):
                if len(cells) > 1 and len(cells[1]) > 5:
                    current_hosp_name = cells[1].upper()
                    print(f"  L{i+1} NEW HOSP: {current_hosp_name}")
                    continue
            
            # Adana stili: İlk hücrede hastane adı varsa ve 'HASTANE' geçiyorsa
            if not current_hosp_name or i < 10: # İlk 10 satırda her zaman bak
                if 'HASTANE' in val0 or 'MERKEZ' in val0 or 'ADSM' in val0:
                    if len(val0) > 10 and 'HEDEF' not in val0 and 'MÜDÜRLÜĞÜ' not in val0:
                        current_hosp_name = val0
                        print(f"  L{i+1} NEW HOSP (Direct): {current_hosp_name}")
                        continue

            # 2. VERİ KAYIT
            if current_hosp_name and len(cells[0]) > 20:
                val = cells[0]
                val_up = val.upper()
                if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI']):
                    continue
                if val_up in current_hosp_name:
                    continue

                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s)
                """, (city_name, current_hosp_name, val, filename))
                city_count += 1

        print(f"  -> {city_count} kayıt yüklendi.")
        total_count += city_count
        wb.close()

    conn.commit()
    print(f"\nBİTTİ. TOPLAM: {total_count}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_all_brute_label()
