import os
import openpyxl
from reference_matcher import ReferenceMatcher, normalize_turkish
from gelisim_parser import GelisimParser, GELISIM_DIR

def deep_debug():
    p = GelisimParser()
    f = os.path.join(GELISIM_DIR, 'AFYONKARAHİSAR.xlsx')
    wb = openpyxl.load_workbook(f, read_only=True)
    ws = wb.active
    print(f"File: {f}")
    print(f"Sheet: {ws.title}")
    
    h_map = None
    h_curr = None
    recs = 0
    
    for i, row in enumerate(ws.iter_rows(values_only=True, max_row=50)):
        if not any(row): continue
        filled = [str(c).strip() for c in row if c is not None and str(c).strip() != '']
        if not filled: continue
        
        # Hospital check first
        new_h = p.detect_hospital(row, 'AFYONKARAHİSAR')
        if new_h:
            h_curr = new_h
            print(f"Row {i+1}: Hosp found -> {h_curr['kurum_adi']}")
        
        # Header check
        if not h_map:
            matches = {}
            row_norm = [normalize_turkish(str(c)) if c else '' for c in row]
            for col, kw_list in p.keywords.items():
                for ci, val in enumerate(row_norm):
                    if any(kw == val or kw in val for kw in kw_list):
                        matches[col] = ci
                        break
            if len(matches) >= 2 and ('kurum_hedefleri' in matches or 'mevcut_durum' in matches):
                h_map = matches
                print(f"Row {i+1}: Header found -> {h_map}")
                continue
        
        if h_map:
            # Check if this row is just a repeat of header or hospital
            if new_h: continue
            
            # Check if it's a data row
            val = row[h_map['kurum_hedefleri']] if h_map['kurum_hedefleri'] < len(row) else None
            if val and len(str(val)) > 5:
                recs += 1
                print(f"Row {i+1}: Record found (Total: {recs})")
    
    print(f"FINAL COUNT for sheet {ws.title}: {recs}")

if __name__ == "__main__":
    deep_debug()
