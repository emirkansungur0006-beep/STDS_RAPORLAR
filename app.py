# -*- coding: utf-8 -*-
"""
STDS Raporlar - Flask API Sunucusu
T.C. Sağlık Bakanlığı Dashboard Backend
"""
import os
import json
import re
import unicodedata
import psycopg2
import psycopg2.extras
from datetime import date, time, datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from functools import wraps
from config import DB_CONFIG
app = Flask(__name__, template_folder='templates', static_folder='static')
# app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')
app.secret_key = os.environ.get('SECRET_KEY', 'stds-saglik-bakanligi-secure-key-2024')
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


import sqlite3

import traceback

def get_db():
    """Veritabanı bağlantısı al (Verified host for Vercel)"""
    db_url = "postgresql://postgres.casbkhujugmibpybhmvm:LLpp1594369*@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
    conn = psycopg2.connect(db_url)
    conn.set_client_encoding('UTF8')
    return conn

def get_placeholder():
    """DB türüne göre placeholder döner (PostgreSQL)"""
    return '%s'

def get_like_op():
    """DB türüne göre case-insensitive LIKE operatörü döner (PostgreSQL)"""
    return 'ILIKE'


def serialize_row(row, columns):
    """Veritabanı satırını JSON-serializable dict'e çevir"""
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

def map_normalize(name):
    """Harita için il ismini normalize et (Büyük harf, Türkçe karakter uyumlu)"""
    if not name: return ""
    # Türkçe büyük harf dönüşümü
    trans = str.maketrans("abcçdefgğhıijklmnoöprsştuüvyz", "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
    norm = name.translate(trans).upper().strip()
    
    # Özel düzeltmeler
    mapping = {
        'AFYON': 'AFYONKARAHİSAR',
        'ANTEP': 'GAZİANTEP',
        'MARAŞ': 'KAHRAMANMARAŞ',
        'URFA': 'ŞANLIURFA',
        'İÇEL': 'MERSİN'
    }
    return mapping.get(norm, norm)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized', 'auth_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'error': 'Forbidden: Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# AUTHENTICATION
# ============================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Kullanıcı adı ve şifre gereklidir'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        placeholder = get_placeholder()
        cur.execute(f"SELECT id, username, password_hash, role FROM users WHERE username = {placeholder}", (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user[2], password):
            session.clear()
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return jsonify({
                'success': True,
                'user': {
                    'username': user[1],
                    'role': user[3]
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
    
    return jsonify({'error': 'Geçersiz kullanıcı adı veya şifre'}), 401
@app.route('/api/auth/logout')
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/current')
def current_user():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'username': session['username'],
                'role': session['role']
            }
        })
    return jsonify({'authenticated': False}), 200

# ============================================
# USER MANAGEMENT (ADMIN ONLY)
# ============================================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
    columns = [desc[0] for desc in cur.description]
    users = [serialize_row(r, columns) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(users)

@app.route('/api/admin/users', methods=['POST'])
@admin_required
def add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'error': 'Kullanıcı adı ve şifre gereklidir'}), 400
    
    password_hash = generate_password_hash(password)
    
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    try:
        cur.execute(f"INSERT INTO users (username, password_hash, role) VALUES ({placeholder}, {placeholder}, {placeholder})", 
                   (username, password_hash, role))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Bu kullanıcı adı zaten mevcut veya bir hata oluştu'}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if 'user_id' in session and session['user_id'] == user_id:
        return jsonify({'error': 'Kendi hesabınızı silemezsiniz'}), 400
        
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"DELETE FROM users WHERE id = {placeholder}", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

# ============================================
# DASHBOARD & NAVIGATION
# ============================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Genel istatistikler"""
    conn = get_db()
    cur = conn.cursor()

    stats = {}

    # Toplam hastane sayısı (Gözlem yapılan hastanelerden al)
    cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gozlem_formlari")
    stats['toplam_hastane'] = cur.fetchone()[0]

    # Gözlem form sayısı
    cur.execute("SELECT COUNT(*) FROM gozlem_formlari")
    stats['toplam_gozlem'] = cur.fetchone()[0]

    # Komite rapor sayısı
    cur.execute("SELECT COUNT(*) FROM komite_raporlari")
    stats['toplam_komite'] = cur.fetchone()[0]

    # İl sayısı (gözlem)
    cur.execute("SELECT COUNT(DISTINCT il) FROM gozlem_formlari")
    stats['gozlem_il_sayisi'] = cur.fetchone()[0]

    # İl sayısı (komite)
    cur.execute("SELECT COUNT(DISTINCT il) FROM komite_raporlari")
    stats['komite_il_sayisi'] = cur.fetchone()[0]

    # Derece dağılımı
    cur.execute("""
        SELECT verilen_derece, COUNT(*) as cnt
        FROM gozlem_formlari
        WHERE verilen_derece IS NOT NULL
        GROUP BY verilen_derece
        ORDER BY cnt DESC
    """)
    stats['derece_dagilimi'] = [{'derece': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    # Uygunluk dağılımı
    cur.execute("""
        SELECT uygunluk_durumu, COUNT(*) as cnt
        FROM standart_degerlendirmeler
        WHERE uygunluk_durumu IS NOT NULL
        GROUP BY uygunluk_durumu
        ORDER BY cnt DESC
    """)
    stats['uygunluk_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    # Son durum dağılımı
    cur.execute("""
        SELECT son_durum, COUNT(*) as cnt
        FROM standart_degerlendirmeler
        WHERE son_durum IS NOT NULL
        GROUP BY son_durum
        ORDER BY cnt DESC
    """)
    stats['sondurum_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    # İl bazlı gözlem sayısı
    cur.execute("""
        SELECT il, COUNT(*) as cnt
        FROM gozlem_formlari
        GROUP BY il
        ORDER BY cnt DESC
    """)
    stats['il_gozlem_dagilimi'] = [{'il': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    # İl bazlı komite sayısı
    cur.execute("""
        SELECT il, COUNT(*) as cnt
        FROM komite_raporlari
        GROUP BY il
        ORDER BY il
    """)
    stats['il_komite_dagilimi'] = [{'il': r[0], 'sayi': r[1]} for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify(stats)


# ============================================
# FİLTRELEME ENDPOINTLERİ
# ============================================

@app.route('/api/filter/iller')
@login_required
def filter_iller():
    """İl listesi"""
    modul = request.args.get('modul', 'gozlem')
    conn = get_db()
    cur = conn.cursor()

    table = 'gozlem_formlari' if modul == 'gozlem' else 'komite_raporlari'
    cur.execute(f"SELECT DISTINCT il FROM {table} WHERE il IS NOT NULL AND il != '' ORDER BY il")
    iller = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify(iller)


@app.route('/api/filter/ilceler/<il>')
@login_required
def filter_ilceler(il):
    """İl bazlı ilçe listesi"""
    modul = request.args.get('modul', 'gozlem')
    conn = get_db()
    cur = conn.cursor()

    table = 'gozlem_formlari' if modul == 'gozlem' else 'komite_raporlari'
    placeholder = get_placeholder()
    cur.execute(f"SELECT DISTINCT ilce FROM {table} WHERE il = {placeholder} AND ilce IS NOT NULL AND ilce != '' ORDER BY ilce", (il,))
    ilceler = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify(ilceler)


@app.route('/api/filter/hastaneler')
@login_required
def filter_hastaneler():
    """İl/İlçe bazlı hastane listesi"""
    il = request.args.get('il')
    ilce = request.args.get('ilce')
    modul = request.args.get('modul', 'gozlem')

    conn = get_db()
    cur = conn.cursor()

    table = 'gozlem_formlari' if modul == 'gozlem' else 'komite_raporlari'
    placeholder = get_placeholder()
    query = f"SELECT DISTINCT hastane_adi FROM {table} WHERE 1=1"
    params = []

    if il:
        query += f" AND il = {placeholder}"
        params.append(il)
    if ilce:
        query += f" AND ilce = {placeholder}"
        params.append(ilce)

    query += " ORDER BY hastane_adi"
    cur.execute(query, params)
    hastaneler = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify(hastaneler)


# ============================================
# GÖRSELLER ENDPOINTLERİ (Anti-Gravity Modal)
# ============================================
from config import GÖZLEM_GÖRSELLER_DIR
GORSELLER_BASE_DIR = GÖZLEM_GÖRSELLER_DIR

def turkish_upper(s):
    """Türkçe karakterlere duyarlı büyük harf dönüşümü"""
    if not s: return ""
    return str(s).replace('i', 'İ').replace('ı', 'I').upper()

def normalize_name(name):
    """Sadece karşılaştırma için: harf büyütür, boşluk temizler, noktaları siler (ASCII only)"""
    if not name: return ""
    # Türkçe karakterleri ASCII'ye çevir
    trans = str.maketrans("çğışüöÇĞİŞÜÖıİ", "cgisuoCGISUOiI")
    name = str(name).translate(trans)
    # ASCII olmayanları sil
    name = "".join(c for c in name if ord(c) < 128)
    # Noktaları sil ve büyük harf yap
    name = name.replace(".", "").upper().strip()
    return " ".join(name.split())

def map_normalize(name):
    """Harita için sadece Türkçe BÜYÜK harf yapar (İşaretleri silmez)"""
    if not name: return ""
    return " ".join(turkish_upper(str(name).strip()).split())

def normalize_storage_path(path):
    """Supabase Storage için yolu normalleştirir (ASCII temizliği ve casing koruması)"""
    if not path: return ""
    trans = str.maketrans("çğışüöÇĞİŞÜÖıİ", "cgisuoCGISUOiI")
    path = str(path).translate(trans)
    # ASCII olmayanları temizle ama yolu (folder/file) koru
    path = "".join(c for c in path if ord(c) < 128)
    return path.replace("\\", "/")

@app.route('/api/gorseller/mevcut')
def get_gorseli_olan_hastaneler():
    """Görsele sahip olan tüm hastanelerin normalleştirilmiş isimlerini döner"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT hastane_adi FROM gozlem_gorselleri")
    hastaneler = [normalize_name(r[0]) for r in cur.fetchall() if r[0]]
    print(f"DEBUG: /api/gorseller/mevcut returning {len(hastaneler)} hospitals")
    cur.close()
    conn.close()
    return jsonify(hastaneler)

@app.route('/api/gorseller/hastane/<path:hastane_adi>')
def get_hastane_gorselleri(hastane_adi):
    """Belirli bir hastaneye ait görselleri döner (Veritabanı bazlı eşleşme ile)"""
    print(f"DEBUG: Searching for images for hospital: {hastane_adi}")
    conn = get_db()
    cur = conn.cursor()
    
    # Tüm gorselleri al ve Python tarafında normalleştirilmiş karşılaştırma yap
    # (En güvenli yol çünkü DB'deki isimler farklı normalizasyonlarda olabilir)
    cur.execute("SELECT id, il, hastane_adi, dosya_yolu FROM gozlem_gorselleri")
    rows = cur.fetchall()
    
    # Column names for response
    columns = [desc[0] for desc in cur.description]
    all_rows = []
    for r in rows:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col] = r[i]
        all_rows.append(row_dict)
    
    norm_target = normalize_name(hastane_adi)
    matches = []
    for r in all_rows:
        if normalize_name(r['hastane_adi']) == norm_target:
            matches.append(r)
            
    print(f"DEBUG: Found {len(matches)} images for {hastane_adi}")
    cur.close()
    conn.close()
    return jsonify(matches)

@app.route('/api/gorseller/upload', methods=['POST'])
def upload_gorsel():
    """Yeni görsel yükler"""
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya bulunamadı'}), 400
    file = request.files['file']
    hastane_adi = request.form.get('hastane_adi')
    
    if not file or not hastane_adi or file.filename == '':
        return jsonify({'error': 'Geçersiz parametre'}), 400

    filename = secure_filename(file.filename)
    hastane_dir = os.path.join(GORSELLER_BASE_DIR, hastane_adi)
    
    if not os.path.exists(hastane_dir):
        os.makedirs(hastane_dir)
        
    file_path = os.path.join(hastane_dir, filename)
    file.save(file_path)

    # Veritabanına da ekle
    conn = get_db()
    cur = conn.cursor()
    # hastanenin il bilgisini bulmaya çalış
    placeholder = get_placeholder()
    cur.execute(f"SELECT DISTINCT il FROM gozlem_formlari WHERE hastane_adi = {placeholder}", (hastane_adi,))
    res = cur.fetchone()
    il = res[0] if res else 'BİLİNMİYOR'

    dosya_yolu = os.path.relpath(file_path, start=GORSELLER_BASE_DIR)
    
    try:
        cur.execute(f"""
            INSERT INTO gozlem_gorselleri (il, hastane_adi, dosya_yolu) 
            VALUES ({placeholder}, {placeholder}, {placeholder}) ON CONFLICT (dosya_yolu) DO NOTHING
        """, (il, hastane_adi, dosya_yolu))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({'success': True, 'dosya_yolu': dosya_yolu})

@app.route('/api/gorseller/delete', methods=['POST'])
def delete_gorsel():
    data = request.json
    dosya_yolu = data.get('dosya_yolu')
    if not dosya_yolu:
        return jsonify({'error': 'Dosya yolu gerekli'}), 400

    full_path = os.path.join(GORSELLER_BASE_DIR, dosya_yolu)
    
    # DB den sil
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"DELETE FROM gozlem_gorselleri WHERE dosya_yolu = {placeholder}", (dosya_yolu,))
    conn.commit()
    cur.close()
    conn.close()

    # Disketten sil
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'success': True, 'message': 'Dosya zaten yok'})

@app.route('/gorsel/<path:filename>')
def serve_gorsel(filename):
    """Görseli Supabase Storage'dan yönlendir (Normalize ve URL Encode ederek)"""
    from config import SUPABASE_URL, BUCKET_GORSELLER
    import urllib.parse
    norm_filename = normalize_storage_path(filename)
    # URL'deki boşluk ve özel karakterleri encode et, klasör slaşlarını koru
    encoded_filename = urllib.parse.quote(norm_filename, safe='/')
    supabase_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_GORSELLER}/{encoded_filename}"
    print(f"DEBUG: Redirecting to {supabase_url}")
    return redirect(supabase_url)


# ============================================
# GÖZLEM FORMLARI ENDPOINTLERİ
# ============================================

@app.route('/api/gozlem/list')
@login_required
def gozlem_list():
    """Gözlem formları listesi (filtrelenebilir)"""
    il = request.args.get('il')
    ilce = request.args.get('ilce')
    hastane = request.args.get('hastane')
    derece = request.args.get('derece')
    bolum = request.args.get('bolum')
    servis = request.args.get('servis')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM gozlem_formlari WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM gozlem_formlari WHERE 1=1"
    params = []

    placeholder = get_placeholder()
    like_op = get_like_op()

    if il:
        query += f" AND il = {placeholder}"
        count_query += f" AND il = {placeholder}"
        params.append(il)
    if ilce:
        query += f" AND ilce = {placeholder}"
        count_query += f" AND ilce = {placeholder}"
        params.append(ilce)
    if hastane:
        query += f" AND hastane_adi = {placeholder}"
        count_query += f" AND hastane_adi = {placeholder}"
        params.append(hastane)
    if derece:
        query += f" AND verilen_derece = {placeholder}"
        count_query += f" AND verilen_derece = {placeholder}"
        params.append(derece)
    if bolum:
        query += f" AND bolum {like_op} {placeholder}"
        count_query += f" AND bolum {like_op} {placeholder}"
        params.append(f'%{bolum}%')
    if servis:
        query += f" AND sheet_adi = {placeholder}"
        count_query += f" AND sheet_adi = {placeholder}"
        params.append(servis)
    if search:
        query += f" AND (soru {like_op} {placeholder} OR notlar {like_op} {placeholder} OR hastane_adi {like_op} {placeholder})"
        count_query += f" AND (soru {like_op} {placeholder} OR notlar {like_op} {placeholder} OR hastane_adi {like_op} {placeholder})"
        params.extend([f'%{search}%'] * 3)

    # Count
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    # Data
    query += " ORDER BY il, hastane_adi, bolum, soru_no"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    cur.execute(query, params)

    columns = [desc[0] for desc in cur.description]
    rows = [serialize_row(row, columns) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        'data': rows,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/gozlem/dereceler')
def gozlem_dereceler():
    """Mevcut derece listesi"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT verilen_derece FROM gozlem_formlari
        WHERE verilen_derece IS NOT NULL
        ORDER BY verilen_derece
    """)
    dereceler = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(dereceler)


@app.route('/api/gozlem/bolumler')
def gozlem_bolumler():
    """Mevcut bölüm listesi"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT bolum FROM gozlem_formlari
        WHERE bolum IS NOT NULL
        ORDER BY bolum
    """)
    bolumler = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(bolumler)


# ============================================
# KOMİTE RAPORLARI ENDPOINTLERİ
# ============================================

@app.route('/api/komite/list')
@login_required
def komite_list():
    """Komite raporları listesi"""
    il = request.args.get('il')
    ilce = request.args.get('ilce')
    hastane = request.args.get('hastane')
    rapor_tipi = request.args.get('rapor_tipi')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM komite_raporlari WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM komite_raporlari WHERE 1=1"
    params = []

    placeholder = get_placeholder()
    like_op = get_like_op()

    if il:
        query += f" AND il = {placeholder}"
        count_query += f" AND il = {placeholder}"
        params.append(il)
    if ilce:
        query += f" AND ilce = {placeholder}"
        count_query += f" AND ilce = {placeholder}"
        params.append(ilce)
    if hastane:
        query += f" AND hastane_adi = {placeholder}"
        count_query += f" AND hastane_adi = {placeholder}"
        params.append(hastane)
    if rapor_tipi:
        query += f" AND rapor_tipi = {placeholder}"
        count_query += f" AND rapor_tipi = {placeholder}"
        params.append(rapor_tipi)
    if search:
        query += f" AND (hastane_adi {like_op} {placeholder} OR kaynak_dosya {like_op} {placeholder})"
        count_query += f" AND (hastane_adi {like_op} {placeholder} OR kaynak_dosya {like_op} {placeholder})"
        params.extend([f'%{search}%'] * 2)

    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    query += " ORDER BY il, ilce, hastane_adi"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    cur.execute(query, params)

    columns = [desc[0] for desc in cur.description]
    rows = [serialize_row(row, columns) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        'data': rows,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/komite/detail/<int:id>')
@login_required
def komite_detail(id):
    """Komite rapor detayı"""
    conn = get_db()
    cur = conn.cursor()

    # Rapor bilgisi
    placeholder = get_placeholder()
    cur.execute(f"SELECT * FROM komite_raporlari WHERE id = {placeholder}", (id,))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({'error': 'Rapor bulunamadı'}), 404

    rapor = serialize_row(row, columns)

    # Standart değerlendirmeler
    placeholder = get_placeholder()
    cur.execute(f"SELECT * FROM standart_degerlendirmeler WHERE rapor_id = {placeholder} ORDER BY standart_no", (id,))
    s_columns = [desc[0] for desc in cur.description]
    standartlar = [serialize_row(r, s_columns) for r in cur.fetchall()]

    # Komisyon kararları
    cur.execute(f"SELECT * FROM komisyon_kararlari WHERE rapor_id = {placeholder}", (id,))
    k_columns = [desc[0] for desc in cur.description]
    kararlar = [serialize_row(r, k_columns) for r in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        'rapor': rapor,
        'standartlar': standartlar,
        'kararlar': kararlar
    })


@app.route('/api/komite/uyeler/<int:id>')
def komite_uyeler(id):
    """Komite üyeleri"""
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"SELECT ekip_uyeleri FROM komite_raporlari WHERE id = {placeholder}", (id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and row[0]:
        # Üye listesini parse et
        raw = row[0]
        members = []
        for line in raw.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                members.append(line)
        return jsonify({'uyeler': members, 'raw': raw})
    return jsonify({'uyeler': [], 'raw': ''})


@app.route('/api/komite/standartlar/<int:id>')
def komite_standartlar(id):
    """Rapor bazlı standart değerlendirmeler"""
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"""
        SELECT * FROM standart_degerlendirmeler
        WHERE rapor_id = {placeholder}
        ORDER BY standart_no
    """, (id,))
    columns = [desc[0] for desc in cur.description]
    rows = [serialize_row(r, columns) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/komite/preview/<int:id>')
@login_required
def komite_preview(id):
    """Komite Raporu kaynak dosyasını Supabase Storage'dan indirip sunar."""
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"SELECT il, kaynak_dosya FROM komite_raporlari WHERE id = {placeholder}", (id,))
    rapor = cur.fetchone()
    cur.close()
    conn.close()

    if not rapor or not rapor[0] or not rapor[1]:
        return jsonify({"error": "Rapor veya dosya bulunamadı"}), 404

    il_adi = rapor[0]
    dosya_adi = rapor[1]

    from config import SUPABASE_URL, SUPABASE_KEY, BUCKET_RAPORLAR
    import requests
    import io
    import urllib.parse

    # Supabase Storage'dan dosyayı indir (Özel bucket için Authenticated URL)
    norm_dosya_adi = normalize_storage_path(dosya_adi)
    encoded_dosya_adi = urllib.parse.quote(norm_dosya_adi, safe='/')
    supabase_url = f"{SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET_RAPORLAR}/{encoded_dosya_adi}"
    print(f"DEBUG: Previewing file from {supabase_url}")
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY
    }
    response = requests.get(supabase_url, headers=headers)

    if response.status_code != 200:
        return f"Dosya bulutta bulunamadı: {dosya_adi} (Status: {response.status_code})", 404

    file_data = io.BytesIO(response.content)
    ext = os.path.splitext(dosya_adi)[1].lower()

    if ext == '.pdf':
        from flask import send_file
        return send_file(file_data, mimetype='application/pdf', as_attachment=False, download_name=dosya_adi)
    
    elif ext == '.docx':
        # Extract text/html using mammoth
        try:
            import mammoth
            result = mammoth.convert_to_html(file_data)
            html = result.value
            
            html_content = f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto;'>"
            html_content += f"<h2 style='text-align:center; color:#0054A6; border-bottom:1px solid #ddd; padding-bottom:10px;'>{dosya_adi}</h2>"
            html_content += f"<div style='margin-top:20px;' class='docx-content'>{html}</div>"
            html_content += "</div>"
            
            # Simple styling for the mammoth output tables
            style = """
            <style>
            .docx-content table { width:100%; border-collapse: collapse; margin-top:10px; margin-bottom:20px; font-size: 13px; }
            .docx-content th, .docx-content td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }
            .docx-content th { background-color: #f8f9fa; font-weight: bold; }
            .docx-content p { margin: 0 0 10px 0; }
            </style>
            """
            return style + html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            return f"<div style='color:red; text-align:center;'>Word dosyası okunamadı: {str(e)}</div>", 500
            
    elif ext in ['.xlsx', '.xls']:
        try:
            import pandas as pd
            # Use pandas to read all sheets
            xls = pd.ExcelFile(file_data)
            html_content = f"<div style='font-family: Arial, sans-serif;'>"
            html_content += f"<h2 style='text-align:center; color:#0054A6;'>{dosya_adi}</h2>"
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                html_content += f"<h3 style='margin-top:20px; background:#f0f4f8; padding:10px;'>Sekme: {sheet_name}</h3>"
                # convert dataframe to interactive HTML table
                html_content += df.to_html(index=False, classes="data-table", justify="left")
            html_content += "</div>"
            # We want to provide some basic css for the pandas table so it's readable
            style = """
            <style>
            .data-table { width:100%; border-collapse: collapse; margin-top:10px; font-size: 13px; }
            .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .data-table th { background-color: #f8f9fa; color: #333; font-weight: 600; }
            </style>
            """
            return style + html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            return f"<div style='color:red; text-align:center;'>Excel dosyası okunamadı: {str(e)}</div>", 500
            
    else:
        return f"<div style='color:red; text-align:center;'>Desteklenmeyen dosya formatı: {ext}</div>", 400


# ============================================
# HİYERARŞİK AĞAÇ YAPISI
# ============================================

@app.route('/api/tree/gozlem')
@login_required
def gozlem_tree():
    """Gözlem formları ağaç yapısı: İl -> İlçe -> Hastane (Tüm hastaneleri gösterir)"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT il, NULL as ilce, hastane_adi FROM gelisim_planlari GROUP BY il, hastane_adi
        UNION
        SELECT il, ilce, hastane_adi FROM komite_raporlari GROUP BY il, ilce, hastane_adi
        UNION
        SELECT il, ilce, hastane_adi FROM gozlem_formlari GROUP BY il, ilce, hastane_adi
    """)
    all_hospitals = cur.fetchall()

    cur.execute("""
        SELECT il, ilce, hastane_adi, COUNT(*) as kayit_sayisi
        FROM gozlem_formlari
        GROUP BY il, ilce, hastane_adi
    """)
    raporlar = {}
    for r in cur.fetchall():
        il, ilce, hastane, count = r
        raporlar[(il, ilce, hastane)] = count

    tree = {}
    for row in all_hospitals:
        il, ilce, hastane = row
        if not il:
            continue
        if il not in tree:
            tree[il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in tree[il]:
            tree[il][ilce_key] = []
            
        count = raporlar.get((il, ilce, hastane), 0)
        tree[il][ilce_key].append({'hastane': hastane, 'kayit_sayisi': count})

    cur.close()
    conn.close()
    return jsonify(tree)


@app.route('/api/tree/komite')
def komite_tree():
    """Komite raporları ağaç yapısı: İl -> İlçe -> Hastane (Tüm hastaneleri gösterir)"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT il, NULL as ilce, hastane_adi FROM gelisim_planlari GROUP BY il, hastane_adi
        UNION
        SELECT il, ilce, hastane_adi FROM komite_raporlari GROUP BY il, ilce, hastane_adi
        UNION
        SELECT il, ilce, hastane_adi FROM gozlem_formlari GROUP BY il, ilce, hastane_adi
    """)
    all_hospitals = cur.fetchall()

    cur.execute("""
        SELECT il, ilce, hastane_adi, rapor_tipi, COUNT(*) as rapor_sayisi
        FROM komite_raporlari
        GROUP BY il, ilce, hastane_adi, rapor_tipi
    """)
    raporlar = {}
    for r in cur.fetchall():
        il, ilce, hastane, tip, count = r
        key = (il, ilce, hastane)
        if key not in raporlar:
            raporlar[key] = []
        raporlar[key].append({'tip': tip, 'count': count})

    tree = {}
    for row in all_hospitals:
        il, ilce, hastane = row
        if not il:
            continue
        if il not in tree:
            tree[il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in tree[il]:
            tree[il][ilce_key] = []
            
        key = (il, ilce, hastane)
        rapor_verisi = raporlar.get(key, [])
        if not rapor_verisi:
            tree[il][ilce_key].append({
                'hastane': hastane,
                'rapor_tipi': 'Yok',
                'rapor_sayisi': 0
            })
        else:
            for rv in rapor_verisi:
                tree[il][ilce_key].append({
                    'hastane': hastane,
                    'rapor_tipi': rv['tip'],
                    'rapor_sayisi': rv['count']
                })

    cur.close()
    conn.close()
    return jsonify(tree)


# ============================================
# GELİŞİM PLANLARI ENDPOINTLERİ
# ============================================

@app.route('/api/gelisim/list')
@login_required
def gelisim_list():
    """Gelişim planları listesi"""
    il = request.args.get('il')
    hastane = request.args.get('hastane')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM gelisim_planlari WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM gelisim_planlari WHERE 1=1"
    params = []

    placeholder = get_placeholder()
    like_op = get_like_op()

    if il:
        query += f" AND il = {placeholder}"
        count_query += f" AND il = {placeholder}"
        params.append(il)
    if hastane:
        query += f" AND hastane_adi = {placeholder}"
        count_query += f" AND hastane_adi = {placeholder}"
        params.append(hastane)
    if search:
        query += f" AND (kurum_hedefleri {like_op} {placeholder} OR mevcut_durum {like_op} {placeholder} OR hastane_adi {like_op} {placeholder})"
        count_query += f" AND (kurum_hedefleri {like_op} {placeholder} OR mevcut_durum {like_op} {placeholder} OR hastane_adi {like_op} {placeholder})"
        params.extend([f'%{search}%'] * 3)

    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    # Sıralama: İl ve Hastane Adı (ID ekleyerek stabilite sağla)
    query += " ORDER BY il ASC, hastane_adi ASC, id ASC"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    cur.execute(query, params)

    columns = [desc[0] for desc in cur.description]
    rows = [serialize_row(row, columns) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        'data': rows,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/tree/gelisim')
@login_required
def gelisim_tree():
    """Gelişim planları ağaç yapısı"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT il, hastane_adi, COUNT(*) as kayit_sayisi
        FROM gelisim_planlari
        GROUP BY il, hastane_adi
        ORDER BY il, hastane_adi
    """)

    tree = {}
    for row in cur.fetchall():
        il, hastane, count = row
        if not il:
            continue
        if il not in tree:
            tree[il] = []
        tree[il].append({'hastane': hastane, 'kayit_sayisi': count})

    cur.close()
    conn.close()
    return jsonify(tree)

@app.route('/api/process/gelisim', methods=['POST'])
def process_gelisim():
    """Gelişim planlarını işle"""
    from gelisim_parser import process_all_gelisim
    count = process_all_gelisim()
    return jsonify({'status': 'ok', 'records': count})

@app.route('/api/filter/gelisim/iller')
@login_required
def gelisim_iller():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT il FROM gelisim_planlari WHERE il IS NOT NULL ORDER BY il")
    iller = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(iller)

@app.route('/api/filter/gelisim/ilceler/<il>')
@login_required
def gelisim_ilceler(il):
    conn = get_db()
    cur = conn.cursor()
    placeholder = get_placeholder()
    cur.execute(f"SELECT DISTINCT ilce FROM gelisim_planlari WHERE il = {placeholder} AND ilce IS NOT NULL ORDER BY ilce", (il,))
    ilceler = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(ilceler)

@app.route('/api/filter/gelisim/hastaneler')
@login_required
def gelisim_hastaneler():
    il = request.args.get('il')
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT DISTINCT hastane_adi FROM gelisim_planlari WHERE 1=1"
    params = []
    placeholder = get_placeholder()
    if il:
        query += f" AND il = {placeholder}"
        params.append(il)
    query += " ORDER BY hastane_adi"
    
    cur.execute(query, params)
    hastaneler = [r[0] for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    return jsonify(hastaneler)

@app.route('/api/stats/gelisim/iller')
@login_required
def gelisim_il_stats():
    """Harita için il bazlı kayıt sayıları"""
    conn = get_db()
    cur = conn.cursor()
    # SQLite'da UPPER Turkish 'İ' leri bozabilir, bu yüzden veriyi çekip Python'da normalize edelim
    cur.execute("""
        SELECT il, COUNT(*) as count 
        FROM gelisim_planlari 
        WHERE il IS NOT NULL AND il != ''
        GROUP BY il
    """)
    raw_stats = cur.fetchall()
    stats = {}
    for il, count in raw_stats:
        norm_il = map_normalize(il)
        if norm_il in stats:
            stats[norm_il] += count
        else:
            stats[norm_il] = count
    
    cur.close()
    conn.close()
    return jsonify(stats)


@app.route('/api/process/gozlem', methods=['POST'])
def process_gozlem():
    """Gözlem formlarını işle"""
    from gozlem_parser import process_all_gozlem
    count = process_all_gozlem()
    return jsonify({'status': 'ok', 'records': count})


@app.route('/api/process/komite', methods=['POST'])
def process_komite():
    """Komite raporlarını işle"""
    from komisyon_parser import process_all_komite
    count = process_all_komite()
    return jsonify({'status': 'ok', 'records': count})


if __name__ == '__main__':
    print("=" * 60)
    print("T.C. SAĞLIK BAKANLIĞI - STDS Dashboard")
    print("http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
