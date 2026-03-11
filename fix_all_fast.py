# -*- coding: utf-8 -*-
"""
HIZLI VERİ DÜZELTMESİ - Direkt SQL ile tüm sorunları giderir.
Yavaş fuzzy matching KULLANILMAZ.
"""
import sys, os
sys.path.append(os.getcwd())
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# ============================================================
# ADIM 1: Hatalı İl İsimlerini Düzelt
# ============================================================
il_fixes = {
    'SAMSUNKÜTAHYA': None,  # Bu dosyada SAMSUN ve KÜTAHYA birleşmiş, sheet bazlı ayıracağız
    'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN': None,  # Birden fazla il
    'EXCEL': None,          # Excel_Yapi_Onizleme.xlsx - gereksiz
    'GİRESUNN': 'GİRESUN',
    'KOACAELİ': 'KOCAELİ',
    'ÇORUM..': 'ÇORUM',
    '81HYA': None,
    'ISTANBUL': 'İSTANBUL',
}

print("ADIM 1: Hatalı İl İsimleri Düzeltiliyor...")
for bad_il, good_il in il_fixes.items():
    if good_il:
        cur.execute("UPDATE gelisim_planlari SET il = %s WHERE il = %s", (good_il, bad_il))
        print(f"  ✓ '{bad_il}' → '{good_il}' ({cur.rowcount} kayıt)")
    else:
        # Gereksiz/karmaşık il adları - Kaynak dosyayı kontrol et
        cur.execute("SELECT COUNT(*) FROM gelisim_planlari WHERE il = %s", (bad_il,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f"  ! '{bad_il}' - {cnt} kayıt var, sheet bazlı düzeltilecek")

# SAMSUNKÜTAHYA - Sheet adına göre ayır
cur.execute("""
    SELECT DISTINCT sheet_adi FROM gelisim_planlari WHERE il = 'SAMSUNKÜTAHYA'
""")
sheets = [r[0] for r in cur.fetchall()]
for sheet in sheets:
    s_upper = (sheet or '').upper()
    if 'SAMSUN' in s_upper or 'SAM' in s_upper:
        cur.execute("UPDATE gelisim_planlari SET il = 'SAMSUN' WHERE il = 'SAMSUNKÜTAHYA' AND sheet_adi = %s", (sheet,))
        print(f"  ✓ SAMSUNKÜTAHYA/{sheet} → SAMSUN ({cur.rowcount})")
    else:
        cur.execute("UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = 'SAMSUNKÜTAHYA' AND sheet_adi = %s", (sheet,))
        print(f"  ✓ SAMSUNKÜTAHYA/{sheet} → KÜTAHYA ({cur.rowcount})")

# Kalan SAMSUNKÜTAHYA'ları KÜTAHYA yap
cur.execute("UPDATE gelisim_planlari SET il = 'KÜTAHYA' WHERE il = 'SAMSUNKÜTAHYA'")
if cur.rowcount > 0: print(f"  ✓ Kalan SAMSUNKÜTAHYA → KÜTAHYA ({cur.rowcount})")

# ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN - Sheet bazlı ayır
cur.execute("""
    SELECT DISTINCT sheet_adi FROM gelisim_planlari WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN'
""")
multi_sheets = [r[0] for r in cur.fetchall()]
multi_il_map = {
    'ERZURUM': ['ERZURUM', 'ERZ'],
    'HAKKARİ': ['HAKKARİ', 'HAKK', 'HAKKARI'],
    'İZMİR': ['İZMİR', 'IZMIR'],
    'KÜTAHYA': ['KÜTAHYA', 'KUTAHYA', 'KÜYAHYA'],
    'SAMSUN': ['SAMSUN', 'SAM'],
}
for sheet in multi_sheets:
    s_upper = (sheet or '').upper()
    found = False
    for il_name, keywords in multi_il_map.items():
        if any(kw in s_upper for kw in keywords):
            cur.execute("UPDATE gelisim_planlari SET il = %s WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND sheet_adi = %s", (il_name, sheet))
            print(f"  ✓ Multi/{sheet} → {il_name} ({cur.rowcount})")
            found = True
            break
    if not found:
        cur.execute("UPDATE gelisim_planlari SET il = 'ERZURUM' WHERE il = 'ERZURUM HAKKARİ İZMİR KÜYAHYA SAMSUN' AND sheet_adi = %s", (sheet,))
        print(f"  ✓ Multi/{sheet} → ERZURUM (varsayılan) ({cur.rowcount})")

# EXCEL - gereksiz dosya, sil
cur.execute("DELETE FROM gelisim_planlari WHERE il = 'EXCEL'")
print(f"  ✗ 'EXCEL' verisi silindi ({cur.rowcount})")

# İSTANBUL KHB ve İSTANBUL KHHB - hepsini İSTANBUL yap
cur.execute("UPDATE gelisim_planlari SET il = 'İSTANBUL' WHERE il IN ('İSTANBUL KHB', 'İSTANBUL KHHB')")
print(f"  ✓ İSTANBUL KHB/KHHB → İSTANBUL ({cur.rowcount})")

conn.commit()

# ============================================================
# ADIM 2: 'İL - SAYFA' formatındaki tesis adlarını düzelt
# ============================================================
print("\nADIM 2: Hatalı Tesis Adları Düzeltiliyor...")

# Sheet adını doğrudan tesis adı olarak kullan (temizleyerek)
cur.execute("""
    SELECT DISTINCT il, hastane_adi, sheet_adi 
    FROM gelisim_planlari 
    WHERE hastane_adi LIKE '%% - %%' 
       OR hastane_adi LIKE '%%BİLİNMEYEN%%'
       OR hastane_adi LIKE '%%SAĞLIK TESİSİ%%'
    ORDER BY il
""")
bad_rows = cur.fetchall()
print(f"  {len(bad_rows)} hatalı tesis adı bulundu.")

for il, bad_name, sheet_adi in bad_rows:
    # Sheet adını temizle ve tesis adı yap
    if not sheet_adi or len(sheet_adi.strip()) < 3:
        new_name = f"{il} İl Sağlık Müdürlüğü"
    elif sheet_adi.upper().startswith('SAYFA') or sheet_adi.upper().startswith('SHEET'):
        new_name = f"{il} İl Sağlık Müdürlüğü"
    else:
        # Sheet adını büyük harfle temizle
        clean = sheet_adi.strip()
        # Başındaki il adını kaldır
        upper_clean = clean.upper()
        if upper_clean.startswith(il):
            clean = clean[len(il):].strip()
            if clean.startswith('-') or clean.startswith('_'):
                clean = clean[1:].strip()
        if len(clean) < 3:
            new_name = f"{il} İl Sağlık Müdürlüğü" 
        else:
            new_name = clean.upper()
    
    cur.execute("""
        UPDATE gelisim_planlari 
        SET hastane_adi = %s
        WHERE il = %s AND hastane_adi = %s AND sheet_adi = %s
    """, (new_name, il, bad_name, sheet_adi))

conn.commit()

# ============================================================
# ADIM 3: Sonuç Raporu
# ============================================================
print("\n" + "="*60)
cur.execute("SELECT COUNT(*) FROM gelisim_planlari")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT il) FROM gelisim_planlari")
total_il = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari")
total_hosp = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gelisim_planlari WHERE hastane_adi LIKE '%% - %%' OR hastane_adi LIKE '%%BİLİNMEYEN%%'")
still_bad = cur.fetchone()[0]

print(f"TOPLAM KAYIT: {total}")
print(f"TOPLAM İL: {total_il}")
print(f"TOPLAM TESİS: {total_hosp}")
print(f"HALA SORUNLU: {still_bad}")

print("\nİL DAĞILIMI:")
cur.execute("SELECT il, COUNT(*), COUNT(DISTINCT hastane_adi) FROM gelisim_planlari GROUP BY il ORDER BY il")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} kayıt, {r[2]} tesis")

print("="*60)
cur.close()
conn.close()
