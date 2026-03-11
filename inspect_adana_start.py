import openpyxl
import os

path = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\Gelişim_Planı_İller\ADANA.xlsx'

def inspect_adana_start():
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    # İlk 50 satırı görelim
    for i, row in enumerate(ws.iter_rows(values_only=True, min_row=1, max_row=50)):
        print(f"L{i+1}: {row}")
    wb.close()

if __name__ == "__main__":
    inspect_adana_start()
