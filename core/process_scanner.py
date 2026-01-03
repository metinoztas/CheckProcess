import psutil
import hashlib
import os
import win32ui
import win32gui
import win32con
import subprocess
from PIL import Image

class ProcessScanner:
    def get_running_processes(self):
        """
        Sistemde çalışan işlemleri listeler.
        Dönen liste şunları içerir: pid, name, memory_info
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'create_time', 'username']):
            try:
                p_info = proc.info
                # Bellek kullanımını MB cinsine çevir
                mem_mb = p_info['memory_info'].rss / (1024 * 1024)
                p_info['memory_mb'] = f"{mem_mb:.2f} MB"
                
                processes.append(p_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # İsme göre sırala
        return sorted(processes, key=lambda x: x['name'].lower())

    def get_process_icon(self, pid):
        """
        İşlem ikonunu alır. Önce ExtractIconEx (daha hızlı/uyumlu) dener,
        olmazsa SHGetFileInfo (daha kapsamlı) dener.
        """
        try:
            try:
                proc = psutil.Process(pid)
                path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                return None
            
            if not path:
                return None

            # YÖNTEM 1: ExtractIconEx (Eski ve güvenilir yöntem)
            hicon = None
            try:
                large, small = win32gui.ExtractIconEx(path, 0)
                if large:
                    hicon = large[0]
                    # small varsa temizle
                    if small: win32gui.DestroyIcon(small[0])
                    # large'ın geri kalanını temizle
                    for h in large[1:]: win32gui.DestroyIcon(h)
                elif small:
                    hicon = small[0]
                    for h in small[1:]: win32gui.DestroyIcon(h)
            except:
                pass

            # YÖNTEM 2: SHGetFileInfo (Yedek)
            if not hicon:
                try:
                    flags = win32con.SHGFI_ICON | win32con.SHGFI_LARGEICON
                    retval, info = win32gui.SHGetFileInfo(path, 0, flags)
                    if info and info[0]:
                        hicon = info[0]
                except:
                    pass

            if not hicon:
                return None

            # HICON -> PIL Image Dönüştürme
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
            
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            
            # Çiz
            win32gui.DrawIconEx(hdc_mem.GetHandleOutput(), 0, 0, hicon, 32, 32, 0, 0, 3) 

            # Bitmap verisini al
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1)

            img = img.copy()
            
            # Temizlik
            win32gui.DestroyIcon(hicon)
            win32gui.DeleteObject(hbmp.GetHandle())
            hdc_mem.DeleteDC()
            hdc.DeleteDC()
            
            return img

        except Exception:
            return None

    def get_process_details(self, pid):
        """
        PID'si verilen işlemin detaylı bilgilerini (Dosya Yolu) getirir.
        Hız için Hash ve İmza şimdilik devre dışı bırakıldı.
        """
        details = {"path": "Bilinmiyor", "hash": "-", "signature": "-"}
        try:
            p = psutil.Process(pid)
            path = p.exe() # En önemli bilgi
            if path:
                details["path"] = path
                # İmza kontrolü açık (Timeout korumalı)
                details["signature"] = self._check_digital_signature(path)
                # Hash açık (VirusTotal tarzi analiz için şart)
                details["hash"] = self._calculate_file_hash(path)
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return details

    def _calculate_file_hash(self, filepath):
        """Bir dosyanın SHA256 özetini çıkarır. (Max 100MB)"""
        try:
            # Dosya boyutu kontrolü (100MB üzeri ise hesaplama)
            if os.path.getsize(filepath) > 100 * 1024 * 1024:
                return "Dosya Çok Büyük (>100MB) - Hash Atlandı"

            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except:
            return None

    def _check_digital_signature(self, filepath):
        """PowerShell kullanarak dijital imzayı kontrol eder. (Timeout: 2s)"""
        try:
            cmd = [
                "powershell", 
                "-NoProfile", 
                "-Command", 
                f"Get-AuthenticodeSignature -FilePath '{filepath}' | Select-Object -ExpandProperty Status"
            ]
            
            # Pencere açılmasını önle
            creationflags = 0x08000000 # CREATE_NO_WINDOW
            
            # Subprocess ile çalıştır ve zaman aşımı ekle (1.5 sn yeterli)
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=1.5, 
                creationflags=creationflags
            )
            status = result.stdout.strip()
            
            if "Valid" in status:
                return "Geçerli (Doğrulanmış)"
            elif "NotSigned" in status:
                return "İmzasız"
            elif "HashMismatch" in status:
                return "İmza Bozuk (RİSKLİ)"
            elif "NotTrusted" in status:
                return "Güvenilmeyen Sertifika"
            else:
                return f"Durum: {status}" if status else "Bilinmiyor"
                
        except subprocess.TimeoutExpired:
            return "Kontrol Zaman Aşımı"
        except Exception:
            return "Kontrol Edilemedi"

    def kill_process(self, pid):
        """Verilen PID'ye sahip işlemi sonlandırır."""
        try:
            p = psutil.Process(pid)
            p.terminate()  # veya p.kill()
            return True, "İşlem sonlandırıldı."
        except psutil.NoSuchProcess:
            return False, "İşlem bulunamadı."
        except psutil.AccessDenied:
            return False, "Erişim reddedildi. Yönetici hakları gerekebilir."
        except Exception as e:
            return False, f"Hata: {str(e)}"

    def get_process_path(self, pid):
        """PID'den dosya yolunu bulur."""
        try:
            p = psutil.Process(pid)
            return p.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
