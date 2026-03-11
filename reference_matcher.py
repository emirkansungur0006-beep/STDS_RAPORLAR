# -*- coding: utf-8 -*-
"""
STDS Raporlar - Referans Hastane Eşleştirme Modülü
Fuzzy matching ile OCR kaynaklı yazım hatalarını referans verisine eşleştirir.
"""
import re
import unicodedata
import psycopg2
import openpyxl
from config import DB_CONFIG, REFERANS_FILE


class ReferenceMatcherError(Exception):
    pass


def normalize_turkish(text):
    """Türkçe metni normalize et - küçük harf, özel karakter temizliği"""
    if not text:
        return ''
    text = str(text).strip()
    # Küçük harfe çevir
    text = text.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'g').replace('Ü', 'u').replace('Ş', 's').replace('Ö', 'o').replace('Ç', 'c')
    text = text.replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c').replace('ı', 'i')
    # Sadece alfanumerik ve boşluk kalsın
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    # Çoklu boşlukları tekle
    text = re.sub(r'\s+', ' ', text).lower().strip()
    return text


def levenshtein_distance(s1, s2):
    """İki string arasındaki Levenshtein mesafesini hesapla"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def similarity_ratio(s1, s2):
    """İki string arasındaki benzerlik oranını hesapla (0-1)"""
    if not s1 or not s2:
        return 0.0
    n1 = normalize_turkish(s1)
    n2 = normalize_turkish(s2)
    if n1 == n2:
        return 1.0
    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return 0.0
    dist = levenshtein_distance(n1, n2)
    return 1.0 - (dist / max_len)


class ReferenceMatcher:
    """Referans hastane veritabanı ile fuzzy matching"""

    def __init__(self):
        self.hospitals = []
        self.hospitals_by_code = {}
        self.hospitals_by_il = {}
        self._load_from_db()

    def _load_from_db(self):
        """Referans verilerini veritabanından yükle"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT kurum_kodu, il, ilce, kurum_adi FROM referans_hastaneler")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            for row in rows:
                entry = {
                    'kurum_kodu': row[0],
                    'il': row[1],
                    'ilce': row[2],
                    'kurum_adi': row[3],
                    'kurum_adi_norm': normalize_turkish(row[3])
                }
                self.hospitals.append(entry)
                self.hospitals_by_code[row[0]] = entry
                il_key = normalize_turkish(row[1])
                if il_key not in self.hospitals_by_il:
                    self.hospitals_by_il[il_key] = []
                self.hospitals_by_il[il_key].append(entry)

            if rows:
                print(f"[ReferenceMatcher] {len(rows)} hastane yüklendi.")
        except Exception as e:
            print(f"[ReferenceMatcher] DB yükleme hatası: {e}")

    def match_by_code(self, kurum_kodu):
        """Kurum koduna göre tam eşleşme"""
        try:
            code = int(kurum_kodu)
            return self.hospitals_by_code.get(code)
        except (ValueError, TypeError):
            return None

    def match_by_name(self, name, il=None, threshold=0.65):
        """Hastane adına göre fuzzy eşleşme"""
        if not name:
            return None

        name_norm = normalize_turkish(name)
        best_match = None
        best_score = 0

        # İl bazlı filtreleme
        candidates = self.hospitals
        if il:
            il_norm = normalize_turkish(il)
            candidates = self.hospitals_by_il.get(il_norm, self.hospitals)

        for h in candidates:
            # Tam eşleşme kontrolü
            if h['kurum_adi_norm'] == name_norm:
                return h

            # 2. İsim içerme kontrolü
            if name_norm in h['kurum_adi_norm'] or h['kurum_adi_norm'] in name_norm:
                score = 0.9
            else:
                score = similarity_ratio(name, h['kurum_adi'])

            # 3. Kelime seti (Word-set) kontrolü - Özellikle isim sırası farklıysa
            if score < threshold:
                # Önemli kelimeleri ayıkla (stop-words hariç)
                stop_words = {'devlet', 'hastanesi', 'sağlık', 'bakanlığı', 't.c', 'tc', 'ili', 'merkezi'}
                input_words = set(w for w in name_norm.split() if len(w) > 1 and w not in stop_words)
                ref_words = set(h['kurum_adi_norm'].split())
                
                if input_words and input_words.issubset(ref_words):
                    score = 0.86
                elif input_words and len(input_words.intersection(ref_words)) >= max(2, len(input_words) - 1):
                    score = 0.81 # Çoğu kelime uyuyorsa kabul et

            if score > best_score:
                best_score = score
                best_match = h

        if best_score >= threshold:
            return best_match
        return None

    def match_filename(self, filename):
        """Dosya adından İL-İLÇE-Tip-KurumKodu bilgisi çıkar"""
        parts = filename.split('-')
        result = {
            'il': None,
            'ilce': None,
            'rapor_tipi': None,
            'kurum_kodu': None,
            'aciklama': None,
            'hastane': None
        }

        if len(parts) >= 4:
            result['il'] = parts[0].strip()
            result['ilce'] = parts[1].strip()
            result['rapor_tipi'] = parts[2].strip()
            try:
                result['kurum_kodu'] = int(parts[3].strip())
            except ValueError:
                pass
            if len(parts) >= 5:
                # Dosya adının geri kalanı (uzantı hariç)
                aciklama = '-'.join(parts[4:])
                aciklama = re.sub(r'\.[^.]+$', '', aciklama)
                result['aciklama'] = aciklama.strip()

        # Kurum kodu varsa referanstan eşleştir
        if result['kurum_kodu']:
            hospital = self.match_by_code(result['kurum_kodu'])
            if hospital:
                result['hastane'] = hospital['kurum_adi']
                # İl/İlçe doğrulaması
                if not result['il']:
                    result['il'] = hospital['il']
                if not result['ilce']:
                    result['ilce'] = hospital['ilce']

        return result


def load_reference_data():
    """Referans XLSX dosyasını oku ve veritabanına yükle"""
    print(f"[Referans] Dosya okunuyor: {REFERANS_FILE}")
    wb = openpyxl.load_workbook(REFERANS_FILE, read_only=True)
    ws = wb.active

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Mevcut veriyi temizle
    cur.execute("DELETE FROM referans_hastaneler")

    count = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        kurum_kodu = row[0]
        if kurum_kodu is None:
            continue

        try:
            kurum_kodu = int(kurum_kodu)
        except (ValueError, TypeError):
            continue

        il = str(row[1]).strip() if row[1] else ''
        ilce = str(row[2]).strip() if row[2] else ''
        kurum_adi = str(row[3]).strip() if row[3] else ''
        eah = str(row[4]).strip() if row[4] else None
        kurum_turu = str(row[5]).strip() if row[5] else None
        tescil_unit = row[6] if isinstance(row[6], (int, float)) else None
        tescil_yatak = row[7] if isinstance(row[7], (int, float)) else None
        sinif = str(row[8]).strip() if row[8] else None
        # Skip column 9 (empty)
        gruplar = str(row[10]).strip() if len(row) > 10 and row[10] else None

        if not il or not kurum_adi:
            continue

        kurum_adi_norm = normalize_turkish(kurum_adi)

        try:
            cur.execute("""
                INSERT INTO referans_hastaneler
                (kurum_kodu, il, ilce, kurum_adi, kurum_adi_normalized, eah, kurum_turu,
                 tescil_unit_sayisi, tescil_yatak_sayisi, sinif, gruplar)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kurum_kodu) DO UPDATE SET
                    il = EXCLUDED.il,
                    ilce = EXCLUDED.ilce,
                    kurum_adi = EXCLUDED.kurum_adi,
                    kurum_adi_normalized = EXCLUDED.kurum_adi_normalized
            """, (kurum_kodu, il, ilce, kurum_adi, kurum_adi_norm, eah, kurum_turu,
                  tescil_unit, tescil_yatak, sinif, gruplar))
            count += 1
        except Exception as e:
            print(f"  [HATA] Kurum {kurum_kodu}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    wb.close()

    print(f"[Referans] {count} hastane kaydı veritabanına yüklendi.")
    return count


if __name__ == '__main__':
    count = load_reference_data()
    matcher = ReferenceMatcher()
    print(f"\nTest: Kod ile eşleşme (6349) -> {matcher.match_by_code(6349)}")
    print(f"Test: İsim ile eşleşme -> {matcher.match_by_name('CEYHAN DEVLET HASTANESİ', il='ADANA')}")
