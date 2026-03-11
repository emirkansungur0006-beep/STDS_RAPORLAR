# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def fix_adana():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    current_hosp = None
    count = 0
    
    for row in ws.iter_rows(values_only=True, max_row=5000):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells): continue
        
        row_str = " ".join(cells).upper()
        
        # 1. Hastane tespiti (Daha esnek)
        # Örn: "ADANA ŞEHİR HASTANESİ" gibi bir ibare geçiyorsa ve kurum/sağlık/tesis kelimeleri varsa
        if ('HASTANE' in row_str or 'MERKEZ' in row_str or 'ADSM' in row_str) and len(cells[0]) > 10:
            current_hosp = cells[0].upper()
            continue

        # 2. Veri satırı tespiti
        # Eğer bir hastane atanmışsa ve satırda "HEDEF" veya "ANALİZ" kelimeleri GEÇMİYORSA (yani veriyse)
        # ama satırın bir sütunu doluysa
        if current_hosp and len(cells) > 5:
            # Sütunlarda anlamlı veri var mı? (Adana dosyasında genelde 2-3. sütunlar dolu)
            val = cells[0]
            if len(val) > 10 and 'HEDEF' not in val.upper() and 'DEĞERLENDİRME' not in val.upper() and 'LÜTFEN' not in val.upper():
                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s)
                """, ('ADANA', current_hosp, val, 'ADANA.xlsx'))
                count += 1

    conn.commit()
    print(f"ADANA TAMAMLANDI: {count} kayıt eklendi.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana()
