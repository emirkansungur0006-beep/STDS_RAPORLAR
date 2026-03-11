import os
import json
import shutil
import psycopg2
import psycopg2.extras
import re
from datetime import date, time, datetime
from config import DB_CONFIG

# Nereden Nereye?
SOURCE_DIR = r"c:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR"
TARGET_DIR = r"c:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR_Masaustu"

def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('UTF8')
    return conn

def serialize_row(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, (date, datetime)):
            d[col] = val.isoformat()
        elif isinstance(val, time):
            d[col] = val.strftime('%H:%M')
        else:
            d[col] = val
    return d

def export_data():
    conn = get_db()
    cur = conn.cursor()
    
    db_dump = {
        'stats': {},
        'iller_gozlem': [],
        'iller_komite': [],
        'iller_gelisim': [],
        'dereceler': [],
        'gozlem_formlari': [],
        'komite_raporlari': [],
        'standart_degerlendirmeler': [],
        'komisyon_kararlari': [],
        'gelisim_planlari': [],
        'gozlem_gorselleri': [],
        'tree_komite': {},
        'tree_gozlem': {},
        'tree_gelisim': {}
    }

    print("İstatistikler Çekiliyor...")
    # Stats
    cur.execute("SELECT COUNT(*) FROM referans_hastaneler")
    db_dump['stats']['toplam_hastane'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gozlem_formlari")
    db_dump['stats']['toplam_gozlem'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM komite_raporlari")
    db_dump['stats']['toplam_komite'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT il) FROM gozlem_formlari")
    db_dump['stats']['gozlem_il_sayisi'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT il) FROM komite_raporlari")
    db_dump['stats']['komite_il_sayisi'] = cur.fetchone()[0]

    cur.execute("SELECT verilen_derece, COUNT(*) FROM gozlem_formlari WHERE verilen_derece IS NOT NULL GROUP BY verilen_derece")
    db_dump['stats']['derece_dagilimi'] = [{'derece': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    
    cur.execute("SELECT uygunluk_durumu, COUNT(*) as cnt FROM standart_degerlendirmeler WHERE uygunluk_durumu IS NOT NULL GROUP BY uygunluk_durumu ORDER BY cnt DESC")
    db_dump['stats']['uygunluk_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    
    cur.execute("SELECT son_durum, COUNT(*) as cnt FROM standart_degerlendirmeler WHERE son_durum IS NOT NULL GROUP BY son_durum ORDER BY cnt DESC")
    db_dump['stats']['sondurum_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    cur.execute("SELECT il, COUNT(*) as cnt FROM komite_raporlari GROUP BY il ORDER BY il")
    db_dump['stats']['il_komite_dagilimi'] = [{'il': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    print("Filtre Listeleri Çekiliyor...")
    cur.execute("SELECT DISTINCT il FROM gozlem_formlari WHERE il IS NOT NULL ORDER BY il")
    db_dump['iller_gozlem'] = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT il FROM komite_raporlari WHERE il IS NOT NULL ORDER BY il")
    db_dump['iller_komite'] = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT il FROM gelisim_planlari WHERE il IS NOT NULL ORDER BY il")
    db_dump['iller_gelisim'] = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT verilen_derece FROM gozlem_formlari WHERE verilen_derece IS NOT NULL ORDER BY verilen_derece")
    db_dump['dereceler'] = [r[0] for r in cur.fetchall()]

    print("Ana Tablolar Çekiliyor...")
    # Gozlem
    cur.execute("SELECT * FROM gozlem_formlari ORDER BY il, hastane_adi, bolum, soru_no")
    cols = [desc[0] for desc in cur.description]
    db_dump['gozlem_formlari'] = [serialize_row(row, cols) for row in cur.fetchall()]

    # Komite
    cur.execute("SELECT * FROM komite_raporlari ORDER BY il, ilce, hastane_adi")
    cols = [desc[0] for desc in cur.description]
    db_dump['komite_raporlari'] = [serialize_row(row, cols) for row in cur.fetchall()]

    # Standart Deg.
    cur.execute("SELECT * FROM standart_degerlendirmeler ORDER BY rapor_id, standart_no")
    cols = [desc[0] for desc in cur.description]
    db_dump['standart_degerlendirmeler'] = [serialize_row(row, cols) for row in cur.fetchall()]

    # Komisyon
    cur.execute("SELECT * FROM komisyon_kararlari")
    cols = [desc[0] for desc in cur.description]
    db_dump['komisyon_kararlari'] = [serialize_row(row, cols) for row in cur.fetchall()]

    # Gelisim
    cur.execute("SELECT * FROM gelisim_planlari ORDER BY il, hastane_adi, id")
    cols = [desc[0] for desc in cur.description]
    db_dump['gelisim_planlari'] = [serialize_row(row, cols) for row in cur.fetchall()]

    # Gorseller
    cur.execute("SELECT * FROM gozlem_gorselleri")
    cols = [desc[0] for desc in cur.description]
    db_dump['gozlem_gorselleri'] = [serialize_row(row, cols) for row in cur.fetchall()]

    print("Ağaç Yapıları Oluşturuluyor...")
    # Komite
    cur.execute("SELECT il, ilce, hastane_adi, rapor_tipi, COUNT(*) as cnt FROM komite_raporlari GROUP BY il, ilce, hastane_adi, rapor_tipi")
    for row in cur.fetchall():
        il, ilce, hastane, tip, count = row
        if not il: continue
        if il not in db_dump['tree_komite']: db_dump['tree_komite'][il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in db_dump['tree_komite'][il]: db_dump['tree_komite'][il][ilce_key] = []
        db_dump['tree_komite'][il][ilce_key].append({'hastane': hastane, 'rapor_tipi': tip, 'rapor_sayisi': count})

    # Gozlem
    cur.execute("SELECT il, ilce, hastane_adi, COUNT(*) as cnt FROM gozlem_formlari GROUP BY il, ilce, hastane_adi")
    for row in cur.fetchall():
        il, ilce, hastane, count = row
        if not il: continue
        if il not in db_dump['tree_gozlem']: db_dump['tree_gozlem'][il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in db_dump['tree_gozlem'][il]: db_dump['tree_gozlem'][il][ilce_key] = []
        db_dump['tree_gozlem'][il][ilce_key].append({'hastane': hastane, 'kayit_sayisi': count})

    # Gelisim
    cur.execute("SELECT il, hastane_adi, COUNT(*) as cnt FROM gelisim_planlari GROUP BY il, hastane_adi")
    for row in cur.fetchall():
        il, hastane, count = row
        if not il: continue
        if il not in db_dump['tree_gelisim']: db_dump['tree_gelisim'][il] = []
        db_dump['tree_gelisim'][il].append({'hastane': hastane, 'kayit_sayisi': count})

    cur.close()
    conn.close()

    return db_dump
def build_static_site():
    print(f"Hedef klasör oluşturuluyor: {TARGET_DIR}")
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 1. Veritabanını Çek
    print("Veritabanı dökümü alınıyor (Bu biraz sürebilir)...")
    db_dump = export_data()
    db_json = json.dumps(db_dump, ensure_ascii=False).replace("</script>", "<\\/script>")

    # 2. Yardımcı Dosyaları Oku
    def read_static(path):
        full_path = os.path.join(SOURCE_DIR, path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        print(f"UYARI: {path} bulunamadı!")
        return f"/* Error: {path} not found */"

    print("Statik dosyalar okunuyor...")
    dashboard_js = read_static('static/js/dashboard.js')
    dashboard_js = dashboard_js.replace("'/gorsel/'", "'gorseller/'").replace('"/gorsel/"', '"gorseller/"')
    dashboard_css = read_static('static/css/dashboard.css')
    
    # Harita verisini al
    map_json = read_static('static/js/tr-all.json')

    # Mock API'yi biraz daha akıllı yapalım
    # f-string kullanmıyoruz çünkü JS kodundaki { } karakterleri bozar!
    mock_api_template = r"""
    (function() {
        const DB = window.STDS_DB;
        const MAP_DATA = window.STDS_MAP;
        
        const distinct = (arr) => [...new Set(arr)].filter(Boolean).sort();
        
        window.fetch = async function(url, options) {
            const urlStr = url.toString();
            
            // Harita isteğini yakala
            if (urlStr.includes('tr-all.json')) {
                return new Response(JSON.stringify(MAP_DATA));
            }

            if (!urlStr.includes('/api/')) {
                return window._originalFetch ? window._originalFetch(url, options) : Promise.reject("OFFLINE");
            }

            const parts = urlStr.split('?');
            const pathname = parts[0].includes('/api/') ? '/api/' + parts[0].split('/api/')[1] : parts[0];
            const searchParams = new URLSearchParams(parts[1] || '');

            if (pathname === '/api/dashboard/stats') return new Response(JSON.stringify(DB.stats || {}));
            
            if (pathname.startsWith('/api/filter/iller')) {
                const md = searchParams.get('modul');
                if (md === 'gozlem') return new Response(JSON.stringify(DB.iller_gozlem || []));
                if (md === 'komite') return new Response(JSON.stringify(DB.iller_komite || []));
                return new Response(JSON.stringify(DB.iller_gelisim || []));
            }
            
            if (pathname.startsWith('/api/filter/ilceler/')) {
                const il = decodeURIComponent(pathname.split('/').pop());
                const md = searchParams.get('modul');
                let d = (md === 'gozlem') ? DB.gozlem_formlari : DB.komite_raporlari;
                return new Response(JSON.stringify(distinct(d.filter(x => x.il === il).map(x => x.ilce))));
            }

            if (pathname.startsWith('/api/filter/hastaneler')) {
                const il = searchParams.get('il'), ilce = searchParams.get('ilce'), md = searchParams.get('modul');
                let d = (md === 'komite') ? DB.komite_raporlari : DB.gozlem_formlari;
                if (il) d = d.filter(x => x.il === il);
                if (ilce) d = d.filter(x => x.ilce === ilce);
                return new Response(JSON.stringify(distinct(d.map(x => x.hastane_adi))));
            }

            if (pathname.startsWith('/api/gozlem/list')) {
                let d = DB.gozlem_formlari || [];
                const il = searchParams.get('il'); if (il) d = d.filter(x => x.il === il);
                const h = searchParams.get('hastane'); if (h) d = d.filter(x => x.hastane_adi === h);
                const p = parseInt(searchParams.get('page') || 1), pp = parseInt(searchParams.get('per_page') || 50);
                return new Response(JSON.stringify({data: d.slice((p-1)*pp, p*pp), total: d.length, page: p, per_page: pp, total_pages: Math.ceil(d.length/pp)}));
            }

            if (pathname.startsWith('/api/komite/list')) {
                let d = DB.komite_raporlari || [];
                const il = searchParams.get('il'); if (il) d = d.filter(x => x.il === il);
                const h = searchParams.get('hastane'); if (h) d = d.filter(x => x.hastane_adi === h);
                const p = parseInt(searchParams.get('page') || 1), pp = parseInt(searchParams.get('per_page') || 50);
                return new Response(JSON.stringify({data: d.slice((p-1)*pp, p*pp), total: d.length, page: p, per_page: pp, total_pages: Math.ceil(d.length/pp)}));
            }

            if (pathname.startsWith('/api/gelisim/list')) {
                let d = DB.gelisim_planlari || [];
                const il = searchParams.get('il'); if (il) d = d.filter(x => x.il === il);
                const h = searchParams.get('hastane'); if (h) d = d.filter(x => x.hastane_adi === h);
                const p = parseInt(searchParams.get('page') || 1), pp = parseInt(searchParams.get('per_page') || 50);
                return new Response(JSON.stringify({data: d.slice((p-1)*pp, p*pp), total: d.length, page: p, per_page: pp, total_pages: Math.ceil(d.length/pp)}));
            }

            if (pathname.startsWith('/api/tree/')) return new Response(JSON.stringify(DB['tree_' + pathname.split('/').pop()] || {}));
            if (pathname === '/api/gozlem/dereceler') return new Response(JSON.stringify(DB.dereceler || []));
            
            return new Response(JSON.stringify({}));
        };
    })();
    """

    # 4. İnşa
    print("Mega-HTML inşa ediliyor...")
    with open(os.path.join(SOURCE_DIR, 'templates', 'index.html'), 'r', encoding='utf-8') as f:
        tmpl = f.read()

    # Temizlik (Link ve Scriptleri kaldır)
    tmpl = re.sub(r'<link.*?dashboard\.css.*?>', '', tmpl)
    tmpl = re.sub(r'<script.*?</script>', '', tmpl, flags=re.DOTALL)
    
    # Body içeriğini al
    body_match = re.search(r'<body>(.*?)</body>', tmpl, re.DOTALL)
    body_content = body_match.group(1) if body_match else "<body>HATA: Body bulunamadı</body>"

    # HTML Şablonunu Oluştur
    final_template = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>T.C. SAĞLIK BAKANLIĞI - STDS (ÇEVRİMDIŞI SÜRÜM)</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <style>[[DASHBOARD_CSS]]</style>
    <style>
        #loading-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #f8fafc; z-index: 10000;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Inter', sans-serif; flex-direction: column;
            transition: opacity 0.5s ease;
        }
        .spinner { width: 50px; height: 50px; border: 5px solid #e2e8f0; border-top: 5px solid #0054A6; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="loading-overlay">
        <div class="spinner"></div>
        <h2 style="color:#0054A6; margin-bottom:10px;">Sistem Hazırlanıyor...</h2>
        <p style="color:#64748b;">Veritabanı yükleniyor (~40MB), lütfen tarayıcıyı kapatmayın.</p>
    </div>

    [[BODY_CONTENT]]
    
    <!-- VERİLER -->
    <script>
        window._originalFetch = window.fetch;
        window.STDS_DB = [[DB_JSON]];
        window.STDS_MAP = [[MAP_JSON]];
        console.log("Veritabanı yüklendi: ", Object.keys(window.STDS_DB).length, " tablo.");
    </script>

    <!-- KÜTÜPHANELER -->
    <script>[[CHART_JS]]</script>
    <script>[[HIGHMAPS_JS]]</script>
    <script>[[EXPORTING_JS]]</script>

    <!-- MOCK API -->
    <script>[[MOCK_API_JS]]</script>

    <!-- DASHBOARD MANTIĞI -->
    <script>
        try {
            [[DASHBOARD_JS]]
            console.log("Dashboard hazır.");
        } catch (e) {
            console.error("Dashboard başlatma hatası:", e);
            document.body.innerHTML += '<div style="background:red; color:white; padding:20px; position:fixed; bottom:0; width:100%; z-index:10001">HATA: ' + e.message + '</div>';
        }
        
        // Yükleme ekranını kaldır
        setTimeout(() => {
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.style.display = 'none', 500);
            }
        }, 1000);
    </script>
</body>
</html>"""

    # Placeholderları değiştir (f-string yerine güvenli yöntem)
    final_html = final_template.replace("[[DASHBOARD_CSS]]", dashboard_css)
    final_html = final_html.replace("[[BODY_CONTENT]]", body_content)
    final_html = final_html.replace("[[DB_JSON]]", db_json)
    final_html = final_html.replace("[[MAP_JSON]]", map_json)
    final_html = final_html.replace("[[CHART_JS]]", read_static('static/js/chart.umd.min.js'))
    final_html = final_html.replace("[[HIGHMAPS_JS]]", read_static('static/js/highmaps.js'))
    final_html = final_html.replace("[[EXPORTING_JS]]", read_static('static/js/exporting.js'))
    final_html = final_html.replace("[[MOCK_API_JS]]", mock_api_template)
    final_html = final_html.replace("[[DASHBOARD_JS]]", dashboard_js)

    # Dosyayı yaz
    output_path = os.path.join(TARGET_DIR, 'Dashboard_TEK_DOSYA.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    # 5. Görselleri Kopyala
    print("Görseller kopyalanıyor...")
    g_src = r"C:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\RAPORLAR\GÖZLEM FORMLARI\İL GÖRSELLERİ"
    if os.path.exists(g_src):
        # Görsel klasörünü 'gorseller' olarak kopyala
        shutil.copytree(g_src, os.path.join(TARGET_DIR, 'gorseller'), dirs_exist_ok=True)
    
    # Ayrıca 'static' klasörünü de kopyalayalım (logo vb. için)
    shutil.copytree(os.path.join(SOURCE_DIR, 'static'), os.path.join(TARGET_DIR, 'static'), dirs_exist_ok=True)

    print("\n" + "="*50)
    print("TAMAMLANDI!")
    print(f"DOSYA: {output_path}")
    print("BUNU AÇMANIZ YETERLİDİR.")
    print("="*50)

if __name__ == "__main__":
    build_static_site()

if __name__ == "__main__":
    build_static_site()
