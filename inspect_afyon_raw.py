import openpyxl
path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\AFYONKARAHİSAR.xlsx'
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws = wb.active
print(f"--- AFYON RAW ---")
for i, row in enumerate(ws.iter_rows(values_only=True, max_row=50)):
    print(f"L{i+1}: {row}")
wb.close()
