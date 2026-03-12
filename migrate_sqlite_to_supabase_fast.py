# -*- coding: utf-8 -*-
import sqlite3
import psycopg2
import psycopg2.extras
import os

def migrate():
    # Supabase connection
    db_url = "postgresql://postgres.casbkhujugmibpybhmvm:LLpp1594369*@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
    sqlite_path = r'c:\Users\EMİRKAN SUNGUR\Desktop\STDS_RAPORLAR\stds.db'
    
    print(f"Migration starting: Local SQLite -> Cloud Supabase")
    
    try:
        src_conn = sqlite3.connect(sqlite_path)
        src_conn.row_factory = sqlite3.Row
        src_cur = src_conn.cursor()
        
        tgt_conn = psycopg2.connect(db_url)
        tgt_cur = tgt_conn.cursor()

        tables = [
            'referans_hastaneler', 
            'gozlem_formlari', 
            'komite_raporlari', 
            'standart_degerlendirmeler', 
            'komisyon_kararlari',
            'gozlem_gorselleri',
            'gelisim_planlari'
        ]

        for table in tables:
            print(f"Migrating table: {table}...")
            
            # 1. Check if table exists in SQLite
            src_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not src_cur.fetchone():
                print(f"  {table} does not exist in SQLite, skipping.")
                continue

            # 2. Get data from SQLite
            src_cur.execute(f"SELECT * FROM {table}")
            rows = src_cur.fetchall()
            
            if not rows:
                print(f"  No data in {table}, skipping.")
                continue

            # 3. Clean target table in Supabase
            print(f"  Cleaning {table} in Supabase...")
            tgt_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            
            # 4. Prepare insertion
            col_names = rows[0].keys()
            col_str = ", ".join(col_names)
            insert_query = f"INSERT INTO {table} ({col_str}) VALUES %s"
            
            # Convert SQLite Row objects to tuples for psycopg2
            data_to_insert = [tuple(row) for row in rows]
            
            # 5. Execute batch insertion
            print(f"  Inserting {len(data_to_insert)} rows...")
            psycopg2.extras.execute_values(tgt_cur, insert_query, data_to_insert)
            print(f"  Successfully migrated {table}.")

        tgt_conn.commit()
        print("\nSUCCESS: MIGRATION COMPLETED!")
        
        src_conn.close()
        tgt_conn.close()
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        if 'tgt_conn' in locals():
            tgt_conn.rollback()

if __name__ == "__main__":
    migrate()
