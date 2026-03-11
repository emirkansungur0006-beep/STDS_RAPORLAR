# -*- coding: utf-8 -*-
import os
import sqlite3
import unicodedata
import re

BASE_DIR = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR'
DB_PATH = os.path.join(BASE_DIR, 'stds.db')
GORSELLER_BASE_DIR = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\GÖZLEM FORMLARI\İL GÖRSELLERİ'

def normalize_name(name):
    if not name: return ""
    s_nfd = unicodedata.normalize('NFD', str(name))
    s_clean = "".join(c for c in s_nfd if unicodedata.category(c) != 'Mn')
    s_clean = re.sub(r'[.]', '', s_clean)
    return " ".join(s_clean.strip().upper().split())

def fix_gorseller():
    print("Görseller veritabanına yeniden işleniyor...")
    
    if not os.path.exists(GORSELLER_BASE_DIR):
        print(f"HATA: {GORSELLER_BASE_DIR} bulunamadı!")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Mevcutları sil
    cur.execute("DELETE FROM gozlem_gorselleri")
    conn.commit()

    # İl haritası oluştur
    cur.execute("SELECT DISTINCT hastane_adi, il FROM gozlem_formlari")
    hastane_il_map = {row[0]: row[1] for row in cur.fetchall() if row[0]}

    count = 0
    for folder in os.listdir(GORSELLER_BASE_DIR):
        folder_path = os.path.join(GORSELLER_BASE_DIR, folder)
        if os.path.isdir(folder_path):
            hastane_adi = folder.strip()
            il = hastane_il_map.get(hastane_adi, 'BİLİNMİYOR')
            
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # Relative path
                        dosya_yolu = os.path.relpath(os.path.join(root, file), start=GORSELLER_BASE_DIR)
                        
                        cur.execute("""
                            INSERT INTO gozlem_gorselleri (il, hastane_adi, dosya_yolu)
                            VALUES (?, ?, ?)
                        """, (il, hastane_adi, dosya_yolu))
                        count += 1
            
    conn.commit()
    conn.close()
    print(f"BİTTİ: {count} görsel başarıyla eklendi.")

if __name__ == '__main__':
    fix_gorseller()
