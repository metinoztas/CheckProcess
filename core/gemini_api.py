import requests
import json
import time
import sqlite3
import threading
from datetime import datetime

class GeminiAnalyzer:
    def __init__(self):
        # SQL Veritabanı
        self.db_path = "process_audit.db"
        self._init_db()
        
        # API Anahtarını Veritabanından Yükle
        self.api_key = self.get_saved_api_key()
        
        # Modeller (Sırasıyla denenecek)
        self.models = [
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash-lite",   
            "gemini-2.5-flash",
            "gemini-1.5-flash"
        ]

    def _connect_db(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            # Analiz tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_analysis (
                    cache_key TEXT PRIMARY KEY,
                    process_name TEXT,
                    file_path TEXT,
                    signature TEXT,
                    risk_score TEXT,
                    analysis_json TEXT,
                    updated_at DATETIME
                )
            ''')
            # Ayarlar tablosu (API Key vb.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()
            conn.close()
            print(f"✅ SQL Veritabanı Hazır: {self.db_path}")
        except Exception as e:
            print(f"⚠️ Veritabanı Hatası: {e}")

    def get_saved_api_key(self):
        """Veritabanından kayıtlı API anahtarını getirir."""
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = 'gemini_api_key'")
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception:
            return None
        return None

    def set_api_key(self, key):
        """Yeni API anahtarını kaydeder."""
        try:
            self.api_key = key
            conn = self._connect_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('gemini_api_key', ?)", (key,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"API Key Kayıt Hatası: {e}")
            return False

    def _get_from_db(self, cache_key):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT analysis_json FROM process_analysis WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception:
            return None
        return None

    def _save_to_db(self, cache_key, proc_info, analysis_data):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            analysis_json = json.dumps(analysis_data)
            
            cursor.execute('''
                INSERT OR REPLACE INTO process_analysis 
                (cache_key, process_name, file_path, signature, risk_score, analysis_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                cache_key, 
                proc_info.get('name'), 
                proc_info.get('path'), 
                proc_info.get('signature'), 
                analysis_data.get('risk_skoru'), 
                analysis_json, 
                now
            ))
            conn.commit()
            conn.close()
            print(f"💾 Veritabanına Kaydedildi: {proc_info.get('name')}")
        except Exception as e:
            print(f"⚠️ DB Kayıt Hatası: {e}")

    def _call_api(self, model, prompt):
        if not self.api_key:
            return None # API Key yoksa deneme bile
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text']
            return None
        except:
            return None

    def _get_best_response(self, prompt):
        if not self.api_key:
            return None, "API Anahtarı Eksik. Lütfen Ayarlar'dan ekleyiniz."

        last_error = None
        for model in self.models:
            print(f"🚀 İstek Gönderiliyor: {model}...")
            text = self._call_api(model, prompt)
            if text:
                print(f"✅ Başarılı Model: {model}")
                return text, None
            print(f"⚠️ {model} BULUNAMADI/HATA. Sonraki...")
            time.sleep(1) # Hızlı retry
            
        return None, "Tüm modeller başarısız."

    def _get_by_path_and_lang(self, path, lang):
        """Dosya yolu ve dile göre veritabanında eski analiz var mı bakar (PID değişse bile)."""
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            # En son analiz edileni getir
            cursor.execute("SELECT analysis_json, cache_key FROM process_analysis WHERE file_path = ? ORDER BY updated_at DESC", (path,))
            rows = cursor.fetchall()
            conn.close()
            
            # Dile uygun olanı bul (Cache key içinde dil kodu var mı?)
            search_tag = f"|{lang}|"
            for row in rows:
                json_data, key = row
                if search_tag in key:
                    return json.loads(json_data)
        except Exception:
            pass
        return None

    def analyze_single_process(self, process_info, lang="TR", force_refresh=False):
        """
        Tek bir işlemi detaylı analiz eder (SQL Cache + Multi-Model).
        """
        path = process_info.get('path', 'Bilinmiyor')
        signature = process_info.get('signature', 'Bilinmiyor')
        name = process_info.get('name', 'bilinmiyor')
        c_pid = str(process_info.get('pid', '0'))
        
        # 1. CACHE KONTROLÜ (Tam Eşleşme: PID Dahil)
        c_name = name.strip()
        c_path = path.strip()
        c_sign = signature.strip()
        c_lang = lang.strip()
        
        cache_key = f"{c_name}|{c_path}|{c_sign}|{c_lang}|{c_pid}"
        print(f"🔑 Cache Key (PID Veritabanı): {cache_key}")
        
        if not force_refresh:
            # A) Tam PID eşleşmesi var mı? (Oturum içi hız)
            cached_result = self._get_from_db(cache_key)
            if cached_result:
                print(f"📦 SQL Veritabanından Getirildi (Tam Eşleşme): {name}")
                return cached_result
    
            # B) Dosya daha önce analiz edilmiş mi? (PID değişse bile kurtar)
            if c_path and c_path != "Bilinmiyor":
                prev_result = self._get_by_path_and_lang(c_path, c_lang)
                if prev_result:
                    print(f"📦 SQL Veritabanından Getirildi (Dosya/Hash Eşleşmesi): {name}")
                    # Eski analizi kullan ama bu yeni PID için de kaydet ki bir dahaki sefere daha hızlı olsun
                    self._save_to_db(cache_key, process_info, prev_result)
                    
                    # Bellek bilgisini güncelle
                    mem_note = "(Current Value)" if lang == "EN" else "(Güncel Değer)"
                    prev_result['bellek_analizi'] = f"{process_info.get('memory_mb', '?')} {mem_note}"
                    return prev_result
        else:
             print(f"🔄 ZORLA YENİLEME: Cache atlanıyor... ({name})")

        file_hash = process_info.get('hash', 'Hesaplanamadı')

        if lang == "EN":
             prompt = f"""
            **ROLE:** You represent the engine of VirusTotal and major Thread Intelligence databases.
            **TASK:** Perform a deep security audit of the process using the **SHA256 HASH** and **Digital Signature**.

            **TARGET PROCESS:**
            - Name: {name} (PID: {process_info.get('pid')})
            - Path: {path}
            - SHA256 HASH: {file_hash}
            - Digital Signature: {signature}
            - Memory: {process_info.get('memory_mb')}
            
            **ANALYSIS RULES:**
            1. **HASH CHECK:** Check this SHA256 hash against your knowledge base of known good/bad files.
            2. **SIGNATURE CHECK:** If the signature is invalid or missing, increase Risk Score.
            3. **BEHAVIOR:** If the path is suspicious (e.g. Temp folder, mimicking system files), flag it.
            4. **FILE.NET CHECK:** Cross-reference with `file.net` database.
            5. **COMMUNITY FEEDBACK:** Check discussions on Reddit, Microsoft Community, etc.
            
            **OUTPUT:**
            Return strict JSON format:
            {{
                "kimlik": "Official identification based on Hash, Path and community info. Use **bold** for app name.",
                "risk_skoru": "X/10",
                "guvenlik_analizi": "Detailed threat report. Highlight key risks/safety factors with **bold** (e.g. **Hash Malicious**, **Signed**).",
                "bellek_analizi": "Memory usage analysis.",
                "sonuc": "Safe / Suspicious / Dangerous"
            }}
            """
        else:
            prompt = f"""
            **ROL:** Sen VirusTotal ve Küresel Tehdit İstihbarat (Threat Intel) motorusun.
            **GÖREV:** Verilen işlemi **SHA256 HASH**, **Dijital İmza**, **file.net** ve **Topluluk Yorumlarına** dayanarak derinlemesine tara.

            **HEDEF İŞLEM:**
            - Adı: {name} (PID: {process_info.get('pid')})
            - Dosya Yolu: {path}
            - SHA256 HASH: {file_hash}
            - Dijital İmza: {signature}
            - Bellek: {process_info.get('memory_mb')}
            
            **ANALİZ KURALLARI:**
            1. **HASH KONTROLÜ:** Bu SHA256 değerini veritabanındaki bilinen zararlı/temiz dosyalarla karşılaştır.
            2. **İMZA KONTROLÜ:** İmza yoksa veya geçersizse risk puanını artır.
            3. **DAVRANIŞ/KONUM:** Dosya yolu şüpheliyse (Temp, System32 taklidi vb.) uyar.
            4. **FILE.NET KONTROLÜ:** İşlem adını `file.net` veri tabanındaki bilgilerle karşılaştır.
            5. **TOPLULUK VE FORUM ANALİZİ:** Reddit, Technopat, Microsoft Community vb. forumlardaki kullanıcı yorumlarını ve şikayetlerini baz al.
            
            **ÇIKTI (SADECE JSON):**
            {{
                "kimlik": "Hash, yol, file.net ve forum bilgilerine dayalı detaylı yazılım kimliği. Uygulama adını **kalın** yaz.",
                "risk_skoru": "X/10 (1: Çok Güvenli - 10: Çok Tehlikeli)",
                "guvenlik_analizi": "İmza, Hash, File.net ve Forum yorumlarını içeren kapsamlı güvenlik raporu. Önemli uyarıları **kalın** ile vurgula (örn: **RİSKLİ**, **İMZALI**, **System32**).",
                "bellek_analizi": "Bellek kullanım yorumu.",
                "sonuc": "Güvenli / Şüpheli / Tehlikeli"
            }}
            """
        
        # Modelleri sırayla dene
        text, error = self._get_best_response(prompt)
        
        if error:
            print("❌ Hiçbir AI modeli yanıt vermedi. Yerel Analiz yapılıyor.")
            return self._local_analysis(process_info, lang)
        
        try:
            clean_text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            self._save_to_db(cache_key, process_info, data)
            return data
        except json.JSONDecodeError:
            return self._local_analysis(process_info, lang)

    def _local_analysis(self, p, lang="TR"):
        """API çalışmadığında devreye giren basit kurallı analiz."""
        path = p.get('path', '')
        sign = p.get('signature', '')
        riskscore = "5/10"
        
        if lang == "EN":
            result_txt = "Unknown (Local)"
            desc = "Offline analysis."
            if "Valid" in sign:
                riskscore = "2/10"
                result_txt = "Safe (Signed)"
            elif "NotSigned" in sign:
                riskscore = "8/10"
                result_txt = "RISKY"
        else:
            result_txt = "Bilinmiyor (Yerel)"
            desc = "Çevrimdışı analiz."
            if "Geçerli" in sign:
                riskscore = "2/10"
                result_txt = "Güvenli (İmzalı)"
            elif "İmzasız" in sign:
                riskscore = "8/10"
                result_txt = "RİSKLİ (İmzasız)"

        return {
            "kimlik": f"{p.get('name')} (Offline)",
            "risk_skoru": riskscore,
            "guvenlik_analizi": desc,
            "bellek_analizi": f"{p.get('memory_mb')}",
            "sonuc": result_txt
        }
