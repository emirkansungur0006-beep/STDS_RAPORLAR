import sys, os
sys.path.append(os.getcwd())
import psycopg2
import openpyxl
from config import DB_CONFIG, BASE_DIR
from reference_matcher import ReferenceMatcher, normalize_turkish

def fix_adana_final_v3():
    path = os.path.join(BASE_DIR, 'RAPORLAR', 'Gelişim_Planı_İller', 'ADANA.xlsx')
    matcher = ReferenceMatcher()
    
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. TEMİZLİK: Sadece Adana'yı ve hatalı Adana-benzeri kayıtları temizle
    print("Temizlik yapılıyor...")
    cur.execute("DELETE FROM gelisim_planlari WHERE il = 'ADANA'")
    
    current_hosp_name = None
    current_hosp_code = None
    count = 0
    
    # Adres belirtileri
    addr_indicators = ['MAH.', 'CAD.', 'BULV', 'YOLU', 'NO:', 'SOK.', 'ADANA', 'SEYHAN', 'YÜREĞİR', 'ÇUKUROVA', 'SARIÇAM']
    
    print("Excel taranıyor...")
    for row in ws.iter_rows(values_only=True, max_row=5000):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells): continue
        
        row_str = " ".join(cells).upper()
        
        # 1. HASTANE TESPİTİ
        # Pattern: İlk hücre hastane adı, ikinci hücre adres (Adana dosyasındaki durum)
        found_new = False
        if len(cells) > 1:
            name_candidate = cells[0]
            addr_candidate = cells[1].upper()
            
            # Eğer ilk hücrede 'HASTANE', 'MERKEZ', 'ADSM' geçiyorsa VE ikinci hücre adres gibi görünüyorsa
            if len(name_candidate) > 10 and any(kw in addr_candidate for kw in addr_indicators):
                m = matcher.match_by_name(name_candidate, il='ADANA', threshold=0.7)
                if m:
                    current_hosp_name = m['kurum_adi']
                    current_hosp_code = m['kurum_kodu']
                    # print(f"[{count}] YENİ HASTANE: {current_hosp_name}")
                    found_new = True
        
        if found_new: continue

        # 2. VERİ KAYIT
        if current_hosp_name:
            # İlk sütundaki veriyi al
            val = cells[0]
            if len(val) > 15: # Anlamlı bir hedef cümlesi mi?
                val_upper = val.upper()
                # Başlıkları veya hastane isminin tekrarını atla
                if any(kw in val_upper for kw in ['SAĞLIK BAKANLIĞI', 'HASTANE ADI', 'HEDEF', 'DURUM', 'GELİŞİM PLANI', 'STRATEJİK']):
                    continue
                if val_upper in current_hosp_name.upper():
                    continue
                
                # ADANA'da bazı satırlarda "Lütfen..." gibi uyarılar var, onları atla
                if val_upper.startswith('LÜTFEN') or val_upper.startswith('NOT:'):
                    continue

                cur.execute("""
                    INSERT INTO gelisim_planlari (il, hastane_adi, kurum_kodu, kurum_hedefleri, kaynak_dosya, sheet_adi)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('ADANA', current_hosp_name, current_hosp_code, val, 'ADANA.xlsx', ws.title))
                count += 1

    conn.commit()
    print(f"BİTTİ: ADANA için {count} geçerli kayıt eklendi.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_adana_final_v3()
