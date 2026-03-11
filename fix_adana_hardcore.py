# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR

def fix_adana_hardcore():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    # Adana'daki hastane isimlerini direkt buraya yazalım (Dosyadan okunanlar)
    # L7: ADANA ŞEHİR EĞİTİM VE ARAŞTIRMA HASTANESİ
    # L261: Adana Seyhan Devlet Hastanesi
    # L1540: Çukurova Devlet Hastanesi (Öngörü)
    
    current_hosp = None
    count = 0
    
    print(f"Scanning {ws.title}...")
    for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells): continue
        
        # 1. Hastane Tespiti (Adana dosyasının spesifik formatı)
        # Genellikle ilk hücre isim, ikinci hücre adres olur.
        if len(cells) > 1 and len(cells[0]) > 10 and len(cells[1]) > 10:
            c0_up = cells[0].upper()
            c1_up = cells[1].upper()
            # Eğer ilk hücrede HASTANE/MERKEZ geçiyorsa VE ikinci hücrede mahalle/bulvar gibi adres varsa
            if ('HASTANE' in c0_up or 'MERKEZ' in c0_up or 'ADSM' in c0_up) and \
               ('MAH' in c1_up or 'BULV' in c1_up or 'CAD' in c1_up or 'SÜMER' in c1_up or 'HACI' in c1_up):
                current_hosp = cells[0].upper()
                print(f"L{i+1} FOUND HOSP: {current_hosp}")
                continue

        # 2. Veri Kaydı
        if current_hosp and len(cells) > 0:
            val = cells[0]
            if len(val) > 20: # Uzun cümleler veri olabilir
                val_up = val.upper()
                # Başlıkları atla
                if any(kw in val_up for kw in ['HEDEF', 'DURUM', 'GELİŞİM PLANI', 'STRATEJİK', 'BAKANLIĞI']):
                    continue
                if val_up in current_hosp:
                    continue
                
                # Insert
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
    fix_adana_hardcore()
