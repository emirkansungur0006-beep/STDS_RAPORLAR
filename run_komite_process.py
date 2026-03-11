# -*- coding: utf-8 -*-
"""
Komite/Komisyon Raporları İşleme Betiği
Detaylı Türkçe ilerleme raporu ile tüm dosyaları yeniden işler.
"""
import os
import sys
import time
import psycopg2
from config import DB_CONFIG, KOMITE_DIR
from reference_matcher import ReferenceMatcher

def format_duration(seconds):
    """Süreyi Türkçe formatla"""
    if seconds < 60:
        return f"{int(seconds)} saniye"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m} dakika {s} saniye"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h} saat {m} dakika"

def main():
    print("=" * 70)
    print("  T.C. SAĞLIK BAKANLIĞI - KOMİTE/KOMİSYON RAPORLARI İŞLEME")
    print("=" * 70)
    print()

    # Klasör kontrol
    if not os.path.exists(KOMITE_DIR):
        print(f"[HATA] Klasör bulunamadı: {KOMITE_DIR}")
        sys.exit(1)

    # Dosyaları listele
    all_entries = sorted(os.listdir(KOMITE_DIR))
    files = [f for f in all_entries if os.path.isfile(os.path.join(KOMITE_DIR, f))]
    
    total_count = len(files)
    
    # Dosya türü analizi
    ext_counts = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
    
    print(f"📁 Kaynak klasör: {KOMITE_DIR}")
    print(f"📊 Toplam dosya sayısı: {total_count}")
    print()
    print("📋 Dosya türü dağılımı:")
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_count) * 100
        print(f"   {ext:8s} → {count:5d} dosya  ({pct:.1f}%)")
    print()
    
    # Tahmini süre hesapla
    # PDF ~3sn/dosya (OCR), DOCX ~0.5sn/dosya, diğer ~0.1sn/dosya
    pdf_count = ext_counts.get('.pdf', 0)
    docx_count = ext_counts.get('.docx', 0)
    other_count = total_count - pdf_count - docx_count
    estimated_seconds = (pdf_count * 3) + (docx_count * 0.5) + (other_count * 0.1)
    
    print(f"⏰ Tahmini işlem süresi: {format_duration(estimated_seconds)}")
    print(f"   (PDF: ~3 sn/dosya, DOCX: ~0.5 sn/dosya, Diğer: ~0.1 sn/dosya)")
    print()
    
    # Veritabanı temizle
    print("🗑️  Mevcut komite verileri temizleniyor...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM komite_raporlari")
    old_count = cur.fetchone()[0]
    cur.execute("DELETE FROM komisyon_kararlari")
    cur.execute("DELETE FROM standart_degerlendirmeler")
    cur.execute("DELETE FROM komite_raporlari")
    conn.commit()
    cur.close()
    conn.close()
    print(f"   ✓ {old_count} eski kayıt silindi.")
    print()
    
    # İşlemeye başla
    print("🚀 İŞLEME BAŞLIYOR...")
    print("-" * 70)
    
    matcher = ReferenceMatcher()
    
    from komisyon_parser import (
        parse_komisyon_docx, parse_komite_pdf, save_komite_rapor
    )
    
    start_time = time.time()
    total_processed = 0
    total_errors = 0
    type_counts = {'docx': 0, 'pdf': 0, 'xlsx': 0, 'doc': 0, 'image': 0, 'other': 0}
    il_counts = {}
    last_report_time = start_time
    
    for idx, filename in enumerate(files):
        filepath = os.path.join(KOMITE_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        file_info = matcher.match_filename(filename)
        il_name = file_info.get('il', 'BİLİNMİYOR') or 'BİLİNMİYOR'
        
        try:
            rapor = None
            standartlar = []
            karar = None
            
            if ext == '.docx':
                rapor, standartlar, karar = parse_komisyon_docx(filepath, file_info, matcher)
                if rapor:
                    save_komite_rapor(rapor, standartlar, karar)
                    type_counts['docx'] += 1
                    
            elif ext == '.pdf':
                rapor, standartlar, karar = parse_komite_pdf(filepath, file_info, matcher)
                if rapor:
                    save_komite_rapor(rapor, standartlar, karar)
                    type_counts['pdf'] += 1
                    
            elif ext in ('.xlsx', '.xls'):
                rapor = {
                    'kurum_kodu': file_info.get('kurum_kodu'),
                    'il': file_info.get('il', ''),
                    'ilce': file_info.get('ilce', ''),
                    'hastane_adi': file_info.get('hastane', '') or f"{file_info.get('il', '')} Sağlık Tesisi",
                    'rapor_tipi': file_info.get('rapor_tipi', 'Komisyon'),
                    'degerlendirme_tarihi': None,
                    'degerlendirme_saati': None,
                    'ekip_uyeleri': '',
                    'kaynak_dosya': filename,
                    'dosya_formati': 'xlsx'
                }
                save_komite_rapor(rapor, [], None)
                type_counts['xlsx'] += 1
                
            elif ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.jfif'):
                rapor = {
                    'kurum_kodu': file_info.get('kurum_kodu'),
                    'il': file_info.get('il', ''),
                    'ilce': file_info.get('ilce', ''),
                    'hastane_adi': file_info.get('hastane', '') or f"{file_info.get('il', '')} Sağlık Tesisi",
                    'rapor_tipi': file_info.get('rapor_tipi', 'Komite'),
                    'degerlendirme_tarihi': None,
                    'degerlendirme_saati': None,
                    'ekip_uyeleri': '',
                    'kaynak_dosya': filename,
                    'dosya_formati': ext.replace('.', '')
                }
                save_komite_rapor(rapor, [], None)
                type_counts['image'] += 1
                
            elif ext == '.doc':
                rapor = {
                    'kurum_kodu': file_info.get('kurum_kodu'),
                    'il': file_info.get('il', ''),
                    'ilce': file_info.get('ilce', ''),
                    'hastane_adi': file_info.get('hastane', '') or f"{file_info.get('il', '')} Sağlık Tesisi",
                    'rapor_tipi': file_info.get('rapor_tipi', 'Komisyon'),
                    'degerlendirme_tarihi': None,
                    'degerlendirme_saati': None,
                    'ekip_uyeleri': '',
                    'kaynak_dosya': filename,
                    'dosya_formati': 'doc'
                }
                save_komite_rapor(rapor, [], None)
                type_counts['doc'] += 1
            else:
                type_counts['other'] += 1
                continue
                
            if rapor:
                total_processed += 1
                rap_il = rapor.get('il', 'BİLİNMİYOR') or 'BİLİNMİYOR'
                il_counts[rap_il] = il_counts.get(rap_il, 0) + 1
                
        except Exception as e:
            total_errors += 1
            if total_errors <= 10:
                print(f"   ⚠️  HATA [{filename}]: {str(e)[:100]}")
        
        # Her 50 dosyada bir ilerleme raporu
        current_num = idx + 1
        now = time.time()
        if current_num % 50 == 0 or current_num == total_count:
            elapsed = now - start_time
            rate = current_num / elapsed if elapsed > 0 else 0
            remaining = (total_count - current_num) / rate if rate > 0 else 0
            pct = (current_num / total_count) * 100
            
            # İlerleme çubuğu
            bar_len = 30
            filled = int(bar_len * current_num / total_count)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            print(f"\n   [{bar}] {pct:.1f}%")
            print(f"   📄 İşlenen: {current_num}/{total_count} | ✅ Başarılı: {total_processed} | ❌ Hata: {total_errors}")
            print(f"   ⏱️  Geçen süre: {format_duration(elapsed)} | Kalan: ~{format_duration(remaining)}")
            print(f"   🏥 Şu anki il: {il_name} | Hız: {rate:.1f} dosya/sn")
            sys.stdout.flush()
    
    # SONUÇ RAPORU
    total_elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    print("  ✅ İŞLEM TAMAMLANDI!")
    print("=" * 70)
    print()
    print(f"📊 GENEL ÖZET:")
    print(f"   Toplam dosya      : {total_count}")
    print(f"   Başarılı işlenen  : {total_processed}")
    print(f"   Hata sayısı       : {total_errors}")
    print(f"   Toplam süre       : {format_duration(total_elapsed)}")
    print()
    print(f"📋 DOSYA TÜRLERİ:")
    print(f"   DOCX  : {type_counts['docx']}")
    print(f"   PDF   : {type_counts['pdf']}")
    print(f"   XLSX  : {type_counts['xlsx']}")
    print(f"   DOC   : {type_counts['doc']}")
    print(f"   Görsel : {type_counts['image']}")
    print(f"   Diğer  : {type_counts['other']}")
    print()
    print(f"🗺️  İL BAZLI DAĞILIM ({len(il_counts)} il):")
    for il, count in sorted(il_counts.items(), key=lambda x: -x[1])[:20]:
        bar_len = min(count // 5, 40)
        bar = '▓' * bar_len
        print(f"   {il:20s} : {count:5d} {bar}")
    if len(il_counts) > 20:
        print(f"   ... ve {len(il_counts) - 20} il daha")
    print()
    print("=" * 70)
    sys.stdout.flush()

if __name__ == '__main__':
    main()
