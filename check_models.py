import requests
import json
import sqlite3
import os

def get_api_key():
    db_path = "process_audit.db"
    if not os.path.exists(db_path):
        print("⚠️ Veritabanı bulunamadı. Önce main.py'yi çalıştırıp API anahtarını kaydedin.")
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'gemini_api_key'")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
        else:
            print("⚠️ API Anahtarı veritabanında bulunamadı.")
            return None
    except Exception as e:
        print(f"⚠️ Veritabanı Hatası: {e}")
        return None

def check_models():
    api_key = get_api_key()
    if not api_key:
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print(f"🚀 Modeller sorgulanıyor... (Key sonu: ...{api_key[-4:]})")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print("\n✅ KULLANILABİLİR MODELLER:")
            found_count = 0
            for m in models:
                # Sadece içerik üretimi yapan modelleri filtrele
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # Sadece gemini modellerini göster
                    if 'gemini' in m['name'].lower():
                        print(f"  - {m['name'].replace('models/', '')}")
                        found_count += 1
            
            if found_count == 0:
                print("  (Hiçbir 'gemini' modeli bulunamadı)")
        else:
            print(f"❌ API Hatası: {response.status_code}")
            print(f"Detay: {response.text}")

    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")

if __name__ == "__main__":
    import sys
    import datetime

    class Logger(object):
        def __init__(self, filename="app_log.txt"):
            self.log = open(filename, "a", encoding="utf-8")
    
        def write(self, message):
            if message.strip():
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # [ModelCheck] ön ekiyle logla
                self.log.write(f"[{timestamp}] [ModelCheck] {message.strip()}\n")
                self.log.flush()
            
        def flush(self):
            self.log.flush()

    # Terminal çıktısını dosyaya yönlendir
    sys.stdout = Logger()
    sys.stderr = sys.stdout

    check_models()
