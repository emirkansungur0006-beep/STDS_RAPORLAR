import openpyxl
import os
for f in ['BARTIN', 'BURDUR', 'BALIKESİR', 'KIRIKKALE']:
    path = rf'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\{f}.xlsx'
    if os.path.exists(path):
        wb = openpyxl.load_workbook(path, read_only=True)
        print(f"{f} SHEETS: {wb.sheetnames}")
        wb.close()
