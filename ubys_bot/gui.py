"""GUI Application for UBYS Bot."""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import logging
from typing import List, Dict
from datetime import datetime
import time

# PyInstaller uyumluluğu: EXE veya normal Python çalışmasında çalışsın
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller ile derlenmiş EXE
    BASE_DIR_TEMP = sys._MEIPASS
else:
    # Normal Python çalışması
    BASE_DIR_TEMP = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR_TEMP not in sys.path:
    sys.path.insert(0, BASE_DIR_TEMP)

import main
import users
import config

# Dosya yolları (config.py ile uyumlu)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "users_config.json")
GRADES_FILE = os.path.join(BASE_DIR, "student_grades.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "bot_settings.json")


class LogHandler(logging.Handler):
    """Custom logging handler to redirect logs to GUI."""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)


class UBYSBotGUI:
    """UBYS Bot GUI Application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("UBYS Bot - Öğrenci Not Takip Sistemi")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)
        
        self.is_running = False
        self.bot_thread = None
        self.user_list = []
        self.settings = {}
        
        # Load users from file
        self.load_users()
        self.load_settings()
        
        # Create GUI
        self.create_widgets()
        
        # Setup logging
        self.setup_logging()
    
    def load_settings(self):
        """Ayarları dosyadan yükle (Telegram optional)."""
        default_settings = {
            "request_delay": 60,  # 1 dakika
            "session_timeout": 1800,  # 30 dakika
            "telegram_enabled": False,  # Default kapalı
            "telegram_token": "",  # Boş default
            "telegram_chat_id": "",  # Boş default
            "auto_survey": False
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                logging.info(f"Ayarlar yükleniyor: {SETTINGS_FILE}")
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                    # Missing keys ile default'ları merge et
                    for key, value in default_settings.items():
                        if key not in self.settings:
                            self.settings[key] = value
                logging.info(f"Ayarlar başarıyla yüklendi")
            except Exception as e:
                logging.error(f"Ayarlar yüklenirken hata: {e}", exc_info=True)
                self.settings = default_settings
        else:
            logging.info(f"Ayarlar dosyası bulunamadı, varsayılan ayarlar oluşturuluyor: {SETTINGS_FILE}")
            self.settings = default_settings
            self.save_settings()
    
    def save_settings(self):
        """Ayarları dosyaya kaydet."""
        try:
            # Dosya yolunun doğru olduğundan emin ol
            logging.info(f"Ayarlar kaydediliyor: {SETTINGS_FILE}")
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logging.info(f"Ayarlar başarıyla kaydedildi: {self.settings}")
        except Exception as e:
            logging.error(f"Ayarlar kaydedilirken hata: {e}", exc_info=True)
    
    def create_widgets(self):
        """Create all GUI widgets."""
        
        # Main container with notebook (tabs)
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎓 UBYS Bot - Not Takip Sistemi", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=10)
        
        # Create notebook (tabs)
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab değiştirildiğinde callback
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Tab 1: Ana Kontrol
        control_tab = ttk.Frame(notebook, padding="10")
        notebook.add(control_tab, text="🎛️ Kontrol Paneli")
        self.create_control_tab(control_tab)
        
        # Tab 2: Notlarım
        grades_tab = ttk.Frame(notebook, padding="10")
        notebook.add(grades_tab, text="📊 Notlarım")
        self.create_grades_tab(grades_tab)
        
        # Tab 3: Ayarlar (Admin)
        settings_tab = ttk.Frame(notebook, padding="10")
        notebook.add(settings_tab, text="⚙️ Ayarlar")
        self.create_settings_tab(settings_tab)
        
        # Notebook referansını sakla
        self.notebook = notebook
    
    def on_tab_changed(self, event):
        """Sekme değiştirildiğinde çalışacak fonksiyon."""
        selected_tab = self.notebook.index("current")
        
        if selected_tab == 1:  # Notlarım sekmesi
            self.refresh_grades()
        elif selected_tab == 2:  # Ayarlar sekmesi
            self.refresh_system_info()
    
    def create_control_tab(self, parent):
        """Create control panel tab."""
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # Left panel - User management
        left_frame = ttk.LabelFrame(parent, text="Öğrenci Yönetimi", padding="10")
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # User listbox
        self.user_listbox = tk.Listbox(left_frame, height=15, width=40)
        self.user_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.user_listbox.yview)
        scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S))
        self.user_listbox.config(yscrollcommand=scrollbar.set)
        
        # Add user button
        add_btn = ttk.Button(left_frame, text="➕ Öğrenci Ekle", command=self.add_user_dialog)
        add_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Remove user button
        remove_btn = ttk.Button(left_frame, text="➖ Öğrenci Sil", command=self.remove_user)
        remove_btn.grid(row=1, column=1, pady=5, padx=(5, 0), sticky=tk.W+tk.E)
        
        # Right panel - Controls and logs
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        
        # Control buttons
        control_frame = ttk.LabelFrame(right_frame, text="Kontrol", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        
        self.start_btn = ttk.Button(control_frame, text="▶ Başlat", command=self.start_bot)
        self.start_btn.grid(row=0, column=0, padx=5, sticky=tk.W+tk.E)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Durdur", command=self.stop_bot, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5, sticky=tk.W+tk.E)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Durum: Bekleniyor", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(right_frame, text="Log Kayıtları", padding="10")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=20)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        clear_log_btn = ttk.Button(log_frame, text="🗑️ Logları Temizle", command=self.clear_logs)
        clear_log_btn.grid(row=1, column=0, pady=(5, 0))
        
        # Refresh user list
        self.refresh_user_list()
    
    def create_grades_tab(self, parent):
        """Create grades viewing tab."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # Top frame - Student selection
        top_frame = ttk.Frame(parent)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)
        
        ttk.Label(top_frame, text="Öğrenci Seç:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5)
        
        self.grades_student_combo = ttk.Combobox(top_frame, state="readonly")
        self.grades_student_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.grades_student_combo.bind('<<ComboboxSelected>>', self.on_student_selected)
        
        refresh_btn = ttk.Button(top_frame, text="🔄 Yenile", command=self.refresh_grades)
        refresh_btn.grid(row=0, column=2, padx=5)
        
        # Info frame
        info_frame = ttk.Frame(parent)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.last_update_label = ttk.Label(info_frame, text="Son Güncelleme: -", 
                                           font=('Arial', 9, 'italic'))
        self.last_update_label.grid(row=0, column=0, sticky=tk.W)
        
        # Grades table frame
        table_frame = ttk.LabelFrame(parent, text="Ders Notları", padding="10")
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Create treeview for grades
        columns = ("Ders Adı", "Notlar")
        self.grades_tree = ttk.Treeview(table_frame, columns=columns, show='tree headings', height=20)
        
        self.grades_tree.heading("#0", text="No")
        self.grades_tree.heading("Ders Adı", text="Ders Adı")
        self.grades_tree.heading("Notlar", text="Notlar")
        
        self.grades_tree.column("#0", width=50)
        self.grades_tree.column("Ders Adı", width=300)
        self.grades_tree.column("Notlar", width=400)
        
        self.grades_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.grades_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.grades_tree.config(yscrollcommand=tree_scroll.set)
        
        # Load initial grades
        self.refresh_grades()
    
    def setup_logging(self):
        """Setup logging to redirect to GUI."""
        log_handler = LogHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Get root logger and add our handler
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
    
    def load_users(self):
        """Load users from config file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.user_list = json.load(f)
            except Exception as e:
                self.user_list = []
        else:
            # Load from users.py if config file doesn't exist
            self.user_list = users.user_list.copy()
            self.save_users()
    
    def save_users(self):
        """Save users to config file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_list, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Hata", f"Kullanıcılar kaydedilemedi: {e}")
    
    def refresh_user_list(self):
        """Refresh the user listbox."""
        self.user_listbox.delete(0, tk.END)
        for user in self.user_list:
            display_text = f"{user['name']} - {user.get('sapid', '')[:50]}..."
            self.user_listbox.insert(tk.END, display_text)
    
    def add_user_dialog(self):
        """Open dialog to add new user."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Öğrenci Ekle")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form fields
        ttk.Label(dialog, text="Öğrenci No:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Şifre:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        password_entry = ttk.Entry(dialog, width=40, show="*")
        password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="SAPID URL:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        sapid_entry = ttk.Entry(dialog, width=40)
        sapid_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def save_user():
            name = name_entry.get().strip()
            password = password_entry.get().strip()
            sapid = sapid_entry.get().strip()
            
            if not all([name, password, sapid]):
                messagebox.showwarning("Uyarı", "Tüm alanları doldurun!")
                return
            
            new_user = {
                "name": name,
                "password": password,
                "sapid": sapid
            }
            
            self.user_list.append(new_user)
            self.save_users()
            self.refresh_user_list()
            dialog.destroy()
            messagebox.showinfo("Başarılı", "Öğrenci eklendi!")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Kaydet", command=save_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="İptal", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def remove_user(self):
        """Remove selected user."""
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz öğrenciyi seçin!")
            return
        
        index = selection[0]
        user = self.user_list[index]
        
        if messagebox.askyesno("Onay", f"{user['name']} öğrencisini silmek istediğinizden emin misiniz?"):
            self.user_list.pop(index)
            self.save_users()
            self.refresh_user_list()
            messagebox.showinfo("Başarılı", "Öğrenci silindi!")
    
    def start_bot(self):
        """Start the bot."""
        if not self.user_list:
            messagebox.showwarning("Uyarı", "Lütfen en az bir öğrenci ekleyin!")
            return
        
        if self.is_running:
            return
        
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Durum: ▶ Çalışıyor", foreground="green")
        
        # Update config variables with current settings
        import config
        config.load_settings()
        config.USER_LIST = self.user_list.copy()
        
        # Start bot in separate thread
        self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
        self.bot_thread.start()
    
    def run_bot(self):
        """Run the bot monitoring loop."""
        try:
            main.run_monitoring_loop()
        except Exception as e:
            logging.error(f"Bot çalışırken hata oluştu: {e}")
        finally:
            self.is_running = False
            self.root.after(0, self.reset_buttons)
    
    def stop_bot(self):
        """Stop the bot."""
        if not self.is_running:
            return
        
        self.is_running = False
        main.stop_bot()
        self.status_label.config(text="Durum: ⏹ Durduruldu", foreground="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        messagebox.showinfo("Bilgi", "Bot durduruldu!")
    
    def reset_buttons(self):
        """Reset button states."""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Durum: ⏹ Durduruldu", foreground="red")
    
    def clear_logs(self):
        """Clear the log text area."""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
    
    def refresh_grades(self):
        """Notları yenile ve combobox'ı güncelle."""
        try:
            logging.info(f"Notlar yükleniyor: {GRADES_FILE}")
            
            if os.path.exists(GRADES_FILE):
                with open(GRADES_FILE, 'r', encoding='utf-8') as f:
                    all_grades = json.load(f)
                
                # Combobox'ı güncelle
                student_ids = list(all_grades.keys())
                self.grades_student_combo['values'] = student_ids
                logging.info(f"{len(student_ids)} öğrenci bulundu: {student_ids}")
                
                if student_ids and not self.grades_student_combo.get():
                    self.grades_student_combo.current(0)
                    self.on_student_selected(None)
            else:
                logging.warning(f"Notlar dosyası bulunamadı: {GRADES_FILE}")
                self.grades_student_combo['values'] = []
                self.last_update_label.config(text="Son Güncelleme: Henüz veri yok")
        except Exception as e:
            logging.error(f"Notlar yüklenirken hata: {e}", exc_info=True)
    
    def on_student_selected(self, event):
        """Öğrenci seçildiğinde notları göster."""
        student_id = self.grades_student_combo.get()
        if not student_id:
            return
        
        try:
            # Clear existing data
            for item in self.grades_tree.get_children():
                self.grades_tree.delete(item)
            
            # Load grades
            if os.path.exists(GRADES_FILE):
                with open(GRADES_FILE, 'r', encoding='utf-8') as f:
                    all_grades = json.load(f)
                
                if student_id in all_grades:
                    student_data = all_grades[student_id]
                    last_updated = student_data.get("last_updated", "Bilinmiyor")
                    courses = student_data.get("courses", [])
                    
                    # Update last update label
                    self.last_update_label.config(text=f"Son Güncelleme: {last_updated}")
                    
                    # Populate treeview
                    for idx, course in enumerate(courses, 1):
                        course_name = course.get("name", "Bilinmiyor")
                        exams = course.get("exams", [])
                        
                        # Ana ders satırı
                        parent = self.grades_tree.insert("", tk.END, text=str(idx), 
                                                        values=(course_name, ""))
                        
                        # Sınav notları alt satırlar
                        if exams:
                            for exam in exams:
                                self.grades_tree.insert(parent, tk.END, text="", 
                                                       values=("", f"  {exam}"))
                        else:
                            self.grades_tree.insert(parent, tk.END, text="", 
                                                   values=("", "  Sınav bilgisi yok"))
                else:
                    self.last_update_label.config(text="Son Güncelleme: Veri bulunamadı")
        except Exception as e:
            logging.error(f"Notlar görüntülenirken hata: {e}")
            messagebox.showerror("Hata", f"Notlar yüklenirken hata oluştu: {e}")
    
    def create_settings_tab(self, parent):
        """Admin ayarları sekmesi oluştur."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # Settings notebook
        settings_notebook = ttk.Notebook(parent)
        settings_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # General Settings
        general_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(general_frame, text="⚡ Genel Ayarlar")
        self.create_general_settings(general_frame)
        
        # Telegram Settings
        telegram_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(telegram_frame, text="📱 Telegram Ayarları")
        self.create_telegram_settings(telegram_frame)
        
        # System Info
        info_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(info_frame, text="ℹ️ Sistem Bilgileri")
        self.create_system_info(info_frame)
    
    def create_general_settings(self, parent):
        """Genel ayarları göster."""
        parent.columnconfigure(1, weight=1)
        
        # İstek Aralığı
        ttk.Label(parent, text="İstek Aralığı (saniye):", font=('Arial', 10)).grid(
            row=0, column=0, sticky=tk.W, pady=10)
        
        self.request_delay_var = tk.StringVar(value=str(self.settings.get("request_delay", 300)))
        request_delay_spin = ttk.Spinbox(parent, from_=1, to=3600, textvariable=self.request_delay_var, width=15)
        request_delay_spin.grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # Session Timeout
        ttk.Label(parent, text="Oturum Zaman Aşımı (saniye):", font=('Arial', 10)).grid(
            row=1, column=0, sticky=tk.W, pady=10)
        
        self.session_timeout_var = tk.StringVar(value=str(self.settings.get("session_timeout", 1800)))
        session_timeout_spin = ttk.Spinbox(parent, from_=60, to=7200, textvariable=self.session_timeout_var, width=15)
        session_timeout_spin.grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # Auto Survey
        self.auto_survey_var = tk.BooleanVar(value=self.settings.get("auto_survey", False))
        survey_check = ttk.Checkbutton(parent, text="Anket Otomatik Çöz (Deneysel)", 
                                      variable=self.auto_survey_var)
        survey_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Save button
        save_btn = ttk.Button(parent, text="💾 Kaydet", command=self.save_general_settings)
        save_btn.grid(row=3, column=0, columnspan=2, pady=20)
    
    def create_telegram_settings(self, parent):
        """Telegram ayarlarını göster (OPSİYONEL)."""
        parent.columnconfigure(1, weight=1)
        
        # Başlık
        info_label = ttk.Label(parent, text="⚠️ Telegram Opsiyoneldir - Boş bırakabilirsiniz", 
                              font=('Arial', 10, 'bold'), foreground="blue")
        info_label.grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        # Telegram Etkinleştir Checkbox
        self.telegram_enabled_var = tk.BooleanVar(value=self.settings.get("telegram_enabled", False))
        telegram_check = ttk.Checkbutton(parent, text="✅ Telegram Bildirimlerini Etkinleştir", 
                                        variable=self.telegram_enabled_var,
                                        command=self.toggle_telegram_fields)
        telegram_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Bot Token
        self.token_label = ttk.Label(parent, text="Bot Token:", font=('Arial', 10))
        self.token_label.grid(row=2, column=0, sticky=tk.W, pady=10)
        
        self.token_var = tk.StringVar(value=self.settings.get("telegram_token", ""))
        self.token_entry = ttk.Entry(parent, textvariable=self.token_var, width=40, show="•")
        self.token_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=10)
        
        # Chat ID
        self.chat_id_label = ttk.Label(parent, text="Chat ID:", font=('Arial', 10))
        self.chat_id_label.grid(row=3, column=0, sticky=tk.W, pady=10)
        
        self.chat_id_var = tk.StringVar(value=self.settings.get("telegram_chat_id", ""))
        self.chat_id_entry = ttk.Entry(parent, textvariable=self.chat_id_var, width=40)
        self.chat_id_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=10)
        
        # Test button
        self.test_btn = ttk.Button(parent, text="🧪 Test Et", command=self.test_telegram)
        self.test_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Save button
        save_btn = ttk.Button(parent, text="💾 Kaydet", command=self.save_telegram_settings)
        save_btn.grid(row=5, column=0, columnspan=2, pady=20)
        
        # İlk durumu ayarla
        self.toggle_telegram_fields()
    
    def toggle_telegram_fields(self):
        """Telegram checkbox durumuna göre field'ları etkinleştir/devre dışı bırak."""
        state = 'normal' if self.telegram_enabled_var.get() else 'disabled'
        self.token_entry.config(state=state)
        self.chat_id_entry.config(state=state)
        self.test_btn.config(state=state)
    
    def create_system_info(self, parent):
        """Sistem bilgilerini göster (dinamik)."""
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        
        self.info_text = scrolledtext.ScrolledText(parent, height=20, state='disabled')
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # İlk yükleme
        self.refresh_system_info()
    
    def refresh_system_info(self):
        """Sistem bilgilerini yenile."""
        # Güncel ayarları yükle
        config.load_settings()
        
        # Sistem bilgilerini hazırla
        info_content = f"""
╔════════════════════════════════════════════════════════════════════╗
║                   UBYS BOT - SİSTEM BİLGİLERİ                    ║
╚════════════════════════════════════════════════════════════════════╝

📊 İSTATİSTİKLER:
  • Toplam Kaydedilmiş Öğrenci: {len(self.user_list)}
  • Kaydedilmiş Ders Notları: {self._count_total_grades()}
  • Uygulama Sürümü: 1.0.0

⚙️ AYARLAR (canlı):
  • İstek Aralığı: {config.REQUEST_DELAY} saniye
  • Oturum Zaman Aşımı: {config.SESSION_TIMEOUT} saniye
  • Telegram: {'Etkin' if config.TELEGRAM_ENABLED else 'Devre Dışı'}
  • Otomatik Anket: {'Etkin' if config.AUTO_SURVEY else 'Devre Dışı'}

� BOT DURUMU:
  • Çalışma Durumu: {'Çalışıyor' if self.is_running else 'Durduruldu'}

📝 AÇIKLAMALAR:
  İstek Aralığı: Bot'un kaç saniyede bir not kontrolü yapacağı
  Oturum Zaman Aşımı: Oturumun ne kadar sürede yenileneceği
  Telegram: Notlar güncellendiğinde bildirim gönderimi

═══════════════════════════════════════════════════════════════════════
Güncelleme Zamanı: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        # Text widget'ı güncelle
        self.info_text.configure(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_content)
        self.info_text.configure(state='disabled')
    
    def _count_total_grades(self):
        """Toplam kaydedilmiş ders sayısını say."""
        if not os.path.exists(GRADES_FILE):
            return 0
        try:
            with open(GRADES_FILE, 'r', encoding='utf-8') as f:
                all_grades = json.load(f)
                total = sum(len(v.get("courses", [])) for v in all_grades.values())
                return total
        except:
            return 0
    
    def save_general_settings(self):
        """Genel ayarları kaydet ve bota bildir."""
        try:
            self.settings["request_delay"] = int(self.request_delay_var.get())
            self.settings["session_timeout"] = int(self.session_timeout_var.get())
            self.settings["auto_survey"] = self.auto_survey_var.get()
            
            # Debug: Ayarları logla
            logging.info(f"Kaydedilen REQUEST_DELAY: {self.settings['request_delay']}s")
            
            self.save_settings()
            
            # Bot'un ayarları güncel alması için config'i reload et
            import config
            config.load_settings()
            logging.info(f"Config yeniden yüklendi. Yeni REQUEST_DELAY: {config.REQUEST_DELAY}s")
            
            messagebox.showinfo("Başarılı", f"Ayarlar kaydedildi!\nYeni istek aralığı: {self.settings['request_delay']}s")
        except ValueError as e:
            messagebox.showerror("Hata", f"Lütfen geçerli sayılar girin! ({e})")
    
    def save_telegram_settings(self):
        """Telegram ayarlarını kaydet - checkbox ile kontrol edilir."""
        enabled = self.telegram_enabled_var.get()
        token = self.token_var.get().strip()
        chat_id = self.chat_id_var.get().strip()
        
        # Eğer enabled ise token ve chat_id dolu olmalı
        if enabled:
            if not token or not chat_id:
                messagebox.showwarning("Uyarı", "Telegram etkinleştirildiğinde Token ve Chat ID girilmelidir!")
                return
        
        # Ayarları kaydet
        self.settings["telegram_enabled"] = enabled
        self.settings["telegram_token"] = token if enabled else ""
        self.settings["telegram_chat_id"] = chat_id if enabled else ""
        self.save_settings()
        
        # Bot'un ayarları güncel alması için config'i reload et
        import config
        config.load_settings()
        
        if enabled:
            messagebox.showinfo("Başarılı", "Telegram ayarları kaydedildi ve etkinleştirildi!")
        else:
            messagebox.showinfo("Bilgi", "Telegram devre dışı - Bot sadece lokal olarak not kaydedecek!")
    
    def test_telegram(self):
        """Telegram bağlantısını test et (sadece enabled ise)."""
        try:
            if not self.telegram_enabled_var.get():
                messagebox.showinfo("Bilgi", "Telegram devre dışı - önce etkinleştirin!")
                return
            
            import telegram as tg
            token = self.token_var.get().strip()
            chat_id = self.chat_id_var.get().strip()
            
            if not token or not chat_id:
                messagebox.showwarning("Uyarı", "Lütfen Token ve Chat ID'yi girin!")
                return
            
            notifier = tg.TelegramNotifier(token, chat_id)
            success = notifier.send_message("🧪 UBYS Bot Telegram Test Mesajı")
            
            if success:
                messagebox.showinfo("Başarılı", "Test mesajı gönderildi!")
            else:
                messagebox.showerror("Hata", "Mesaj gönderilemedi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Hata oluştu: {e}")


def main_gui():
    """Run the GUI application."""
    root = tk.Tk()
    app = UBYSBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main_gui()
