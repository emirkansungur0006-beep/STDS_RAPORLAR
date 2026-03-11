# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def final_mega_fix():
    problem_files = {
        'ADANA.xlsx': 'ADANA',
        'AFYONKARAHİSAR.xlsx': 'AFYONKARAHİSAR',
        'BARTIN.xlsx': 'BARTIN',
        'BALIKESİR.xlsx': 'BALIKESİR',
        'BURDUR.xlsx': 'BURDUR',
        'KIRIKKALE.xlsx': 'KIRIKKALE',
        'ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx': 'İSTANBUL'
    }
    
    # Adana ve benzeri dosyalar için manuel tetikleyiciler
    hardcoded_hospitals = [
        'ÇUKUROVA DEVLET HASTANESİ', 'SEYHAN DEVLET HASTANESİ', 'ADANA ŞEHİR',
        'YÜREĞİR DEVLET', 'KOZAN DEVLET', 'CEYHAN DEVLET', 'KARAİSALI DEVLET',
        'İMAMOĞLU DEVLET', 'KARATAŞ DEVLET', 'TUFANBEYLİ DEVLET', 'FEKE İLÇE',
        'SAİMBEYLİ İLÇE', 'ALADAĞ İLÇE', 'POZANTI 80.YIL', 'SÜREYYAPAŞA',
        'AFYONKARAHİSAR DEVLET', 'BARTIN DEVLET', 'BALIKESİR ŞEHİR', 'BURDUR DEVLET',
        'KIRIKKALE YÜKSEK İHTİSAS'
    ]

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_count = 0
    
    for filename, city_name in problem_files.items():
        path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', filename)
        if not os.path.exists(path): continue
            
        print(f"--- MEGA FIX: {city_name} ---")
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        
        cur.execute("DELETE FROM gelisim_planlari WHERE il = %s", (city_name,))
        
        current_hosp_name = None
        city_count = 0
        
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
            cells = [str(c).strip() if c is not None else "" for c in row if c is not None]
            if not any(cells): continue
            
            val0 = cells[0].upper()
            
            # STRATEJİ 1: "KURUM ADI:" vb. Etiketler
            is_new = False
            if any(label in val0 for label in ['KURUM ADI', 'HASTANE ADI', 'TESİS ADI', 'KURUM KODU']):
                if len(cells) > 1 and len(cells[1]) > 5:
                    current_hosp_name = cells[1].upper()
                    print(f"  L{i+1} NEW (Label): {current_hosp_name}")
                    is_new = True
            
            # STRATEJİ 2: Hücrede hastane ismi direkt geçiyorsa (Hardcoded listeye göre)
            if not is_new:
                for hh in hardcoded_hospitals:
                    if hh in val0:
                        current_hosp_name = val0
                        print(f"  L{i+1} NEW (Hardcoded Match): {current_hosp_name}")
                        is_new = True
                        break
            
            if is_new: continue

            # STRATEJİ 3: Veri Kaydı
            if current_hosp_name and len(cells[0]) > 20:
                val = cells[0]
                val_up = val.upper()
                if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI', 'STRATEJİK']):
                    continue
                if val_up == current_hosp_name:
                    continue

                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s)
                """, (city_name, current_hosp_name, val, filename))
                city_count += 1

        print(f"  -> {city_count} kayıt.")
        total_count += city_count
        wb.close()

    conn.commit()
    print(f"\nMİSYON TAMAMLANDI. TOPLAM: {total_count}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    final_mega_fix()
