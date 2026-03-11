# -*- coding: utf-8 -*-
"""
STDS Raporlar - Admin Kullanıcısı Tanımlama
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import SQLITE_DB_PATH, USE_SQLITE

def seed_admin():
    print("Admin kullanıcısı tanımlanıyor...")
    
    username = "emirkan.sungur@saglik.gov.tr"
    password = "LLpp369*"
    role = "admin"
    
    password_hash = generate_password_hash(password)
    
    if USE_SQLITE:
        conn = sqlite3.connect(SQLITE_DB_PATH)
    else:
        # PostgreSQL logic if needed
        import psycopg2
        from config import DB_CONFIG
        conn = psycopg2.connect(**DB_CONFIG)
        
    cur = conn.cursor()
    
    # Tabloyu oluştur
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Mevcut kullanıcıyı kontrol et
    cur.execute("SELECT id FROM users WHERE username = ?", (username,) if USE_SQLITE else (username,))
    if cur.fetchone():
        print(f"Kullanıcı zaten mevcut: {username}")
        # Şifre güncellemesi yapalım
        if USE_SQLITE:
            cur.execute("UPDATE users SET password_hash = ?, role = ? WHERE username = ?", (password_hash, role, username))
        else:
            cur.execute("UPDATE users SET password_hash = %s, role = %s WHERE username = %s", (password_hash, role, username))
        print("Şifre güncellendi.")
    else:
        if USE_SQLITE:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
        else:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", (username, password_hash, role))
        print(f"Admin başarıyla oluşturuldu: {username}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_admin()
