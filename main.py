import customtkinter as ctk
import psutil
import threading
import tkinter as tk
from tkinter import messagebox
import os
import subprocess
from core.gemini_api import GeminiAnalyzer
from core.process_scanner import ProcessScanner
from core.languages import Language 

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AI Process Manager")
        self.geometry("1100x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Dil Ayarları
        self.current_lang = "TR"
        self.loc = Language.TR

        # Araçlar
        self.scanner = ProcessScanner()
        self.gemini = GeminiAnalyzer()
        
        # Değişkenler
        self.full_process_list = []
        self.selected_pid = None
        self.selected_proc_name = None
        self.current_icon = None
        self.icon_cache = {} 
        
        # Sıralama: name, mem, pid
        self.sort_col = "name"
        self.sort_desc = False

        self._init_ui()

    def _init_ui(self):
        # --- SOL PANEL: Liste ---
        self.left_frame = ctk.CTkFrame(self, width=350, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_rowconfigure(3, weight=1) # Scroll frame index kaydı (Header eklenince)

        # Başlık ve Butonlar
        self.header_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(self.header_frame, text=self.loc["title"], font=("Roboto", 18, "bold"))
        self.lbl_title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(self.header_frame, text="⟳", width=30, height=25, command=self.refresh_process_list)
        self.btn_refresh.pack(side="right", padx=(5,0))

        # API Butonu
        self.btn_api = ctk.CTkButton(self.header_frame, text=self.loc["api_btn"], width=70, height=25, fg_color="#F57C00", hover_color="#E65100", command=self.open_api_settings)
        self.btn_api.pack(side="right", padx=5)

        # Dil Butonu
        self.btn_lang = ctk.CTkButton(self.header_frame, text="EN", width=30, height=25, fg_color="#444444", command=self.toggle_language)
        self.btn_lang.pack(side="right")
        
        # Arama Alanı
        self.search_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.search_container.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        self.search_entry = ctk.CTkEntry(self.search_container, placeholder_text=self.loc["search_placeholder"], height=28, font=("Roboto", 12))
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self.filter_process_list)
        
        self.btn_clear_search = ctk.CTkButton(self.search_container, text="✕", width=28, height=28, fg_color="transparent", hover_color="#444444", text_color="#AAAAAA", command=self.clear_search)
        self.btn_clear_search.pack(side="right", padx=(5, 0))

        # --- KOLON BAŞLIKLARI (SIRALAMA İÇİN) ---
        self.list_header_frame = ctk.CTkFrame(self.left_frame, height=30, fg_color="transparent")
        self.list_header_frame.grid(row=2, column=0, padx=10, pady=0, sticky="ew")
        
        # Buton genişlikleri liste elemanlarındaki karakter sayılarına göre ayarlandı (Consolas font)
        # PID: ~7 char -> 65px
        self.btn_h_pid = ctk.CTkButton(self.list_header_frame, text=self.loc["col_pid"], width=65, height=24, 
                                       fg_color="#333333", hover_color="#444444", font=("Roboto", 11, "bold"),
                                       command=self.sort_by_pid)
        self.btn_h_pid.pack(side="left", padx=(0, 2))
        
        # Name: Esnek
        self.btn_h_name = ctk.CTkButton(self.list_header_frame, text=self.loc["col_name"], height=24, 
                                        fg_color="#333333", hover_color="#444444", font=("Roboto", 11, "bold"),
                                        command=self.sort_by_name)
        self.btn_h_name.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        # Memory: ~90px
        self.btn_h_mem = ctk.CTkButton(self.list_header_frame, text=self.loc["col_mem"], width=90, height=24,
                                       fg_color="#333333", hover_color="#444444", font=("Roboto", 11, "bold"),
                                       command=self.sort_by_mem)
        self.btn_h_mem.pack(side="left")

        # Liste (Label Text kaldırıldı, headerlar yukarı taşındı)
        self.scroll_frame = ctk.CTkScrollableFrame(self.left_frame, width=340)
        self.scroll_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        # --- SAĞ PANEL ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_rowconfigure(2, weight=1) 
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Detay Başlık
        self.lbl_detail_title = ctk.CTkLabel(self.right_frame, text=self.loc["detail_title"], font=("Roboto", 20, "bold"))
        self.lbl_detail_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Bilgi Alanı
        self.info_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        
        self.lbl_icon = ctk.CTkLabel(self.info_frame, text="?", width=64, height=64, fg_color="#333333", corner_radius=8)
        self.lbl_icon.grid(row=0, column=0, rowspan=3, padx=(0, 15))
        
        self.lbl_pid = ctk.CTkLabel(self.info_frame, text=self.loc["pid"], font=("Roboto", 14))
        self.lbl_pid.grid(row=0, column=1, sticky="w")
        
        self.lbl_name = ctk.CTkLabel(self.info_frame, text=self.loc["name"], font=("Roboto", 14))
        self.lbl_name.grid(row=1, column=1, sticky="w")
        
        self.lbl_mem = ctk.CTkLabel(self.info_frame, text=self.loc["memory"], font=("Roboto", 14))
        self.lbl_mem.grid(row=2, column=1, sticky="w")

        # Rapor Alanı
        self.details_scroll_frame = ctk.CTkScrollableFrame(self.right_frame, label_text=self.loc["card_result"])
        self.details_scroll_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # Butonlar
        self.actions_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.actions_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.btn_analyze = ctk.CTkButton(self.actions_frame, text=self.loc["analyze_btn"], fg_color="#7B1FA2", hover_color="#4A148C", command=self.on_analyze_click)
        self.btn_analyze.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self.btn_reanalyze = ctk.CTkButton(self.actions_frame, text=self.loc.get("reanalyze_btn", "Yeniden"), width=120, fg_color="#F9A825", hover_color="#C17900", command=self.on_force_analyze_click)
        self.btn_reanalyze.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ctk.CTkButton(self.actions_frame, text=self.loc["folder_btn"], fg_color="#0277BD", hover_color="#01579B", command=self.open_file_location)
        self.btn_open_folder.pack(side="left", padx=(0, 10))

        self.btn_kill = ctk.CTkButton(self.actions_frame, text=self.loc["kill_btn"], fg_color="#C62828", hover_color="#B71C1C", command=self.kill_selected_process)
        self.btn_kill.pack(side="right")

        self.refresh_process_list()
        
        # Başlangıçta API Key kontrolü
        self.after(1000, self.check_api_key)

    def check_api_key(self):
        """API anahtarı yoksa kullanıcıdan ister."""
        # Eğer key zaten varsa hiçbir şey yapma
        if self.gemini.api_key:
            return
            
        # Yoksa kullanıcıya sor
        self.open_api_settings()

    def open_api_settings(self):
        """API Ayarları Penceresi"""
        try:
            # Varsa eskisini kapat (Çift pencere olmasın)
            if hasattr(self, 'api_window') and self.api_window.winfo_exists():
                self.api_window.lift()
                return
        except:
            pass

        self.api_window = ctk.CTkToplevel(self)
        self.api_window.title(self.loc["api_title"])
        self.api_window.geometry("400x250")
        self.api_window.resizable(False, False)
        try:
            self.api_window.transient(self) # Ana pencereye bağlı
            self.api_window.grab_set() # Diğer pencereleri kilitle
        except:
            pass

        # Mevcut Durum Kontrolü
        current_key = self.gemini.api_key
        status_text = "✅ " + self.loc.get("api_success", "Active") if current_key else "❌ " + self.loc.get("api_missing", "Missing")
        status_color = "green" if current_key else "red"

        # Başlık
        lbl_info = ctk.CTkLabel(self.api_window, text=self.loc["api_label"], font=("Roboto", 14, "bold"))
        lbl_info.pack(pady=(15, 5))

        # Status
        lbl_stat = ctk.CTkLabel(self.api_window, text=status_text, text_color=status_color, font=("Roboto", 12))
        lbl_stat.pack(pady=(0, 10))

        # Entry
        self.api_entry = ctk.CTkEntry(self.api_window, width=320, placeholder_text="AIzaSy...")
        self.api_entry.pack(pady=5)
        
        # Varsa keyi göster
        if current_key:
            self.api_entry.insert(0, current_key)

        # Mesaj (Alt)
        self.lbl_msg = ctk.CTkLabel(self.api_window, text="", font=("Roboto", 11))
        self.lbl_msg.pack(pady=5)

        # Butonlar
        btn_frame = ctk.CTkFrame(self.api_window, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x")

        def save_action():
            key = self.api_entry.get().strip()
            if not key:
                self.lbl_msg.configure(text=self.loc["api_missing"], text_color="red")
                return
            
            if self.gemini.set_api_key(key):
                self.lbl_msg.configure(text=self.loc["api_success"], text_color="green")
                # Durumu güncelle
                lbl_stat.configure(text="✅ " + self.loc.get("api_saved", "Saved"), text_color="green")
                self.api_window.after(1000, self.api_window.destroy)
            else:
                self.lbl_msg.configure(text="Error saving key!", text_color="red")

        def cancel_action():
            self.api_window.destroy()

        # Kaydet Butonu
        btn_save = ctk.CTkButton(btn_frame, text=self.loc["api_save"], fg_color="#2E7D32", hover_color="#1B5E20", width=120, command=save_action)
        btn_save.pack(side="left", padx=(60, 10)) # Ortalama için padding

        # İptal/Kapat Butonu
        btn_cancel = ctk.CTkButton(btn_frame, text="Kapat", fg_color="#555555", hover_color="#333333", width=80, command=cancel_action)
        btn_cancel.pack(side="left")

    def sort_by_name(self):
        if self.sort_col == "name":
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = "name"
            self.sort_desc = False
        self.filter_process_list()
        self.update_ui_texts() # Ok işaretlerini güncellemek için

    def sort_by_mem(self):
        if self.sort_col == "mem":
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = "mem"
            self.sort_desc = True # Memory için default yüksekten düşüğe mantıklı
        self.filter_process_list()
        self.update_ui_texts()

    def sort_by_pid(self):
        if self.sort_col == "pid":
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = "pid"
            self.sort_desc = False
        self.filter_process_list()
        self.update_ui_texts()

    def toggle_language(self):
        if self.current_lang == "TR":
            self.current_lang = "EN"
            self.loc = Language.EN
            self.btn_lang.configure(text="TR")
        else:
            self.current_lang = "TR"
            self.loc = Language.TR
            self.btn_lang.configure(text="EN")
            
        self.update_ui_texts()

    def update_ui_texts(self):
        self.lbl_title.configure(text=self.loc["title"])
        self.search_entry.configure(placeholder_text=self.loc["search_placeholder"])
        self.btn_api.configure(text=self.loc["api_btn"])
        
        # Header + Oklar
        arrow = " ▼" if self.sort_desc else " ▲"
        
        t_pid = self.loc["col_pid"] + (arrow if self.sort_col == "pid" else "")
        t_name = self.loc["col_name"] + (arrow if self.sort_col == "name" else "")
        t_mem = self.loc["col_mem"] + (arrow if self.sort_col == "mem" else "")
        
        self.btn_h_pid.configure(text=t_pid)
        self.btn_h_name.configure(text=t_name)
        self.btn_h_mem.configure(text=t_mem)
        
        self.lbl_detail_title.configure(text=self.loc["detail_title"])
        self.lbl_pid.configure(text=self.loc["pid"] if not self.selected_pid else f"PID: {self.selected_pid}")
        self.lbl_name.configure(text=self.loc["name"] if not self.selected_pid else f"{'Name' if self.current_lang=='EN' else 'Ad'}: {self.selected_proc_name}")
        self.btn_analyze.configure(text=self.loc["analyze_btn"])
        self.btn_reanalyze.configure(text=self.loc.get("reanalyze_btn", "Yeniden"))
        self.btn_open_folder.configure(text=self.loc["folder_btn"])
        self.btn_kill.configure(text=self.loc["kill_btn"])
        self.details_scroll_frame.configure(label_text=self.loc["card_result"])
        
        # Eğer henüz analiz yapılmadıysa başlangıç mesajını güncelle
        if not self.details_scroll_frame.winfo_children():
             pass 
        else:
             # İçerik varsa ve analiz henüz yapılmadıysa (sadece label varsa)
             children = self.details_scroll_frame.winfo_children()
             if len(children) == 1 and isinstance(children[0], ctk.CTkLabel):
                  children[0].configure(text=self.loc["start_msg"])

    def clear_search(self):
        self.search_entry.delete(0, 'end')
        self.filter_process_list()

    def refresh_process_list(self):
        # Tüm listeyi çek ve sakla
        self.full_process_list = self.scanner.get_running_processes()
        # Filtrele ve göster
        self.filter_process_list()

    def filter_process_list(self, event=None):
        # Arama metnini al
        query = self.search_entry.get().lower()
        
        # UI temizle
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Filtreleme
        display_list = [p for p in self.full_process_list if (query in p['name'].lower() or query in str(p['pid'])) and p['name']]
        
        # SIRALAMA
        if self.sort_col == "name":
            display_list.sort(key=lambda x: x['name'].lower(), reverse=self.sort_desc)
        elif self.sort_col == "mem":
            # memory_info.rss (byte) üzerinden sırala
            display_list.sort(key=lambda x: x['memory_info'].rss, reverse=self.sort_desc)
        elif self.sort_col == "pid":
            display_list.sort(key=lambda x: x['pid'], reverse=self.sort_desc)
        
        # Butonları oluştur
        for proc in display_list:
            # Hizalama
            # PID: 7 karakter
            pid_str = f"[{proc['pid']}]".ljust(7)
            
            # İsim: 28 karakter (Sığması için)
            raw_name = proc['name']
            if len(raw_name) > 28:
                name_str = raw_name[:25] + "..."
            else:
                name_str = raw_name
            name_str = name_str.ljust(29)
            
            # Bellek
            mem_str = f"({proc['memory_mb']})"
            
            # SADECE DEĞERLERİ YAZDIRIYORUZ (Hizalamayı buton içindeki font hallediyor)
            # Ancak Headerlar ayrı buton olduğu için, buradaki boşluklar (ljust)
            # header butonlarının genişliklerine denk gelmeli.
            # Header PID: 65px. Consolas 7 char ~63px. Uygun.
            # Header Name: Esnek.
            # Header Mem: 90px.
            
            btn_text = f"{pid_str} {name_str} {mem_str}"
            
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=btn_text, 
                height=35,
                font=("Consolas", 12), # Monospace
                fg_color="transparent", 
                border_width=1,
                border_color="#333333",
                text_color="#DDDDDD",
                anchor="w",
                command=lambda p=proc: self.select_process(p)
            )
            btn.pack(fill="x", padx=2, pady=2)

    def select_process(self, proc_info):
        self.selected_pid = proc_info['pid']
        self.selected_proc_name = proc_info['name']
        
        # Bilgileri güncelle
        self.lbl_pid.configure(text=str(self.loc["pid"]).replace("-", str(proc_info['pid'])))
        self.lbl_name.configure(text=str(self.loc["name"]).replace("-", str(proc_info['name'])))
        self.lbl_mem.configure(text=str(self.loc["memory"]).replace("-", str(proc_info['memory_mb'])))
        
        # İkonu belirle (Önce cache, sonra tarama)
        final_icon = None
        try:
            cache_key = (self.selected_pid, proc_info['name'])
            
            if cache_key in self.icon_cache:
                final_icon = self.icon_cache[cache_key]
            else:
                icon_img = self.scanner.get_process_icon(self.selected_pid)
                if icon_img:
                    final_icon = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(64, 64))
                    self.icon_cache[cache_key] = final_icon
        except Exception:
            pass

        # UI Güncelle (Elementi yeniden oluşturarak hayalet görüntü sorununu çöz)
        if self.lbl_icon:
            self.lbl_icon.destroy()

        if final_icon:
            self.current_icon = final_icon # Referansı tut
            self.lbl_icon = ctk.CTkLabel(self.info_frame, text="", image=final_icon, width=64, height=64)
        else:
            self.current_icon = None
            self.lbl_icon = ctk.CTkLabel(self.info_frame, text="?", width=64, height=64, fg_color="#333333", corner_radius=8)
            
        self.lbl_icon.grid(row=0, column=0, rowspan=3, padx=(0, 15))

        # Paneli temizle ve sıfırla
        for w in self.details_scroll_frame.winfo_children():
            w.destroy()
        
        lbl = ctk.CTkLabel(self.details_scroll_frame, text=self.loc["start_msg"])
        lbl.pack(pady=20)

    def on_analyze_click(self):
        if not self.selected_pid:
            tk.messagebox.showwarning("Uyarı", self.loc["error_select"])
            return

        # Yükleniyor mesajı
        for w in self.details_scroll_frame.winfo_children():
            w.destroy()
        
        loading_lbl = ctk.CTkLabel(self.details_scroll_frame, text=self.loc["loading"], font=("Roboto", 14))
        loading_lbl.pack(pady=40)
        
        self.update() # UI güncellensin

        threading.Thread(target=self._run_analysis, daemon=True).start()

    def on_force_analyze_click(self):
        if not self.selected_pid:
            tk.messagebox.showwarning("Uyarı", self.loc["error_select"])
            return

        # Yükleniyor mesajı (Farklı olabilir)
        for w in self.details_scroll_frame.winfo_children():
            w.destroy()
        
        msg = "ZORLA YENİLEME:\n" + self.loc["loading"]
        loading_lbl = ctk.CTkLabel(self.details_scroll_frame, text=msg, font=("Roboto", 14), text_color="#F9A825")
        loading_lbl.pack(pady=40)
        
        self.update()

        # True ile gönder (Force Refresh)
        threading.Thread(target=self._run_analysis, args=(True,), daemon=True).start()

    def _run_analysis(self, force_refresh=False):
        try:
            print(f"--- Analiz Başlatıldı: PID {self.selected_pid} (Force: {force_refresh}) ---")
            # HATA DÜZELTME: self.current_processes yerine self.full_process_list kullanılmalı
            proc = next((p for p in self.full_process_list if p['pid'] == self.selected_pid), None)
            
            if not proc:
                # Eğer listede yoksa (örn: işlem kapandıysa) ama PID varsa devam etmeye çalış
                if self.selected_pid:
                    proc = {'pid': self.selected_pid, 'name': self.selected_proc_name, 'memory_mb': '?'}
                else:
                    self.after(0, lambda: self._update_analysis_ui({"error": self.loc["error_list"]}))
                    return

            # 1. Dosya yolu ve Hash hesapla (Zaman alabilir)
            print(self.loc["analyzing"])
            details = self.scanner.get_process_details(self.selected_pid)
            proc.update(details) # path ve hash ekle
            
            # 2. Analiz
            print(self.loc["analyzing_2"])
            # Dili ve force değerini gönder
            result_json = self.gemini.analyze_single_process(proc, lang=self.current_lang, force_refresh=force_refresh)
            print(self.loc["analyzing_3"])
            
            # 3. Sonucu göster
            self.after(0, lambda: self._update_analysis_ui(result_json))

        except Exception as e:
            print(f"!!! KRİTİK HATA (_run_analysis): {e}")
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            self.after(0, lambda: self._update_analysis_ui({"error": f"Analiz Hatası: {error_msg}"}))

    def _update_analysis_ui(self, result_data):
        # Mevcut widgetları temizle
        for w in self.details_scroll_frame.winfo_children():
            w.destroy()

        if "error" in result_data:
            err_lbl = ctk.CTkLabel(self.details_scroll_frame, text=result_data["error"], text_color="red")
            err_lbl.pack(pady=10)
            return

        # Sonuç başlıkları ve verileri
        mapping = {
            "kimlik": self.loc["card_identity"],
            "risk_skoru": self.loc["card_risk"],
            "guvenlik_analizi": self.loc["card_security"],
            "bellek_analizi": self.loc["card_memory"],
            "sonuc": self.loc["card_result"]
        }
        
        for key, title in mapping.items():
            content = result_data.get(key, "Bilgi yok")
            self._create_collapsible_card(title, content)

    def _create_collapsible_card(self, title, content):
        """Açılır kapanır kart oluşturur"""
        card_frame = ctk.CTkFrame(self.details_scroll_frame, fg_color="#2B2B2B", corner_radius=6)
        card_frame.pack(fill="x", pady=5, padx=5)
        
        # Başlık butonu (Tıklayınca aç/kapa yapacak)
        def toggle():
            if content_lbl.winfo_viewable():
                content_lbl.pack_forget()
                btn.configure(text=f"▶ {title}")
            else:
                content_lbl.pack(padx=10, pady=10, fill="x")
                btn.configure(text=f"▼ {title}")

        btn = ctk.CTkButton(card_frame, text=f"▼ {title}", fg_color="transparent", hover_color="#333333", anchor="w", command=toggle, font=("Roboto", 14, "bold"))
        btn.pack(fill="x")
        
        content_lbl = ctk.CTkLabel(card_frame, text=str(content), wraplength=450, justify="left", font=("Roboto", 13))
        content_lbl.pack(padx=10, pady=10, fill="x")


    def open_file_location(self):
        if not self.selected_pid:
            return
            
        path = self.scanner.get_process_path(self.selected_pid)
        if path and os.path.exists(path):
            # Dosya gezgininde seçili olarak aç (Windows)
            subprocess.Popen(f'explorer /select,"{path}"')
        else:
            tk.messagebox.showerror("Hata", self.loc["error_path"])

    def kill_selected_process(self):
        if not self.selected_pid:
            return
            
        confirm = tk.messagebox.askyesno("Onay", self.loc["confirm_kill"].format(self.selected_proc_name, self.selected_pid))
        if confirm:
            success, msg = self.scanner.kill_process(self.selected_pid)
            if success:
                tk.messagebox.showinfo("Başarılı", self.loc["success_kill"])
                self.refresh_process_list()
                self.selected_pid = None
                self.lbl_pid.configure(text=self.loc["pid"])
            else:
                tk.messagebox.showerror("Hata", msg)

if __name__ == "__main__":
    import sys
    import datetime

    class Logger(object):
        def __init__(self, filename="app_log.txt"):
            self.log = open(filename, "a", encoding="utf-8")
    
        def write(self, message):
            if message.strip():
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log.write(f"[{timestamp}] {message.strip()}\n")
                self.log.flush()
            
        def flush(self):
            self.log.flush()

    # Terminal çıktısını dosyaya yönlendir
    sys.stdout = Logger()
    sys.stderr = sys.stdout
    
    app = App()
    app.mainloop()
