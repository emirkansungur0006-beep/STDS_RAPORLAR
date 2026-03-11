import openpyxl
path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\ADANA.xlsx'
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws = wb.active
print(f"Scanning for hospital names in Cell 0...")
for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
    if row[0] and 'HASTANE' in str(row[0]).upper():
        print(f"L{i+1}: {row[0]}")
wb.close()
