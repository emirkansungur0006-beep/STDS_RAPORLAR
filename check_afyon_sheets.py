import openpyxl
path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\AFYONKARAHİSAR.xlsx'
wb = openpyxl.load_workbook(path, read_only=True)
print(f"AFYON SHEETS: {wb.sheetnames}")
wb.close()
