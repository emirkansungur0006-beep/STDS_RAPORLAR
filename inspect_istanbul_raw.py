import openpyxl
path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\ISTANBUL_KHHB-5_2026_YILI_HASTANE GELISIM_PLANLARI (ALT ALTA ŞEKLİNDE).xlsx'
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws = wb.active
print(f"--- ISTANBUL RAW (First 50 Rows) ---")
for i, row in enumerate(ws.iter_rows(values_only=True, max_row=50)):
    print(f"L{i+1}: {row}")
wb.close()
