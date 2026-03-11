import openpyxl
path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\ADANA.xlsx'
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws = wb.active
print(f"Searching...")
for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5000)):
    row_str = " ".join([str(c) for c in row if c is not None]).upper()
    if 'ADANA ŞEHİR' in row_str or 'SEYHAN' in row_str or 'ÇUKUROVA' in row_str:
        print(f"L{i+1}: {row}")
wb.close()
