# -*- coding: utf-8 -*-
import os
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher

def fix_adana():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    matcher = ReferenceMatcher()
    
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Sadece Adana'yı temizle
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    current_hosp = None
    header_map = None
    keywords = {
        'kurum_hedefleri': ['hedef', 'kurum hedefleri'],
        'gerceklesme_suresi': ['süre', 'sure'],
        'mevcut_durum': ['mevcut durum', 'tespit'],
        'cozum_secenekleri': ['çözüm', 'cozum'],
        'etki_analizi': ['etki analizi'],
        'uygun_secenek': ['uygun', 'secenek'],
        'isbirligi_plani': ['işbirliği', 'isbirligi'],
        'uygulama_takvimi': ['takvim']
    }

    count = 0
    for row in ws.iter_rows(values_only=True, max_row=5000):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells): continue
        
        # Hastane tespiti (İlk hücrede hastane adı varsa ve yanında Adana adresi varsa)
        if len(cells) > 1 and len(cells[0]) > 10:
            m = matcher.match_by_name(cells[0], il='ADANA', threshold=0.7)
            if m:
                current_hosp = m
                header_map = None
                continue

        # Header tespiti
        if not header_map:
            matches = {}
            for col, kws in keywords.items():
                for ci, val in enumerate(cells):
                    if any(kw in val.lower() for kw in kws):
                        matches[col] = ci
                        break
            if len(matches) >= 2:
                header_map = matches
                continue
        
        # Veri kaydı
        if header_map and current_hosp:
            hedef = cells[header_map['kurum_hedefleri']] if header_map['kurum_hedefleri'] < len(cells) else None
            if hedef and len(hedef) > 5:
                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, mevcut_durum, kaynak_dosya)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('ADANA', current_hosp['kurum_adi'], current_hosp['kurum_kodu'], hedef, cells[header_map['mevcut_durum']], 'ADANA.xlsx'))
                count += 1

    conn.commit()
    print(f"ADANA TAMAMLANDI: {count} kayıt eklendi.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana()
