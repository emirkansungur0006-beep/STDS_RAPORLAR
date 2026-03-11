# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher

def fix_adana_reference_based():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    matcher = ReferenceMatcher()
    
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active # Adana (2)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    current_hosp_name = None
    current_hosp_code = None
    count = 0
    
    print(f"Scanning {ws.title} with Reference Matching...")
    
    for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
        val = str(row[0]).strip() if row[0] is not None else ""
        if not val: continue
        
        # 1. HASTANE TESPİTİ (Referans Matched)
        # Sadece ilk hücreye bakıyoruz, threshold'u yüksek tutuyoruz (0.85+)
        match = matcher.match_by_name(val, il='ADANA', threshold=0.85)
        
        if match and ('HASTANE' in val.upper() or 'MERKEZ' in val.upper() or 'ADSM' in val.upper()):
            # Adana özel: 'ADANA SEYHAN DEVLET HASTANESİ' gibi tam isimler
            current_hosp_name = match['kurum_adi']
            current_hosp_code = match['kurum_kodu']
            print(f"L{i+1} MATCHED: {current_hosp_name}")
            continue

        # 2. VERİ SATIRI
        if current_hosp_name:
            # Satırın bir başlık veya hastane isminin kendisi olmadığını kontrol et
            val_up = val.upper()
            if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'HASTANE ADI']):
                continue
            
            # Eğer val_up hastanenin içindeki bir kelimeyse ama sadece oysa (tekrar), atla
            if val_up in current_hosp_name.upper():
                 continue
                 
            # Anlamlı uzunluktaki verileri kaydet
            if len(val) > 15:
                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('ADANA', current_hosp_name, current_hosp_code, val, 'ADANA.xlsx'))
                count += 1

    conn.commit()
    print(f"DONE: {count} records for Adana.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana_reference_based()
