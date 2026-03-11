# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def super_final_mega_fix():
    problem_files = {
        'ADANA.xlsx': 'ADANA',
        'AFYONKARAHİSAR.xlsx': 'AFYONKARAHİSAR',
        'BARTIN.xlsx': 'BARTIN',
        'BALIKESİR.xlsx': 'BALIKESİR',
        'BURDUR.xlsx': 'BURDUR',
        'KIRIKKALE.xlsx': 'KIRIKKALE',
        'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx': 'İSTANBUL'
    }
    
    # Çoklu hastane içeren dosyalar (Vertical Scan gerekir)
    multi_hosp_files = ['ADANA.xlsx', 'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx']
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_count = 0
    
    for filename, city_name in problem_files.items():
        path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', filename)
        if not os.path.exists(path): continue
            
        print(f"--- SUPER MEGA FIX: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        # Fallback Name: Eğer çoklu hastane dosyası değilse en baştan il müdürlüğü set et
        current_hosp_name = None
        if filename not in multi_hosp_files:
            current_hosp_name = f"{city_name} İL SAĞLIK MÜDÜRLÜĞÜ"

        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row if c is not None]
            if not any(cells): continue
            
            val0 = cells[0].upper()
            
            # 1. HASTANE TESPİTİ (Sadece çoklu dosyalarda veya label gördüğümüzde)
            # Label Check (Tüm dosyalar için geçerli)
            is_new_hosp = False
            if any(label in val0 for label in ['KURUM ADI', 'HASTANE ADI', 'TESİS ADI']):
                if len(cells) > 1 and len(cells[1]) > 5:
                    current_hosp_name = cells[1].upper()
                    print(f"  L{i+1} NEW (Label): {current_hosp_name}")
                    is_new_hosp = True
            
            # Adana özel veya Direct Match (Sadece Çoklu Dosyalarda)
            if not is_new_hosp and filename in multi_hosp_files:
                if 'HASTANE' in val0 or 'MERKEZ' in val0 or 'ADSM' in val0:
                    if len(val0) > 10 and 'HEDEF' not in val0 and 'MÜDÜRLÜĞÜ' not in val0:
                        current_hosp_name = val0
                        print(f"  L{i+1} NEW (Direct): {current_hosp_name}")
                        is_new_hosp = True
            
            if is_new_hosp: continue

            # 2. VERİ KAYIT
            if current_hosp_name:
                val = cells[0]
                # Afyon gibi dosyalarda bazen ilk sütunda 1, 2, 3 gibi sayılar olur, veri ikinci sütundadır
                if len(val) < 5 and len(cells) > 1:
                    val = cells[1]
                
                if len(val) > 15: # Anlamlı veri
                    val_up = val.upper()
                    # Başlıkları atla
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
    print(f"\nİŞLEM BAŞARIYLA TAMAMLANDI. TOPLAM: {total_count} YENİ KAYIT.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    super_final_mega_fix()
