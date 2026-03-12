# -*- coding: utf-8 -*-
import os
import time
import re
from supabase import create_client, Client

# Configuration
SUPABASE_URL = "https://casbkhujugmibpybhmvm.supabase.co"
SUPABASE_KEY = "sb_secret_kkqvW8fy_qwGEeTSUjPVeA_9V1KxGh3"

LOCAL_REPORTS_DIR = r"c:\Users\EMİRKAN SUNGUR\Desktop\RAPORLAR_FINAL_TMP\KOMİTE KOMİSYON RAPORLARI"
LOCAL_IMAGES_DIR = r"c:\Users\EMİRKAN SUNGUR\Desktop\RAPORLAR_FINAL_TMP\GÖZLEM FORMLARI\İL GÖRSELLERİ"

BUCKET_RAPORLAR = "stds_raporlar"
BUCKET_GORSELLER = "stds_gorseller"

RETRY_COUNT = 3
DELAY_BETWEEN_UPLOADS = 0.2 # Seconds

def normalize_storage_path(path):
    """Normalize path for Supabase Storage (ASCII only, no special chars)"""
    trans = str.maketrans("çğışüöÇĞİŞÜÖı", "cgisuoCGISUOi")
    path = str(path).translate(trans)
    path = "".join(c for c in path if ord(c) < 128)
    return path

def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file_sequential(file_path, bucket_name, storage_path, client):
    """Single file upload with retries"""
    for attempt in range(RETRY_COUNT):
        try:
            with open(file_path, 'rb') as f:
                client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"upsert": "true"}
                )
            return True, "OK"
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg:
                return True, "EXISTS"
            if attempt < RETRY_COUNT - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return False, str(e)
    return False, "Max retries reached"

def upload_directory_sequential(local_dir, bucket_name):
    print(f"\nProcessing {local_dir}...")
    if not os.path.exists(local_dir):
        print(f"Directory not found: {local_dir}")
        return

    client = get_client()
    files_to_upload = []
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, local_dir)
            storage_path = normalize_storage_path(rel_path).replace("\\", "/")
            files_to_upload.append((file_path, storage_path))

    total = len(files_to_upload)
    print(f"Found {total} files. Starting sequential upload with safety delays...")

    for i, (file_path, storage_path) in enumerate(files_to_upload):
        success, status = upload_file_sequential(file_path, bucket_name, storage_path, client)
        
        if (i + 1) % 20 == 0 or not success:
            print(f"[{i+1}/{total}] {storage_path} -> {status}")
        
        if not success:
            # If a major error occurs, wait longer and try to get a fresh client
            print("Refreshing client due to error...")
            time.sleep(5)
            client = get_client()
            
        time.sleep(DELAY_BETWEEN_UPLOADS)

if __name__ == "__main__":
    # Upload Images FIRST (Less files, restores UI quickly)
    upload_directory_sequential(LOCAL_IMAGES_DIR, BUCKET_GORSELLER)
    # Upload Reports (High volume, continues in background)
    upload_directory_sequential(LOCAL_REPORTS_DIR, BUCKET_RAPORLAR)
    print("\nALL OPERATIONS COMPLETED!")
