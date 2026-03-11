# -*- coding: utf-8 -*-
import os
import re
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def slugify(text):
    if not text: return ""
    t = str(text).upper().replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
    return re.sub(r'\s+', '', t)

def super_mega_fix_v2():
    problem_files = {
        'ADANA.xlsx': 'ADANA',
        'AFYONKARAHİSAR.xlsx': 'AFYONKARAHİSAR',
        'BARTIN.xlsx': 'BARTIN',
        'BALIKESİR.xlsx': 'BALIKESİR',
        'BURDUR.xlsx': 'BURDUR',
        'KIRIKKALE.xlsx': 'KIRIKKALE',
        'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx': 'İSTANBUL'
    }
    
    multi_hosp_files = ['ADANA.xlsx', 'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx']
    
    # Çok daha esnek anahtar kelimeler
    keywords = ['CUKUROVA', 'SEYHAN', 'SEHIR', 'YUREGIR', 'KOZAN', 'CEYHAN', 'KARAISALI', 'IMAMOGLU', 'KARATAS', 'TUFANBEYLI', 'FEKE', 'SAIMBEYLI', 'ALADAG', 'POZANTI', 'SUREYYAPASA', 'DEVLET', 'EGITIM', 'ADSM', 'AGIZ', 'TIP']

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_count = 0
    
    for filename, city_name in problem_files.items():
        path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', filename)
        if not os.path.exists(path): continue
            
        print(f"--- ABSOLUTE MEGA FIX: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        current_hosp_name = None
        if filename not in multi_hosp_files:
            current_hosp_name = f"{city_name} İL SAĞLIK MÜDÜRLÜĞÜ"

        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row if c is not None]
            if not any(cells): continue
            
            val0 = cells[0]
            val0_slug = slugify(val0)
            
            # 1. HASTANE TESPİTİ
            is_new = False
            
            # Pattern A: Label based (L7 Istanbul)
            if any(label in val0.upper() for label in ['KURUM ADI', 'HASTANE ADI', 'TESİS ADI']):
                if len(cells) > 1 and len(cells[1]) > 5:
                    current_hosp_name = cells[1].upper()
                    print(f"  L{i+1} NEW (Label): {current_hosp_name}")
                    is_new = True
            
            # Pattern B: Keyword based (Adana/Multi-Hosp)
            if not is_new and filename in multi_hosp_files:
                if len(val0) > 10 and ('HASTANE' in val0.upper() or 'MERKEZ' in val0.upper() or 'ADSM' in val0.upper()):
                    # Başlık kelimelerini ele
                    if not any(kw in val0.upper() for kw in ['SAĞLIK BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HEDEF', 'DURUM']):
                        current_hosp_name = val0.upper()
                        print(f"  L{i+1} NEW (Direct): {current_hosp_name}")
                        is_new = True

            if is_new: continue

            # 2. VERİ KAYIT
            if current_hosp_name:
                val = cells[0]
                if len(val) < 5 and len(cells) > 1:
                    val = cells[1]
                
                if len(val) > 15:
                    val_up = val.upper()
                    if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI', 'STRATEJİK']):
                        continue
                    if val_up in current_hosp_name:
                         continue

                    cur.execute("""
                        INSERT INTO gelisim_planlari (il, hastane_adi, kurum_hedefleri, kaynak_dosya)
                        VALUES (%s, %s, %s, %s)
                    """, (city_name, current_hosp_name, val, filename))
                    city_count += 1

        print(f"  -> {city_count} kayıt eklendi.")
        total_count += city_count
        wb.close()

    conn.commit()
    print(f"\nİŞLEM BAŞARIYLA TAMAMLANDI. TOPLAM: {total_count} YÜKLENDİ.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    super_mega_fix_v2()
