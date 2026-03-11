# -*- coding: utf-8 -*-
"""
STDS Raporlar - Komisyon/Komite Rapor Parser
DOCX ve PDF dosyalarını okur, OCR ile tarar ve veritabanına yazar.
"""
import os
import re
import sqlite3
from datetime import datetime, date, time
from config import DB_CONFIG, KOMITE_DIR, USE_SQLITE
from app import get_db, get_placeholder
from reference_matcher import ReferenceMatcher


def parse_date(text):
    """Tarih metnini parse et"""
    if not text:
        return None
    text = str(text).strip()
    patterns = [
        r'(\d{2})[./](\d{2})[./](\d{4})',
        r'(\d{2})\s*[-]\s*(\d{2})\s*[-]\s*(\d{4})',
        r'(\d{4})[./](\d{2})[./](\d{2})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            groups = m.groups()
            try:
                if len(groups[0]) == 4:
                    return datetime.strptime(f"{groups[0]}-{groups[1]}-{groups[2]}", "%Y-%m-%d").date()
                else:
                    return datetime.strptime(f"{groups[0]}/{groups[1]}/{groups[2]}", "%d/%m/%Y").date()
            except ValueError:
                continue
    return None


def parse_time(text):
    """Saat metnini parse et"""
    if not text:
        return None
    m = re.search(r'(\d{1,2})[:.:](\d{2})', str(text))
    if m:
        try:
            return datetime.strptime(f"{m.group(1)}:{m.group(2)}", "%H:%M").time()
        except ValueError:
            pass
    return None


def parse_komisyon_docx(filepath, file_info, matcher):
    """Komisyon DOCX dosyasını parse et"""
    from docx import Document

    filename = os.path.basename(filepath)

    try:
        doc = Document(filepath)
    except Exception as e:
        print(f"    [HATA] DOCX açılamadı: {e}")
        return None, [], None

    rapor = {
        'kurum_kodu': file_info.get('kurum_kodu'),
        'il': file_info.get('il', ''),
        'ilce': file_info.get('ilce', ''),
        'hastane_adi': file_info.get('hastane', '') or '',
        'rapor_tipi': file_info.get('rapor_tipi', 'Komisyon'),
        'degerlendirme_tarihi': None,
        'degerlendirme_saati': None,
        'ekip_uyeleri': '',
        'kaynak_dosya': filename,
        'dosya_formati': 'docx'
    }

    standartlar = []
    karar = None

    # Tabloları parse et
    for ti, table in enumerate(doc.tables):
        rows = table.rows
        if not rows:
            continue

        # Tablo 0: Genel bilgiler
        if ti == 0:
            for row in rows:
                cells = [cell.text.strip() for cell in row.cells]
                if len(cells) >= 2:
                    label = cells[0].lower()
                    value = cells[1]

                    if 'tesis' in label and 'adı' in label:
                        if value:
                            # Referans eşleştirme
                            hospital = matcher.match_by_name(value, il=rapor['il'])
                            if hospital:
                                rapor['hastane_adi'] = hospital['kurum_adi']
                                rapor['kurum_kodu'] = hospital['kurum_kodu']
                            else:
                                rapor['hastane_adi'] = value
                    elif 'kurum kodu' in label:
                        try:
                            rapor['kurum_kodu'] = int(value)
                        except (ValueError, TypeError):
                            pass
                    elif 'tarih' in label:
                        rapor['degerlendirme_tarihi'] = parse_date(value)
                    elif 'saat' in label:
                        rapor['degerlendirme_saati'] = parse_time(value)
                    elif 'üye' in label or 'ekip' in label:
                        rapor['ekip_uyeleri'] = value

        # Standart değerlendirme tabloları
        else:
            # Tablo yapısını analiz et
            try:
                header_cells = [cell.text.strip().lower() for cell in rows[0].cells]
            except:
                continue

            # Standart bazında değerlendirme tablosu mu kontrol et
            is_standart_table = False
            for h in header_cells:
                if 'standart' in h or 'uygunluk' in h or 'karşılan' in h:
                    is_standart_table = True
                    break

            if is_standart_table:
                for ri in range(1, len(rows)):
                    try:
                        cells = [cell.text.strip() for cell in rows[ri].cells]
                    except:
                        continue

                    if len(cells) < 2:
                        continue

                    standart = {
                        'standart_no': '',
                        'standart_adi': '',
                        'degerlendirme_olcutu': '',
                        'uygunluk_durumu': None,
                        'eksikler': '',
                        'sorumlu': '',
                        'planlanan_baslangic_tarihi': None,
                        'planlanan_bitis_tarihi': None,
                        'son_durum': None,
                        'aciklama': ''
                    }

                    for ci, cell_text in enumerate(cells):
                        cell_lower = cell_text.lower()
                        h_lower = header_cells[ci % len(header_cells)] if ci < len(header_cells) else ''

                        if 'standart' in h_lower and 'no' in h_lower:
                            standart['standart_no'] = cell_text
                        elif 'standart' in h_lower:
                            standart['standart_adi'] = cell_text
                        elif 'ölçüt' in h_lower or 'kriter' in h_lower:
                            standart['degerlendirme_olcutu'] = cell_text
                        elif 'uygunluk' in h_lower or 'karşılan' in h_lower:
                            # Uygunluk durumu tespit
                            standart['uygunluk_durumu'] = detect_uygunluk(cell_text)
                        elif 'eksik' in h_lower:
                            standart['eksikler'] = cell_text
                        elif 'sorumlu' in h_lower:
                            standart['sorumlu'] = cell_text
                        elif 'son durum' in h_lower or 'durum' in h_lower:
                            standart['son_durum'] = detect_son_durum(cell_text)
                        elif 'tarih' in h_lower:
                            standart['planlanan_baslangic_tarihi'] = parse_date(cell_text)

                    if standart['standart_no'] or standart['standart_adi'] or standart['uygunluk_durumu']:
                        standartlar.append(standart)

            else:
                # İyileştirme/Karar tablosu
                for row in rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    combined = ' '.join(cells).lower()

                    if 'iyileştirme' in combined or 'komisyon kararı' in combined:
                        if karar is None:
                            karar = {
                                'iyilestirme_alanlari': '',
                                'komisyon_karari': '',
                                'muafiyetler': ''
                            }
                        for cell_text in cells:
                            cell_lower = cell_text.lower()
                            if 'iyileştirme' in cell_lower and len(cell_text) > 30:
                                karar['iyilestirme_alanlari'] = cell_text
                            elif 'komisyon kararı' in cell_lower and len(cell_text) > 20:
                                karar['komisyon_karari'] = cell_text
                            elif 'muaf' in cell_lower:
                                karar['muafiyetler'] = cell_text
                            elif len(cell_text) > 50 and not karar['komisyon_karari']:
                                karar['komisyon_karari'] = cell_text

    # Kurum kodu ile referans eşleştirme (dosya adından)
    if rapor['kurum_kodu'] and not rapor['hastane_adi']:
        hospital = matcher.match_by_code(rapor['kurum_kodu'])
        if hospital:
            rapor['hastane_adi'] = hospital['kurum_adi']

    return rapor, standartlar, karar


def detect_uygunluk(text):
    """Uygunluk durumunu tespit et (metin analizi)"""
    if not text:
        return None
    text_lower = text.lower().strip()

    # Checkbox işareti kontrol
    # ☑, ✓, ✔, X, x işaretli checkbox'lar
    if re.search(r'[☑✓✔].*karşılanıyor', text_lower) or re.search(r'karşılanıyor.*[☑✓✔]', text_lower):
        if 'kısmen' in text_lower:
            return 'Kısmen Karşılanıyor'
        elif 'karşılanmıyor' not in text_lower:
            return 'Karşılanıyor'

    if 'kısmen karşılanıyor' in text_lower or 'kısmen' in text_lower:
        return 'Kısmen Karşılanıyor'
    elif 'karşılanmıyor' in text_lower:
        return 'Karşılanmıyor'
    elif 'karşılanıyor' in text_lower:
        return 'Karşılanıyor'

    return text.strip()[:30] if text.strip() else None


def detect_son_durum(text):
    """Son durumu tespit et"""
    if not text:
        return None
    text_lower = text.lower().strip()

    if 'tamamlandı' in text_lower and 'tamamlanmadı' not in text_lower:
        return 'Tamamlandı'
    elif 'tamamlanmadı' in text_lower:
        return 'Tamamlanmadı'
    elif 'devam' in text_lower:
        return 'Devam Ediyor'

    return text.strip()[:30] if text.strip() else None


def parse_komite_pdf(filepath, file_info, matcher):
    """Komite PDF dosyasını OCR ile tarayıp parse et"""
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import numpy as np
    import cv2
    import io

    filename = os.path.basename(filepath)

    rapor = {
        'kurum_kodu': file_info.get('kurum_kodu'),
        'il': file_info.get('il', ''),
        'ilce': file_info.get('ilce', ''),
        'hastane_adi': file_info.get('hastane', '') or '',
        'rapor_tipi': file_info.get('rapor_tipi', 'Komite'),
        'degerlendirme_tarihi': None,
        'degerlendirme_saati': None,
        'ekip_uyeleri': '',
        'kaynak_dosya': filename,
        'dosya_formati': 'pdf'
    }

    standartlar = []
    karar = None

    try:
        doc = fitz.open(filepath)
    except Exception as e:
        print(f"    [HATA] PDF açılamadı: {e}")
        return rapor, standartlar, karar

    full_text = ''
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Önce doğrudan metin çıkar
        text = page.get_text().strip()

        if not text:
            # OCR yap
            try:
                # Sayfayı yüksek çözünürlüklü görüntüye dönüştür
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # OpenCV ile ön işleme
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

                # Adaptif eşikleme
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 15, 8
                )

                # Gürültü azaltma
                kernel = np.ones((1, 1), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

                # Tesseract OCR
                text = pytesseract.image_to_string(
                    Image.fromarray(thresh),
                    lang='tur',
                    config='--oem 3 --psm 6'
                )

                # Checkbox tespiti
                checkboxes = detect_checkboxes_in_page(img_cv, thresh)
                if checkboxes:
                    text += '\n[CHECKBOX_DATA]\n'
                    for cb in checkboxes:
                        text += f"CHECKBOX:{cb['label']}={cb['checked']}\n"

            except Exception as e:
                text = ''

        full_text += text + '\n---PAGE_BREAK---\n'

    doc.close()

    # Full text analiz
    if full_text:
        # Tarih tespiti
        rapor['degerlendirme_tarihi'] = parse_date(full_text)
        rapor['degerlendirme_saati'] = parse_time(full_text)

        # Üye isimleri tespiti
        uye_patterns = [
            r'(?:üye|ekip|katılımcı|başkan)[\s:]*([^\n]+)',
            r'Dr\.?\s*[A-ZÇĞİÖŞÜa-zçğıöşü]+\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+',
        ]
        uye_list = []
        for pat in uye_patterns:
            matches = re.findall(pat, full_text, re.IGNORECASE)
            uye_list.extend(matches)
        if uye_list:
            rapor['ekip_uyeleri'] = '\n'.join(set(uye_list))

        # Standart değerlendirme tespiti
        standart_blocks = re.split(r'(?=Standart\s*\d)', full_text)
        for block in standart_blocks:
            if not block.strip():
                continue

            m_no = re.match(r'Standart\s*(\d+[\.\d]*)', block)
            if m_no:
                standart = {
                    'standart_no': m_no.group(1),
                    'standart_adi': block[:200].strip(),
                    'degerlendirme_olcutu': '',
                    'uygunluk_durumu': None,
                    'eksikler': '',
                    'sorumlu': '',
                    'planlanan_baslangic_tarihi': None,
                    'planlanan_bitis_tarihi': None,
                    'son_durum': None,
                    'aciklama': ''
                }

                # Uygunluk tespiti
                standart['uygunluk_durumu'] = detect_uygunluk(block)
                standart['son_durum'] = detect_son_durum(block)

                standartlar.append(standart)

        # Checkbox verilerinden uygunluk güncelleme
        if '[CHECKBOX_DATA]' in full_text:
            cb_section = full_text.split('[CHECKBOX_DATA]')[1]
            for line in cb_section.split('\n'):
                if line.startswith('CHECKBOX:'):
                    parts = line.replace('CHECKBOX:', '').split('=')
                    if len(parts) == 2:
                        label = parts[0].strip()
                        checked = parts[1].strip().lower() == 'true'
                        if checked:
                            if 'karşılanıyor' in label.lower() and 'kısmen' not in label.lower():
                                for s in standartlar:
                                    if not s['uygunluk_durumu']:
                                        s['uygunluk_durumu'] = 'Karşılanıyor'
                                        break

    # Hastane adı referans eşleştirme
    if rapor['kurum_kodu'] and not rapor['hastane_adi']:
        hospital = matcher.match_by_code(rapor['kurum_kodu'])
        if hospital:
            rapor['hastane_adi'] = hospital['kurum_adi']
            rapor['ilce'] = hospital['ilce']

    if not rapor['hastane_adi']:
        rapor['hastane_adi'] = f"{rapor['il']} - {rapor['ilce']} Sağlık Tesisi"

    return rapor, standartlar, karar


def detect_checkboxes_in_page(img_cv, thresh):
    """OpenCV ile checkbox/kutucuk tespiti"""
    try:
        # Kontur tespiti
        contours, _ = cv2.findContours(
            cv2.bitwise_not(thresh), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        checkboxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # Kutucuk boyutu filtresi (15-50 px arası)
            if 12 <= w <= 55 and 12 <= h <= 55:
                aspect_ratio = w / float(h)
                if 0.7 <= aspect_ratio <= 1.3:  # Kareye yakın
                    # İçi dolu mu kontrol et
                    roi = thresh[y:y+h, x:x+w]
                    white_ratio = cv2.countNonZero(roi) / (w * h)
                    is_checked = white_ratio < 0.75  # Dolu kutucuk

                    # Yanındaki metni bul (OCR ile)
                    # Sağ taraftaki bölge
                    text_roi = img_cv[max(0, y-5):y+h+5, x+w:min(img_cv.shape[1], x+w+300)]
                    if text_roi.size > 0:
                        try:
                            import pytesseract
                            from PIL import Image
                            label = pytesseract.image_to_string(
                                Image.fromarray(cv2.cvtColor(text_roi, cv2.COLOR_BGR2RGB)),
                                lang='tur',
                                config='--oem 3 --psm 7'
                            ).strip()
                        except:
                            label = ''
                    else:
                        label = ''

                    if label:
                        checkboxes.append({
                            'x': x, 'y': y, 'w': w, 'h': h,
                            'checked': is_checked,
                            'label': label
                        })

        return checkboxes
    except Exception:
        return []


def save_komite_rapor(rapor, standartlar, karar):
    """Komite raporunu veritabanına kaydet"""
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()

    try:
        # Kurum kodu doğrulama - referans tablosunda var mı kontrol et
        kurum_kodu = rapor['kurum_kodu']
        if kurum_kodu is not None:
            cur.execute(f"SELECT 1 FROM referans_hastaneler WHERE kurum_kodu = {placeholder}", (kurum_kodu,))
            if not cur.fetchone():
                kurum_kodu = None  # Referansta olmayan kod - NULL olarak kaydet

        # Ana rapor kaydı
        cur.execute(f"""
            INSERT INTO komite_raporlari
            (kurum_kodu, il, ilce, hastane_adi, rapor_tipi, degerlendirme_tarihi,
             degerlendirme_saati, ekip_uyeleri, kaynak_dosya, dosya_formati)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, (
            kurum_kodu, rapor['il'], rapor['ilce'], rapor['hastane_adi'],
            rapor['rapor_tipi'], 
            rapor['degerlendirme_tarihi'].isoformat() if isinstance(rapor['degerlendirme_tarihi'], (date, datetime)) else rapor['degerlendirme_tarihi'],
            rapor['degerlendirme_saati'].strftime('%H:%M') if isinstance(rapor['degerlendirme_saati'], time) else rapor['degerlendirme_saati'], 
            rapor['ekip_uyeleri'],
            rapor['kaynak_dosya'], rapor['dosya_formati']
        ))
        
        # SQLite'da son eklenen ID'yi al
        rapor_id = cur.lastrowid

        # Standart değerlendirmeler
        for s in standartlar:
            cur.execute(f"""
                INSERT INTO standart_degerlendirmeler
                (rapor_id, standart_no, standart_adi, degerlendirme_olcutu,
                 uygunluk_durumu, eksikler, sorumlu,
                 planlanan_baslangic_tarihi, planlanan_bitis_tarihi,
                 son_durum, aciklama)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (
                rapor_id, s['standart_no'], s['standart_adi'],
                s['degerlendirme_olcutu'], s['uygunluk_durumu'],
                s['eksikler'], s['sorumlu'],
                s['planlanan_baslangic_tarihi'].isoformat() if isinstance(s['planlanan_baslangic_tarihi'], (date, datetime)) else s['planlanan_baslangic_tarihi'], 
                s['planlanan_bitis_tarihi'].isoformat() if isinstance(s['planlanan_bitis_tarihi'], (date, datetime)) else s['planlanan_bitis_tarihi'],
                s['son_durum'], s['aciklama']
            ))

        # Komisyon kararı
        if karar:
            cur.execute(f"""
                INSERT INTO komisyon_kararlari
                (rapor_id, iyilestirme_alanlari, komisyon_karari, muafiyetler)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (rapor_id, karar['iyilestirme_alanlari'],
                  karar['komisyon_karari'], karar['muafiyetler']))

        conn.commit()
        return rapor_id
    except Exception as e:
        conn.rollback()
        print(f"    [HATA] Kayıt yazılamadı: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def process_all_komite():
    """Tüm komite/komisyon raporlarını işle"""
    print("=" * 60)
    print("KOMİTE/KOMİSYON RAPORLARI İŞLENİYOR")
    print("=" * 60)

    matcher = ReferenceMatcher()
    total_files = 0
    total_errors = 0
    processed_types = {'docx': 0, 'pdf': 0, 'xlsx': 0, 'other': 0}

    # Mevcut verileri temizle
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM komisyon_kararlari")
    cur.execute("DELETE FROM standart_degerlendirmeler")
    cur.execute("DELETE FROM komite_raporlari")
    conn.commit()
    cur.close()
    conn.close()

    from concurrent.futures import ThreadPoolExecutor
    
    def process_file_wrapper(filename):
        filepath = os.path.join(KOMITE_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()
        file_info = matcher.match_filename(filename)
        
        try:
            if ext == '.docx':
                rapor, standartlar, karar = parse_komisyon_docx(filepath, file_info, matcher)
                if rapor: return save_komite_rapor(rapor, standartlar, karar), 'docx'
            elif ext == '.pdf':
                rapor, standartlar, karar = parse_komite_pdf(filepath, file_info, matcher)
                if rapor: return save_komite_rapor(rapor, standartlar, karar), 'pdf'
            elif ext in ('.xlsx', '.xls'):
                rapor = {'kurum_kodu': file_info.get('kurum_kodu'), 'il': file_info.get('il', ''), 'ilce': file_info.get('ilce', ''), 'hastane_adi': file_info.get('hastane', '') or f"{file_info.get('il', '')} Sağlık Tesisi", 'rapor_tipi': file_info.get('rapor_tipi', 'Komisyon'), 'degerlendirme_tarihi': None, 'degerlendirme_saati': None, 'ekip_uyeleri': '', 'kaynak_dosya': filename, 'dosya_formati': 'xlsx'}
                return save_komite_rapor(rapor, [], None), 'xlsx'
            elif ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.jfif', '.doc'):
                rapor = {'kurum_kodu': file_info.get('kurum_kodu'), 'il': file_info.get('il', ''), 'ilce': file_info.get('ilce', ''), 'hastane_adi': file_info.get('hastane', '') or f"{file_info.get('il', '')} Sağlık Tesisi", 'rapor_tipi': 'Komite', 'degerlendirme_tarihi': None, 'degerlendirme_saati': None, 'ekip_uyeleri': '', 'kaynak_dosya': filename, 'dosya_formati': ext.replace('.', '')}
                return save_komite_rapor(rapor, [], None), 'other'
        except Exception as e:
            print(f"  [HATA] {filename}: {e}")
        return None, None

    files = sorted([f for f in os.listdir(KOMITE_DIR) if os.path.isfile(os.path.join(KOMITE_DIR, f))])
    total_count = len(files)

    print(f"Toplam {total_count} dosya paralel işleniyor (8 thread)...")
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_file_wrapper, files))

    for res, type_name in results:
        if res:
            total_files += 1
            processed_types[type_name if type_name in processed_types else 'other'] += 1

    print(f"\n{'=' * 60}")
    print(f"TOPLAM: {total_files} dosya işlendi")
    print(f"{'=' * 60}")
    return total_files

    print(f"\n{'=' * 60}")
    print(f"TOPLAM: {total_files} dosya işlendi, {total_errors} hata")
    print(f"  DOCX: {processed_types['docx']}")
    print(f"  PDF:  {processed_types['pdf']}")
    print(f"  XLSX: {processed_types['xlsx']}")
    print(f"  Diğer: {processed_types['other']}")
    print(f"{'=' * 60}")
    return total_files


if __name__ == '__main__':
    process_all_komite()
