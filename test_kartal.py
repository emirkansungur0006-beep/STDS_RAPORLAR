import os
from gozlem_parser import parse_gozlem_xlsx, save_gozlem_records
from reference_matcher import ReferenceMatcher

matcher = ReferenceMatcher()
filepath = r"C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\GÖZLEM FORMLARI\İSTANBUL\T.C. SAĞLIK BAKANLIĞI KARTAL AĞIZ VE DİŞ SAĞLIĞI MERKEZİ.xlsx"

print(f"Parsing {filepath}...")
records = parse_gozlem_xlsx(filepath, "İSTANBUL", matcher)
print(f"Parsed {len(records)} records.")

if records:
    print("Testing save_gozlem_records...")
    try:
        saved = save_gozlem_records(records)
        print(f"Saved: {saved} records")
    except Exception as e:
        import traceback
        traceback.print_exc()
