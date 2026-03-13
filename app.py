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
import requests
import urllib.parse
import io
from datetime import date, time, datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for, Response, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from functools import wraps
from config import DB_CONFIG, SUPABASE_URL, SUPABASE_KEY, BUCKET_RAPORLAR, BUCKET_GORSELLER

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'stds-saglik-bakanligi-secure-key-2024')
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

def get_supabase_url_base(bucket, filename):
    """Normalize filename and return base storage URL for authenticated access"""
    if not filename: return None
    # Ensure forward slashes and no leading slash
    path = str(filename).replace('\\', '/').strip('/')
    # Encoded path (quote handles spaces as %20)
    encoded_path = urllib.parse.quote(path)
    return f"{SUPABASE_URL}/storage/v1/object/authenticated/{bucket}/{encoded_path}"

def get_supabase_signed_url(bucket, filename, expires_in=3600):
    """Generates a signed URL for a file in Supabase Storage"""
    if not filename: return None
    path = str(filename).replace('\\', '/').strip('/')
    encoded_path = urllib.parse.quote(path)
    # API: POST /storage/v1/object/sign/[bucket]/[path]
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{encoded_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, headers=headers, json={"expiresIn": expires_in})
        if r.status_code == 200:
            data = r.json()
            # Supabase returns /object/sign/..., we must prefix with SUPABASE_URL + /storage/v1
            return f"{SUPABASE_URL}/storage/v1{data['signedURL']}"
    except Exception as e:
        print(f"DEBUG: Signed URL error: {e}")
    return None

import sqlite3
import traceback

def get_db():
    """Veritabanı bağlantısı al (Verified host for Vercel)"""
    db_url = "postgresql://postgres.casbkhujugmibpybhmvm:LLpp1594369*@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
    conn = psycopg2.connect(db_url)
    conn.set_client_encoding('UTF8')
    return conn

def normalize_storage_path(path):
    """Normalize path for Supabase Storage (Forward slashes, no double slashes)"""
    if not path: return ""
    path = path.replace('\\', '/')
    while '//' in path:
        path = path.replace('//', '/')
    return path.strip('/')

def normalize_name(name):
    """Kusursuz Normalizasyon: Türkçe karakterleri ASCII karşılıklarına indirger ve temizler"""
    if not name: return ""
    import unicodedata
    import re
    # NFD: Normalize characters (dotted I -> I + dot)
    s_nfd = unicodedata.normalize('NFD', str(name))
    # Filter out non-spacing marks (dots, accents)
    s_clean = "".join(c for c in s_nfd if unicodedata.category(c) != 'Mn')
    # Custom mapping for edge cases if any
    # Replace common symbols
    s_clean = re.sub(r'[.\-\(\)\_]', ' ', s_clean)
    # Upper case and collapse spaces
    return " ".join(s_clean.strip().upper().split())

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
    trans = str.maketrans("abcçdefgğhıijklmnoöprsştuüvyz", "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
    norm = name.translate(trans).upper().strip()
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
    conn = get_db()
    cur = conn.cursor()
    stats = {}
    cur.execute("SELECT COUNT(DISTINCT hastane_adi) FROM gozlem_formlari")
    stats['toplam_hastane'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gozlem_formlari")
    stats['toplam_gozlem'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM komite_raporlari")
    stats['toplam_komite'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT il) FROM gozlem_formlari")
    stats['gozlem_il_sayisi'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT il) FROM komite_raporlari")
    stats['komite_il_sayisi'] = cur.fetchone()[0]
    cur.execute("SELECT verilen_derece, COUNT(*) as cnt FROM gozlem_formlari WHERE verilen_derece IS NOT NULL GROUP BY verilen_derece ORDER BY cnt DESC")
    stats['derece_dagilimi'] = [{'derece': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    cur.execute("SELECT uygunluk_durumu, COUNT(*) as cnt FROM standart_degerlendirmeler WHERE uygunluk_durumu IS NOT NULL GROUP BY uygunluk_durumu ORDER BY cnt DESC")
    stats['uygunluk_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    cur.execute("SELECT son_durum, COUNT(*) as cnt FROM standart_degerlendirmeler WHERE son_durum IS NOT NULL GROUP BY son_durum ORDER BY cnt DESC")
    stats['sondurum_dagilimi'] = [{'durum': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    cur.execute("SELECT il, COUNT(*) as cnt FROM gozlem_formlari GROUP BY il ORDER BY cnt DESC")
    stats['il_gozlem_dagilimi'] = [{'il': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    cur.execute("SELECT il, COUNT(*) as cnt FROM komite_raporlari GROUP BY il ORDER BY il")
    stats['il_komite_dagilimi'] = [{'il': r[0], 'sayi': r[1]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(stats)

@app.route('/api/filter/iller')
@login_required
def filter_iller():
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
# GÖRSELLER ENDPOINTLERİ
# ============================================
from config import GÖZLEM_GÖRSELLER_DIR
GORSELLER_BASE_DIR = GÖZLEM_GÖRSELLER_DIR

def turkish_upper(s):
    if not s: return ""
    return str(s).replace('i', 'İ').replace('ı', 'I').upper()

@app.route('/api/gorseller/mevcut')
def get_gorseli_olan_hastaneler():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT hastane_adi FROM gozlem_gorselleri")
    hastaneler = [normalize_name(r[0]) for r in cur.fetchall() if r[0]]
    cur.close()
    conn.close()
    return jsonify(hastaneler)

@app.route('/api/gorseller/hastane/<path:hastane_adi>')
def get_hastane_gorselleri(hastane_adi):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, il, hastane_adi, dosya_yolu FROM gozlem_gorselleri")
    rows = cur.fetchall()
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
    cur.close()
    conn.close()
    return jsonify(matches)

@app.route('/gorsel/<path:filename>')
def serve_gorsel(filename):
    """Yerel diskte yoksa Supabase'den çekip sun (Proxy with Signed URL redirection fallback)"""
    from config import GÖZLEM_GÖRSELLER_DIR
    local_path = os.path.join(GÖZLEM_GÖRSELLER_DIR, filename)
    if os.path.exists(local_path):
        return send_from_directory(GÖZLEM_GÖRSELLER_DIR, filename)
    
    # Try fetching with Signed URL for better compatibility
    signed_url = get_supabase_signed_url(BUCKET_GORSELLER, filename)
    if signed_url:
        try:
            r = requests.get(signed_url)
            if r.status_code == 200:
                # Still proxying in backend to avoid CORS/broken iframe if images are embedded complexly
                # But using a SIGNED URL from backend makes the request more reliable
                return Response(r.content, mimetype=r.headers.get('Content-Type'))
        except Exception as e:
            print(f"DEBUG: Image proxy error: {e}")
    
    return "Görsel bulunamadı", 404

# ============================================
# KOMİTE RAPORLARI ENDPOINTLERİ
# ============================================

@app.route('/api/komite/list')
@login_required
def komite_list():
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
    return jsonify({'data': rows, 'total': total, 'page': page, 'per_page': per_page, 'total_pages': (total + per_page - 1) // per_page})

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

    dosya_adi = rapor[1]
    # Use Signed URL for more reliable access
    signed_url = get_supabase_signed_url(BUCKET_RAPORLAR, dosya_adi)
    
    try:
        if not signed_url:
            raise Exception("Supabase Signed URL üretilemedi.")
            
        response = requests.get(signed_url)
        if response.status_code != 200:
            return f"Dosya bulutta bulunamadı: {dosya_adi} (Status: {response.status_code})", 404
            
        file_data = io.BytesIO(response.content)
        ext = os.path.splitext(dosya_adi)[1].lower()

        if ext == '.pdf':
            return send_file(file_data, mimetype='application/pdf', as_attachment=False, download_name=dosya_adi)
        
        elif ext == '.docx':
            import mammoth
            result = mammoth.convert_to_html(file_data)
            html = result.value
            html_content = f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto;'>"
            html_content += f"<h2 style='text-align:center; color:#0054A6; border-bottom:1px solid #ddd; padding-bottom:10px;'>{dosya_adi}</h2>"
            html_content += f"<div style='margin-top:20px;' class='docx-content'>{html}</div>"
            html_content += "</div>"
            style = "<style>.docx-content table { width:100%; border-collapse: collapse; margin-top:10px; margin-bottom:20px; font-size: 13px; } .docx-content th, .docx-content td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; } .docx-content th { background-color: #f8f9fa; font-weight: bold; } .docx-content p { margin: 0 0 10px 0; }</style>"
            return style + html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
            
        elif ext in ['.xlsx', '.xls']:
            import pandas as pd
            xls = pd.ExcelFile(file_data)
            html_content = f"<div style='font-family: Arial, sans-serif;'><h2 style='text-align:center; color:#0054A6;'>{dosya_adi}</h2>"
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                html_content += f"<h3 style='margin-top:20px; background:#f0f4f8; padding:10px;'>Sekme: {sheet_name}</h3>"
                html_content += df.to_html(index=False, classes="data-table", justify="left")
            html_content += "</div>"
            style = "<style>.data-table { width:100%; border-collapse: collapse; margin-top:10px; font-size: 13px; } .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; } .data-table th { background-color: #f8f9fa; color: #333; font-weight: 600; }</style>"
            return style + html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
            
    except Exception as e:
        return f"<div style='color:red; text-align:center;'>Dosya işleme hatası: {str(e)}</div>", 500
    
    return f"<div style='color:red; text-align:center;'>Desteklenmeyen dosya formatı: {ext}</div>", 400

# ============================================
# HİYERARŞİK AĞAÇ YAPISI
# ============================================
@app.route('/api/tree/gozlem')
@login_required
def gozlem_tree():
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
    cur.execute("SELECT il, ilce, hastane_adi, COUNT(*) as kayit_sayisi FROM gozlem_formlari GROUP BY il, ilce, hastane_adi")
    raporlar = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    tree = {}
    for il, ilce, hastane in all_hospitals:
        if not il: continue
        if il not in tree: tree[il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in tree[il]: tree[il][ilce_key] = []
        count = raporlar.get((il, ilce, hastane), 0)
        tree[il][ilce_key].append({'hastane': hastane, 'kayit_sayisi': count})
    cur.close()
    conn.close()
    return jsonify(tree)

@app.route('/api/tree/komite')
@login_required
def komite_tree():
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
    cur.execute("SELECT il, ilce, hastane_adi, rapor_tipi, COUNT(*) as rapor_sayisi FROM komite_raporlari GROUP BY il, ilce, hastane_adi, rapor_tipi")
    raporlar = {}
    for il, ilce, hastane, tip, count in cur.fetchall():
        key = (il, ilce, hastane)
        if key not in raporlar: raporlar[key] = []
        raporlar[key].append({'tip': tip, 'count': count})
    tree = {}
    for il, ilce, hastane in all_hospitals:
        if not il: continue
        if il not in tree: tree[il] = {}
        ilce_key = ilce or 'Belirtilmemiş'
        if ilce_key not in tree[il]: tree[il][ilce_key] = []
        key = (il, ilce, hastane)
        rapor_verisi = raporlar.get(key, [])
        if not rapor_verisi:
            tree[il][ilce_key].append({'hastane': hastane, 'rapor_tipi': 'Yok', 'rapor_sayisi': 0})
        else:
            for rv in rapor_verisi:
                tree[il][ilce_key].append({'hastane': hastane, 'rapor_tipi': rv['tip'], 'rapor_sayisi': rv['count']})
    cur.close()
    conn.close()
    return jsonify(tree)

# ============================================
# GELİŞİM PLANLARI ENDPOINTLERİ
# ============================================
@app.route('/api/gelisim/list')
@login_required
def gelisim_list():
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
    query += " ORDER BY il ASC, hastane_adi ASC, id ASC"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    cur.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    rows = [serialize_row(row, columns) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'data': rows, 'total': total, 'page': page, 'per_page': per_page, 'total_pages': (total + per_page - 1) // per_page})

@app.route('/api/tree/gelisim')
@login_required
def gelisim_tree():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT il, hastane_adi, COUNT(*) as kayit_sayisi FROM gelisim_planlari GROUP BY il, hastane_adi ORDER BY il, hastane_adi")
    tree = {}
    for il, hastane, count in cur.fetchall():
        if not il: continue
        if il not in tree: tree[il] = []
        tree[il].append({'hastane': hastane, 'kayit_sayisi': count})
    cur.close()
    conn.close()
    return jsonify(tree)

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
    cur.execute(f"SELECT DISTINCT ilce FROM gelisim_planlari WHERE il = %s AND ilce IS NOT NULL ORDER BY ilce", (il,))
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
    if il:
        query += " AND il = %s"
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT il, COUNT(*) as count FROM gelisim_planlari WHERE il IS NOT NULL AND il != '' GROUP BY il")
    stats = {}
    for il, count in cur.fetchall():
        norm_il = map_normalize(il)
        stats[norm_il] = stats.get(norm_il, 0) + count
    cur.close()
    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
