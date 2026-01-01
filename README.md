# 🧠 AI Process Manager (AI Süreç Yöneticisi)

**AI Process Manager**, bilgisayarınızda çalışan işlemleri (process) listeleyen, yapay zeka (Google Gemini) desteğiyle güvenlik analizi yapan ve şüpheli yazılımları tespit etmenize yardımcı olan modern bir görev yöneticisidir.

![AI Process Manager Screenshot](https://via.placeholder.com/800x450?text=AI+Process+Manager+Interface)

## 🚀 Özellikler

*   **🔍 Akıllı İşlem Listesi:**
    *   Tüm çalışan işlemleri (PID, İsim, RAM kullanımı) anlık olarak listeler.
    *   İsme, Bellek kullanımına veya PID'ye göre sıralama (Artan/Azalan).
    *   Hızlı arama filtresi.
    
*   **🤖 Yapay Zeka Destekli Analiz:**
    *   Seçilen işlemi **Google Gemini AI** motoruna gönderir.
    *   **Dosya Hash (SHA256)** ve **Dijital İmza** kontrolü yapar.
    *   VirusTotal ve Global Tehdit İstihbaratı simülasyonu ile risk skoru belirler.
    *   Sonuçları: Kimlik, Risk Skoru, Güvenlik Analizi ve Bellek Yorumu olarak raporlar.

*   **💾 Akıllı Önbellek (Smart Caching):**
    *   Analiz sonuçlarını **SQLite Veritabanında** (`process_audit.db`) saklar.
    *   Aynı dosya tekrar açıldığında API harcamaz, eski sonucu (RAM bilgisini güncelleyerek) gösterir.
    *   **"Yeniden Analiz"** butonu ile cache atlanıp taze tarama yapılabilir.

*   **⚙️ Kolay API Yönetimi:**
    *   Program içinden API anahtarınızı güvenle kaydedebilirsiniz.
    *   Anahtar yerel veritabanında saklanır.

*   **🌍 Çoklu Dil Desteği:**
    *   Türkçe (TR) ve İngilizce (EN) dil seçenekleri.

*   **🛠️ İşlem Yönetimi:**
    *   Dosya konumunu açma.
    *   İşlemi sonlandırma (Kill Process).

*   **📝 Loglama Sistemi:**
    *   Tüm sistem çıktıları `app_log.txt` dosyasına kaydedilir (Terminal kirliliği yaratmaz).

---

## 📦 Kurulum ve Kullanım



Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```
*(Eğer requirements.txt yoksa manuel olarak: `customtkinter`, `psutil`, `requests`, `pywin32`, `Pillow`)*

Uygulamayı başlatın:
```bash
python main.py
```

---


## 📚 Kullanılan Teknolojiler

*   **Python 3.12+**
*   **UI:** CustomTkinter (Modern Arayüz)
*   **Sistem:** Psutil, PyWin32 (Windows API)
*   **AI:** Google Generative AI (Gemini Flash Modelleri)
*   **Veritabanı:** SQLite3
*   **Paketleme:** PyInstaller

---

## ⚠️ Yasal Uyarı
Bu program sadece sistem analizi ve bilgilendirme amaçlıdır. "Zararlı" olarak işaretlenen dosyaları silmeden önce mutlaka kendi kontrolünüzü yapınız. AI hatalı pozitif (false positive) sonuçlar verebilir.
