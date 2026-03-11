# -*- coding: utf-8 -*-
"""
Hastane Görselleri Parser'ı
RAPORLAR\\GÖZLEM FORMLARI\\İL GÖRSELLERİ klasörü altındaki 
hastane isimleriyle adlandırılmış klasörleri tarar ve içindeki PNG'leri veritabanına ekler.
"""
import os
import psycopg2
from config import DB_CONFIG

import unicodedata
import re

BASE_DIR = r'C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\GÖZLEM FORMLARI\İL GÖRSELLERİ'

def normalize_name(name):
    """Kusursuz Normalizasyon: Türkçe ve tüm aksanlı karakterleri ASCII karşılıklarına indirger."""
    if not name: return ""
    s_nfd = unicodedata.normalize('NFD', str(name))
    s_clean = "".join(c for c in s_nfd if unicodedata.category(c) != 'Mn')
    s_clean = re.sub(r'[.]', '', s_clean)
    return " ".join(s_clean.strip().upper().split())

def parse_gorseller():
    print("=" * 60)
    print("Anti-Gravity Görselleri Veritabanına Aktarılıyor...")
    print("=" * 60)

    if not os.path.exists(BASE_DIR):
        print(f"[HATA] {BASE_DIR} bulunamadı.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Önce eski tüm görselleri siliyoruz (sıfırdan tertemiz haritalandırma)
    # cur.execute("TRUNCATE TABLE gozlem_gorselleri RESTART IDENTITY")
    conn.commit()

    # İl bulabilmek için hastane adından ili çeken bir map oluştur
    cur.execute("SELECT DISTINCT hastane_adi, il FROM gozlem_formlari")
    hastane_il_map = {normalize_name(row[0]): row[1] for row in cur.fetchall()}

    komut = """
        INSERT INTO gozlem_gorselleri (il, hastane_adi, dosya_yolu) 
        VALUES (%s, %s, %s)
        ON CONFLICT (dosya_yolu) DO NOTHING
    """
    
    eklenen_sayisi = 0

    # BASE_DIR altındaki elemanlar (hastane adıyla klasör)
    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(folder_path):
            hastane_adi = folder.strip()
            # İli map'ten bulmayı dener (varsa), yoksa None bırakacağız veya aramaya devam
            il = hastane_il_map.get(normalize_name(hastane_adi))
            if not il:
                cur.execute("SELECT DISTINCT il FROM referans_hastaneler WHERE upper(kurum_adi) = %s", (hastane_adi.upper(),))
                res = cur.fetchone()
                il = res[0] if res else 'BİLİNMİYOR'
            
            # Klasör içindeki resimleri bul
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # Dosyanın Base_dir e göre relative pathini al
                        dosya_yolu = os.path.relpath(os.path.join(root, file), start=BASE_DIR)
                        
                        try:
                            cur.execute(komut, (il, hastane_adi, dosya_yolu))
                            if cur.rowcount > 0:
                                eklenen_sayisi += 1
                        except psycopg2.Error as e:
                            print(f"[HATA] {dosya_yolu} eklenemedi: {e}")
                            conn.rollback()
                        else:
                            conn.commit()

    print(f"\n[TAMAM] Toplam {eklenen_sayisi} hastane görseli sisteme işlendi.")
    cur.close()
    conn.close()

if __name__ == '__main__':
    parse_gorseller()
