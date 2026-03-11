# -*- coding: utf-8 -*-
"""
STDS Raporlar - Master Güncelleme Sistemi
Tüm verileri Excel'den okuyan ve SQLite veritabanını güncelleyen ana script.
"""
import os
import subprocess
import time
from init_sqlite import init_sqlite
from config import GÖZLEM_GÖRSELLER_DIR, SQLITE_DB_PATH
import sqlite3

def run_script(script_name):
    print(f"\n--- Çalıştırılıyor: {script_name} ---")
    try:
        # Python scriptini çalıştır
        result = subprocess.run(['python', script_name], capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print(f"[OK] {script_name} başarıyla tamamlandı.")
        else:
            print(f"[HATA] {script_name} hata verdi:")
            print(result.stderr)
    except Exception as e:
        print(f"[ERROR] {script_name} çalıştırılamadı: {e}")

def sync_images():
    print("\n--- Görseller Veritabanı ile Senkronize Ediliyor ---")
    if not os.path.exists(GÖZLEM_GÖRSELLER_DIR):
        print(f"[UYARI] Görsel klasörü bulunamadı: {GÖZLEM_GÖRSELLER_DIR}")
        return

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    
    # Mevcut görselleri temizle (tekrar eklemeyi önlemek için)
    cur.execute("DELETE FROM gozlem_gorselleri")
    
    count = 0
    # Klasör yapısı: Hastane Adi / PNG
    # Not: Bazı yerlerde IL/Hastane/PNG olabilir ama mevcut yapı doğrudan Hastane bazlı görünüyor
    for item in os.listdir(GÖZLEM_GÖRSELLER_DIR):
        item_path = os.path.join(GÖZLEM_GÖRSELLER_DIR, item)
        if not os.path.isdir(item_path): continue
        
        # Eğer bu bir hastane klasörü mü yoksa il klasörü mü? 
        # Klasör içinde doğrudan .png varsa hastanedir.
        files = os.listdir(item_path)
        has_png = any(f.lower().endswith('.png') for f in files)
        
        if has_png:
            # Hastane klasörü
            hastane = item
            # Bu hastanenin ilini bulmaya çalış
            cur.execute("SELECT il FROM gozlem_formlari WHERE hastane_adi LIKE ? LIMIT 1", (f"%{hastane}%",))
            row = cur.fetchone()
            il = row[0] if row else "BİLİNMİYOR"
            
            for f in files:
                if f.lower().endswith('.png'):
                    rel_path = f"{hastane}/{f}"
                    cur.execute("""
                        INSERT INTO gozlem_gorselleri (il, hastane_adi, dosya_yolu)
                        VALUES (?, ?, ?)
                    """, (il, hastane, rel_path))
                    count += 1
        else:
            # Belki IL/Hastane yapısıdır (Gelecekteki düzen için destek)
            for subitem in files:
                subitem_path = os.path.join(item_path, subitem)
                if os.path.isdir(subitem_path):
                    subfiles = os.listdir(subitem_path)
                    if any(sf.lower().endswith('.png') for sf in subfiles):
                        il = item
                        hastane = subitem
                        for sf in subfiles:
                            if sf.lower().endswith('.png'):
                                rel_path = f"{il}/{hastane}/{sf}"
                                cur.execute("""
                                    INSERT INTO gozlem_gorselleri (il, hastane_adi, dosya_yolu)
                                    VALUES (?, ?, ?)
                                """, (il, hastane, rel_path))
                                count += 1
    
    conn.commit()
    conn.close()
    print(f"[OK] {count} adet görsel sisteme tanıtıldı.")

def main():
    print("="*60)
    print("STDS RAPORLAR - MEKANİK GÜNCELLEME SİSTEMİ")
    print("="*60)
    start_time = time.time()

    # 1. Veritabanını sıfırla
    init_sqlite()

    # 2. Parsers - Sırasıyla çalıştır
    # Not: Bu scriptlerin SQLite desteği için app.py'deki get_db mantığını kullanması gerekir.
    # Mevcut scriptler doğrudan psycopg2 kullanıyor olabilir, bu yüzden onları da kontrol etmeliyim.
    # Ancak şimdilik ana akışı kuruyoruz.
    
    scripts = [
        'run_komite_hizli.py', # Komite raporları
        'gelisim_parser.py',   # Gelişim planları
        'gozlem_parser.py'     # Gözlem formları (Eğer varsa)
    ]
    
    for script in scripts:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f"[UYARI] {script} bulunamadı, atlanıyor.")

    # 3. Görselleri tara
    sync_images()

    end_time = time.time()
    print("\n" + "="*60)
    print(f"GÜNCELLEME TAMAMLANDI! (Süre: {end_time - start_time:.2f} sn)")
    print(f"Veritabanı: {SQLITE_DB_PATH}")
    print("="*60)

if __name__ == "__main__":
    main()
