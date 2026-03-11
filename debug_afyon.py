import os
import openpyxl
from gelisim_parser import GelisimParser, GELISIM_DIR

def debug_afyon():
    parser = GelisimParser()
    filepath = os.path.join(GELISIM_DIR, 'AFYONKARAHİSAR.xlsx')
    print(f"File: {filepath}")
    
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    print(f"Sheet: {ws.title}")
    
    current_hosp = None
    header_map = None
    il_name = "AFYONKARAHİSAR"
    il_name_for_match = il_name
    recs = 0
    
    rows = list(ws.iter_rows(values_only=True, max_row=50))
    
    for i, row in enumerate(rows):
        if not any(row): continue
        filled_cells = [str(c).strip() for c in row if c is not None and str(c).strip() != '']
        if not filled_cells: continue
        
        row_str = " ".join(filled_cells)
        print(f"Row {i+1}: {' '.join(filled_cells[:2])}...")
        
        # 1. Header Tespiti
        if not header_map:
            matches = {}
            for col_db_name, kw_list in parser.keywords.items():
                for ci, val in enumerate(row):
                    if val and any(kw in str(val).lower() for kw in kw_list):
                        matches[col_db_name] = ci
                        break
            if len(matches) >= 2 and ('kurum_hedefleri' in matches or 'mevcut_durum' in matches):
                header_map = matches
                print(f"  [!] Header Found at Row {i+1}: {header_map}")
                continue

        # 2. Hastane Başlığı Tespiti
        new_hosp = parser.detect_hospital(row, il=il_name_for_match)
        if new_hosp:
            current_hosp = new_hosp
            print(f"  [!] Hospital Detected at Row {i+1}: {current_hosp['kurum_adi']}")
            # header_map = None # Bu satır tehlikeli olabilir mi?
            # continue
        
        # 3. Veri İşleme
        if header_map:
            print(f"  [+] Data Row Check at Row {i+1} (Filled: {len(filled_cells)})")
            # Simulating record check
            h_idx = header_map.get('kurum_hedefleri')
            if h_idx is not None and h_idx < len(row):
                rec_val = clean_text_local(row[h_idx])
                if rec_val and len(str(rec_val)) >= 5:
                    hosp_name = current_hosp['kurum_adi'] if current_hosp else "NONE"
                    print(f"    [OK] Captured Record for {hosp_name}: {str(rec_val)[:30]}...")
                    recs += 1
                else:
                    print(f"    [SKIP] Content too short or None: {rec_val}")
            else:
                print(f"    [FAIL] Index {h_idx} missing in row of length {len(row)}")
    
    print(f"\nTOTAL RECORDS FOUND: {recs}")

def clean_text_local(text):
    import re
    if text is None: return None
    t = str(text).strip()
    if t.lower() == 'none' or t == '': return None
    t = t.replace('_x000D_', ' ')
    t = re.sub(r'\s+', ' ', t)
    return t

if __name__ == "__main__":
    debug_afyon()
