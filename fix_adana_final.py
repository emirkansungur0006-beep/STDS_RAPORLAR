# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher

def fix_adana_final():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    matcher = ReferenceMatcher()
    
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    current_hosp_name = None
    current_hosp_code = None
    count = 0
    
    addr_keywords = ['MAH.', 'CAD.', 'BULV', 'YOLU', 'NO:', 'SOK.', 'ADANA']
    
    for row in ws.iter_rows(values_only=True, max_row=5000):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells): continue
        
        # 1. KESİN HASTANE TESPİTİ (Adres içeren satırlar)
        if len(cells) > 1:
            name_candidate = cells[0]
            addr_candidate = cells[1].upper()
            
            # Eğer ilk hücre uzunsa ve ikinci hücre adres kelimeleri içeriyorsa
            if len(name_candidate) > 10 and any(kw in addr_candidate for kw in addr_keywords):
                # Matcher ile doğrula
                m = matcher.match_by_name(name_candidate, il='ADANA', threshold=0.7)
                if m:
                    current_hosp_name = m['kurum_adi']
                    current_hosp_code = m['kurum_kodu']
                    # print(f"Bulunan Hastane: {current_hosp_name}")
                    continue

        # 2. VERİ SATIRI (Ancak geçerli bir hastane bloğundaysak)
        if current_hosp_name and len(cells) > 0:
            val = cells[0]
            # Hedef metni genellikle uzun olur ve başlık kelimelerini içermez
            if len(val) > 10:
                # Satırın bir başlık (Header) olmadığını kontrol et
                val_upper = val.upper()
                if any(kw in val_upper for kw in ['SAĞLIK BAKANLIĞI', 'HASTANE ADI', 'HEDEF', 'DURUM', 'GELİŞİM PLANI']):
                    continue
                
                # Eğer val_upper hastane adının kendisiyse (tekrar satırı), atla
                if val_upper in current_hosp_name.upper():
                    continue

                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, kaynak_dosya)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('ADANA', current_hosp_name, current_hosp_code, val, 'ADANA.xlsx'))
                count += 1

    conn.commit()
    print(f"ADANA KESİN TAMAMLANDI: {count} kayıt eklendi.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana_final()
