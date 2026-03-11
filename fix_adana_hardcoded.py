# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def fix_adana_hardcoded():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active # Adana (2)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    # Adana için bilinen hastane anahtarları
    hospitals = {
        'ÇUKUROVA': 'ÇUKUROVA DEVLET HASTANESİ',
        'SEYHAN': 'ADANA SEYHAN DEVLET HASTANESİ',
        'ŞEHİR': 'ADANA ŞEHİR EĞİTİM VE ARAŞTIRMA HASTANESİ',
        'YÜREĞİR': 'ADANA YÜREĞİR DEVLET HASTANESİ',
        'KOZAN': 'ADANA KOZAN DEVLET HASTANESİ',
        'CEYHAN': 'ADANA CEYHAN DEVLET HASTANESİ',
        'KARAİSALI': 'ADANA KARAİSALI DEVLET HASTANESİ',
        'İMAMOĞLU': 'ADANA İMAMOĞLU DEVLET HASTANESİ',
        'KARATAŞ': 'ADANA KARATAŞ DEVLET HASTANESİ',
        'TUFANBEYLİ': 'ADANA TUFANBEYLİ DEVLET HASTANESİ',
        'FEKE': 'ADANA FEKE İLÇE DEVLET HASTANESİ',
        'SAİMBEYLİ': 'ADANA SAİMBEYLİ İLÇE DEVLET HASTANESİ',
        'ALADAĞ': 'ADANA ALADAĞ İLÇE DEVLET HASTANESİ',
        'POZANTI': 'ADANA POZANTI 80.YIL DEVLET HASTANESİ'
    }

    current_hosp = None
    count = 0
    
    print(f"Scanning {ws.title} with Hardcoded Keywords...")
    
    for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
        val = str(row[0]).strip() if row[0] is not None else ""
        if not val: continue
        
        val_up = val.upper()
        
        # 1. Hastane Tespiti
        is_hosp = False
        for kw, full_name in hospitals.items():
            if kw in val_up and ('HASTANE' in val_up or 'MERKEZ' in val_up):
                current_hosp = full_name
                print(f"L{i+1} TRIGGERED: {current_hosp}")
                is_hosp = True
                break
        
        if is_hosp: continue

        # 2. Veri Kaydı
        if current_hosp:
            if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'BAKANLIĞI', 'MÜDÜRLÜĞÜ', 'HASTANE ADI', '2026 YILI']):
                continue
            
            # Anlamlı uzunlukta veri
            if len(val) > 20:
                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s)
                """, ('ADANA', current_hosp, val, 'ADANA.xlsx'))
                count += 1

    conn.commit()
    print(f"DONE: {count} records for Adana.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana_hardcoded()
