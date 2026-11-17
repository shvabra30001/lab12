# -*- coding: utf-8 -*-
"""
MY JARVIS - С историей действий и округлыми кнопками
"""
import customtkinter as ctk
import subprocess
import os
import threading
import cv2
import ollama
from datetime import datetime
import pyautogui
import speech_recognition as sr
import random
import requests
from PIL import Image, ImageSequence
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox
import time
import math
import urllib.parse
import json

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANIMATION_FILE = os.path.join(BASE_DIR, "jarvis_anim.gif")
HISTORY_FILE = os.path.join(BASE_DIR, "jarvis_history.json")

NEW_YEAR_MUSIC = None
for path in [os.path.expanduser("~/Desktop/new_year_theme.mp3"), os.path.expanduser("~/Desktop/new_year_theme.MP3")]:
    if os.path.exists(path):
        NEW_YEAR_MUSIC = path
        break

SMART_PROMPT = """Ты - MY JARVIS, умный ИИ-ассистент на MacBook Air M4.
Отвечай на русском языке. Будь краток."""

RADIO_STATIONS = {
    "европа плюс": "https://ep128.hostingradio.ru:8030/ep128",
    "русское радио": "https://rusradio.hostingradio.ru/rusradio128",
}

THEMES = {
    "cosmic": {"name": "🌌 Космос", "bg": "#0f0f0f", "sidebar": "#171717", "accent": "#615ced", "message_user": "#615ced", "message_ai": "#1e1e1e", "border": "#3a3a3a", "text": "#ffffff"},
    "newyear": {"name": "🎄 Новый Год", "bg": "#0a1628", "sidebar": "#0d1f3c", "accent": "#ff4444", "message_user": "#ff4444", "message_ai": "#1a2d4a", "border": "#2a4a6a", "text": "#ffffff"},
}

# ============ ИСТОРИЯ ДЕЙСТВИЙ ============

class ActionHistory:
    """Сохраняет все действия пользователя"""
    def __init__(self, filepath):
        self.filepath = filepath
        self.actions = []
        self.load()
    
    def load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.actions = json.load(f)
        except:
            self.actions = []
    
    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.actions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")
    
    def add(self, action_type, description, details=""):
        action = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": action_type,
            "description": description,
            "details": details
        }
        self.actions.append(action)
        # Храним только последние 500 действий
        if len(self.actions) > 500:
            self.actions = self.actions[-500:]
        self.save()
    
    def get_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return [a for a in self.actions if a["time"].startswith(today)]
    
    def get_all(self):
        return self.actions
    
    def clear(self):
        self.actions = []
        self.save()

# ============ АНИМАЦИИ ============

class StarfieldBackground(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#000000", highlightthickness=0, **kwargs)
        self.stars = []
        self.create_stars()
        self.animate()
    def create_stars(self):
        w, h = 2000, 2000
        for _ in range(100):
            x, y = random.randint(0, w), random.randint(0, h)
            size = random.uniform(0.5, 1.5)
            star = self.create_oval(x, y, x+size, y+size, fill="#ffffff", outline="")
            self.stars.append({"id": star, "x": x, "y": y, "size": size})
    def animate(self):
        try:
            if self.winfo_height() < 10:
                self.after(100, self.animate); return
            self.after(100, self.animate)
        except: self.after(100, self.animate)

class GifPlayer(ctk.CTkLabel):
    def __init__(self, parent, gif_path, size=(120, 120), **kwargs):
        super().__init__(parent, text="", **kwargs)
        self.gif_path = gif_path; self.size = size; self.frames = []; self.current_frame = 0
        self.load_gif()
        if self.frames: self.animate()
    def load_gif(self):
        try:
            if os.path.exists(self.gif_path):
                img = Image.open(self.gif_path)
                for frame in ImageSequence.Iterator(img):
                    frame = frame.copy().resize(self.size, Image.Resampling.LANCZOS)
                    self.frames.append(ctk.CTkImage(light_image=frame, dark_image=frame, size=self.size))
        except: pass
    def animate(self):
        if self.frames:
            self.configure(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(100, self.animate)

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Loading..."); self.geometry("600x600"); self.overrideredirect(True)
        self.configure(fg_color="#000000"); self.center_window()
        self.loading_label = ctk.CTkLabel(self, text="ЗАГРУЗКА MY JARVIS...", font=("SF Pro Display", 18, "bold"), text_color="#00d9ff", fg_color="transparent")
        self.loading_label.place(relx=0.5, rely=0.6, anchor="center")
        self.progress = ctk.CTkProgressBar(self, width=400, fg_color="#1a1f3a", progress_color="#00d9ff")
        self.progress.place(relx=0.5, rely=0.7, anchor="center"); self.progress.set(0)
        self.animate()
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 300; y = (self.winfo_screenheight() // 2) - 300
        self.geometry(f'600x600+{x}+{y}')
    def animate(self):
        for i in range(100):
            self.progress.set(i / 100); self.update(); time.sleep(0.02)
        self.destroy()

class PlusMenu(ctk.CTkFrame):
    def __init__(self, parent, on_select, **kwargs):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=25, border_width=1, border_color="#3a3a3a", **kwargs)
        self.on_select = on_select
        self.items = [
            ("📷", "Отправить фото", "photo"),
            ("📸", "Режим камеры", "camera"),
            ("🎮", "Игры", "games"),
            ("📜", "История", "history"),
            ("⚙️", "Настройки", "settings"),
            ("🤖", "Режим робота", "robot"),
            ("📸", "Скриншот", "screenshot"),
            ("😂", "Случайный мем", "meme")
        ]
        for icon, text, action in self.items:
            btn = ctk.CTkFrame(self, fg_color="transparent", corner_radius=20, cursor="hand2")
            btn.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(btn, text=f"{icon}  {text}", font=("SF Pro Display", 13), text_color="#e0e0e0", fg_color="transparent").pack(pady=10, padx=12, anchor="w")
            btn.bind("<Enter>", lambda e, b=btn: b.configure(fg_color="#2a2a2a"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(fg_color="transparent"))
            btn.bind("<Button-1>", lambda e, a=action: self._select(a))
            for child in btn.winfo_children():
                child.bind("<Button-1>", lambda e, a=action: self._select(a))
                child.bind("<Enter>", lambda e, b=btn: b.configure(fg_color="#2a2a2a"))
                child.bind("<Leave>", lambda e, b=btn: b.configure(fg_color="transparent"))
    def _select(self, action): self.destroy(); self.on_select(action)

# ============ ОКНО ИСТОРИИ ============

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, history):
        super().__init__(parent)
        self.title("📜 История действий")
        self.geometry("600x700")
        self.resizable(True, True)
        self.configure(fg_color="#1a1a2e")
        self.transient(parent)
        self.history = history
        
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="#0f0f1e", corner_radius=20)
        header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(header, text="📜 История действий", font=("SF Pro Display", 20, "bold"), text_color="#00d9ff", fg_color="transparent").pack(pady=15)
        
        # Статистика
        today_actions = len(history.get_today())
        total_actions = len(history.get_all())
        
        stats = ctk.CTkFrame(header, fg_color="transparent")
        stats.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(stats, text=f"📅 Сегодня: {today_actions} действий", font=("SF Pro Display", 12), text_color="#00ff88", fg_color="transparent").pack(side="left", padx=10)
        ctk.CTkLabel(stats, text=f"📊 Всего: {total_actions} действий", font=("SF Pro Display", 12), text_color="#00a8ff", fg_color="transparent").pack(side="right", padx=10)
        
        # Список действий
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0f0f1e", corner_radius=20)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        actions = history.get_all()
        if not actions:
            ctk.CTkLabel(scroll_frame, text="История пуста", font=("SF Pro Display", 14), text_color="#888888", fg_color="transparent").pack(pady=50)
        else:
            # Группируем по дням
            current_date = None
            for action in reversed(actions):
                action_date = action["time"].split(" ")[0]
                if action_date != current_date:
                    current_date = action_date
                    date_label = ctk.CTkLabel(scroll_frame, text=f"📅 {action_date}", font=("SF Pro Display", 13, "bold"), text_color="#ffaa00", fg_color="transparent")
                    date_label.pack(anchor="w", padx=10, pady=(15, 5))
                
                # Тип действия - иконка
                type_icons = {
                    "message": "💬", "command": "⚡", "search": "🔍", "weather": "🌤️",
                    "radio": "📻", "game": "🎮", "camera": "📸", "settings": "⚙️",
                    "chat": "🆕", "image": "🎨", "screenshot": "📷", "meme": "😂",
                    "volume": "🔊", "brightness": "🔆", "system": "⏻"
                }
                icon = type_icons.get(action["type"], "•")
                
                action_frame = ctk.CTkFrame(scroll_frame, fg_color="#1a1f3a", corner_radius=15)
                action_frame.pack(fill="x", padx=10, pady=3)
                
                ctk.CTkLabel(action_frame, text=f"{icon} {action['description']}", font=("SF Pro Display", 12), text_color="#ffffff", fg_color="transparent", justify="left").pack(padx=12, pady=8, anchor="w")
                ctk.CTkLabel(action_frame, text=action["time"].split(" ")[1], font=("SF Pro Display", 10), text_color="#888888", fg_color="transparent").pack(padx=12, pady=(0, 8), anchor="w")
        
        # Кнопки внизу
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkButton(btn_frame, text="🗑️ Очистить историю", command=self.clear_history, width=200, height=45, corner_radius=22, fg_color="#ff0044", hover_color="#cc0033", font=("SF Pro Display", 13, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="✕ Закрыть", command=self.destroy, width=200, height=45, corner_radius=22, fg_color="#615ced", hover_color="#7b73f5", font=("SF Pro Display", 13, "bold")).pack(side="right", padx=10)
    
    def clear_history(self):
        if messagebox.askyesno("Очистить историю", "Вы уверены? Все действия будут удалены."):
            self.history.clear()
            self.destroy()
            HistoryWindow(self.master, self.history)

# ============ ГЛАВНЫЙ КЛАСС ============

class AIAssistant(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MY JARVIS"); self.geometry("1200x800")
        self.current_theme = "cosmic"
        self.is_speaking = False; self.audio_playing = False
        self.recognizer = sr.Recognizer()
        self.volume = 5; self.music_volume = 50
        self.radio_process = None; self.music_process = None
        self.chats = [{"id": 1, "title": "Новый чат", "messages": []}]
        self.current_chat_id = 1; self.current_chat = []
        self.plus_menu = None
        self.wake_word_active = True
        self.command_mode = False
        self.command_mode_timer = None
        self.last_ai_responses = []
        self.camera_mode = False
        self.camera_cap = None
        self.camera_overlay = None
        self.camera_label = None
        self.camera_text_label = None
        
        # 🔑 ИСТОРИЯ ДЕЙСТВИЙ
        self.history = ActionHistory(HISTORY_FILE)
        self.history.add("system", "Приложение запущено", "MY JARVIS v2.0")
        
        self.create_widgets()
        self.apply_theme("cosmic")
        self.add_message("Привет! Я ваш ИИ-помощник. Все ваши действия сохраняются в истории 📜🚀", "ai", save=False)
        
        threading.Thread(target=lambda: ollama.chat(model='qwen2.5:7b', messages=[{'role': 'user', 'content': 'hi'}], options={'num_predict': 5, 'keep_alive': '30m'}), daemon=True).start()
        threading.Thread(target=self.wake_word_loop, daemon=True).start()

    def apply_theme(self, theme_id):
        self.current_theme = theme_id
        theme = THEMES[theme_id]
        if hasattr(self, 'sidebar'): self.sidebar.configure(fg_color=theme["sidebar"])
        if hasattr(self, 'chat_frame'): self.chat_frame.configure(fg_color=theme["bg"])
        if hasattr(self, 'input_box'): self.input_box.configure(fg_color=theme["message_ai"], border_color=theme["border"])
        if hasattr(self, 'chat_title'): self.chat_title.configure(text_color=theme["text"])
        if hasattr(self, 'send_btn'): self.send_btn.configure(fg_color=theme["accent"])
        if hasattr(self, 'main_area'): self.main_area.configure(fg_color=theme["bg"])
        if hasattr(self, 'input_container'): self.input_container.configure(fg_color=theme["bg"])
        if theme_id == "newyear" and NEW_YEAR_MUSIC:
            self.start_new_year_music()

    def start_new_year_music(self):
        music_path = os.path.expanduser("~/Desktop/new_year_theme.mp3")
        if not os.path.exists(music_path): return
        try:
            self.music_process = subprocess.Popen(["afplay", "-v", "0.5", music_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.add_message("🎄 Новогодняя музыка играет! 🎵", "ai")
            self.history.add("radio", "Включена новогодняя музыка", music_path)
        except: pass

    def create_widgets(self):
        theme = THEMES[self.current_theme]
        
        # 🔑 Все кнопки теперь с corner_radius=25 (максимально округлые)
        
        self.sidebar = ctk.CTkFrame(self, fg_color=theme["sidebar"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y"); self.sidebar.configure(width=260)
        
        # Округлые кнопки в сайдбаре
        ctk.CTkButton(self.sidebar, text="+ Новый чат", command=self.new_chat, width=236, height=45, corner_radius=25, fg_color="#2a2a2a", hover_color="#3a3a3a", font=("SF Pro Display", 13, "bold")).pack(pady=10, padx=12)
        
        self.search_entry = ctk.CTkEntry(self.sidebar, placeholder_text="🔍 Поиск чатов...", height=40, corner_radius=20, fg_color="#2a2a2a", border_width=0, font=("SF Pro Display", 12))
        self.search_entry.pack(padx=12, pady=5, fill="x")
        
        ctk.CTkFrame(self.sidebar, fg_color="#2a2a2a", height=1, border_width=0).pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(self.sidebar, text="История чатов", font=("SF Pro Display", 11, "bold"), text_color="#888888", fg_color="transparent").pack(padx=12, pady=5, anchor="w")
        
        self.chat_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color=theme["sidebar"])
        self.chat_list_frame.pack(fill="both", expand=True, padx=12, pady=10)
        
        ctk.CTkFrame(self.sidebar, fg_color="#2a2a2a", height=1, border_width=0).pack(fill="x", padx=12, pady=10)
        
        # 🔑 Округлые кнопки в сайдбаре
        ctk.CTkButton(self.sidebar, text="📜  История", command=self.open_history, width=236, height=45, corner_radius=25, fg_color="#0066ff", hover_color="#0044cc", font=("SF Pro Display", 13, "bold")).pack(pady=5, padx=12)
        ctk.CTkButton(self.sidebar, text="🎮  Игры", command=self.open_games_menu, width=236, height=45, corner_radius=25, fg_color="#2a2a2a", hover_color="#3a3a3a", font=("SF Pro Display", 13, "bold")).pack(pady=5, padx=12)
        ctk.CTkButton(self.sidebar, text="⚙️  Настройки", command=self.open_settings, width=236, height=45, corner_radius=25, fg_color="#2a2a2a", hover_color="#3a3a3a", font=("SF Pro Display", 13, "bold")).pack(pady=5, padx=12)
        ctk.CTkButton(self.sidebar, text="👤  Tripatropa", width=236, height=45, corner_radius=25, fg_color="#2a2a2a", font=("SF Pro Display", 13, "bold")).pack(pady=5, padx=12)
        
        self.main_area = ctk.CTkFrame(self, fg_color=theme["bg"])
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.animation_canvas = StarfieldBackground(self.main_area, width=2000, height=2000)
        self.animation_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.content_container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content_container.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.content_container.lift()
        
        self.chat_title = ctk.CTkLabel(self.content_container, text="Новый чат", font=("SF Pro Display", 16, "bold"), text_color=theme["text"], fg_color="transparent")
        self.chat_title.pack(pady=15, padx=20, anchor="w")
        
        self.chat_frame = ctk.CTkScrollableFrame(self.content_container, fg_color=theme["bg"])
        self.chat_frame.pack(fill="both", expand=True)
        
        self.input_container = ctk.CTkFrame(self.content_container, fg_color=theme["bg"])
        self.input_container.pack(fill="x", side="bottom", pady=(0, 20))
        
        self.input_box = ctk.CTkFrame(self.input_container, fg_color=theme["message_ai"], corner_radius=25, border_width=1, border_color=theme["border"])
        self.input_box.pack(fill="x", padx=60, pady=10)
        
        input_row = ctk.CTkFrame(self.input_box, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=10)
        
        # 🔑 Округлые кнопки в поле ввода
        self.plus_btn = ctk.CTkButton(input_row, text="+", command=self.toggle_plus_menu, width=40, height=40, corner_radius=20, fg_color="#2a2a2a", font=("SF Pro Display", 20, "bold"))
        self.plus_btn.pack(side="left", padx=(0, 8))
        
        self.entry = ctk.CTkEntry(input_row, placeholder_text="Спросите что-нибудь...", height=40, font=("SF Pro Display", 14), corner_radius=20, border_width=0, fg_color="transparent", text_color=theme["text"])
        self.entry.pack(side="left", fill="x", expand=True, padx=0)
        self.entry.bind("<Return>", lambda e: self.send_message())
        
        self.mic_btn = ctk.CTkButton(input_row, text="🎤", command=self.toggle_listening, width=40, height=40, corner_radius=20, fg_color="#2a2a2a", font=("SF Pro Display", 16))
        self.mic_btn.pack(side="right", padx=(8, 0))
        
        self.send_btn = ctk.CTkButton(input_row, text="➤", command=self.send_message, width=40, height=40, corner_radius=20, fg_color=theme["accent"], font=("SF Pro Display", 16, "bold"))
        self.send_btn.pack(side="right", padx=(8, 0))
        
        self.wake_indicator = ctk.CTkLabel(self.input_container, text="🎤 Слушаю 'Джарвис'...", font=("SF Pro Display", 11), text_color="#ffaa00", fg_color="transparent")
        self.wake_indicator.pack(pady=5)
        
        ctk.CTkLabel(self.input_container, text="Скажите 'Джарвис' для активации", font=("SF Pro Display", 11), text_color="#666666", fg_color="transparent").pack(pady=5)

    def open_history(self):
        """Открыть окно истории"""
        self.history.add("system", "Открыта история действий")
        HistoryWindow(self, self.history)

    def wake_word_loop(self):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 4000
        recognizer.dynamic_energy_threshold = True
        
        while self.wake_word_active:
            if self.is_speaking or self.audio_playing:
                time.sleep(0.5)
                continue
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=4)
                    if self.is_speaking or self.audio_playing: continue
                    text = recognizer.recognize_google(audio, language="ru-RU").lower()
                    if "джарвис" in text or "jarvis" in text:
                        self.after(0, self.activate_command_mode)
                        self.speak("Да?")
                        time.sleep(0.5)
                        with sr.Microphone() as source2:
                            recognizer.adjust_for_ambient_noise(source2, duration=0.3)
                            audio2 = recognizer.listen(source2, timeout=10, phrase_time_limit=15)
                            command = recognizer.recognize_google(audio2, language="ru-RU")
                            self.after(0, lambda c=command: self.process_voice_command(c))
            except sr.WaitTimeoutError: continue
            except sr.UnknownValueError: continue
            except Exception as e: time.sleep(1)

    def activate_command_mode(self):
        self.command_mode = True
        self.wake_indicator.configure(text="🟢 Джарвис слушает...", text_color="#00ff88")
        self.mic_btn.configure(fg_color="#00ff88")
        if self.command_mode_timer: self.after_cancel(self.command_mode_timer)
        self.command_mode_timer = self.after(12000, self.deactivate_command_mode)

    def deactivate_command_mode(self):
        self.command_mode = False
        self.wake_indicator.configure(text="🎤 Слушаю 'Джарвис'...", text_color="#ffaa00")
        self.mic_btn.configure(fg_color="#2a2a2a")

    def toggle_plus_menu(self):
        if self.plus_menu and self.plus_menu.winfo_exists():
            self.plus_menu.destroy(); self.plus_menu = None; return
        self.plus_menu = PlusMenu(self, on_select=self.handle_plus_action, width=220)
        btn_x = self.plus_btn.winfo_rootx() - self.winfo_rootx()
        btn_y = self.plus_btn.winfo_rooty() - self.winfo_rooty()
        self.plus_menu.place(x=btn_x, y=btn_y - 350, anchor="nw")
        self.plus_menu.lift()

    def handle_plus_action(self, action):
        self.plus_menu = None
        if action == "photo": self.send_photo()
        elif action == "camera": self.toggle_camera_mode()
        elif action == "games": self.open_games_menu()
        elif action == "history": self.open_history()
        elif action == "settings": self.open_settings()
        elif action == "robot": self.enter_robot_mode()
        elif action == "screenshot": self.take_screenshot()
        elif action == "meme": self.send_meme()

    def toggle_camera_mode(self):
        if self.camera_mode: self.disable_camera_mode()
        else: self.enable_camera_mode()

    def enable_camera_mode(self):
        self.camera_mode = True
        self.add_message("📸 Режим камеры включён!", "ai")
        self.history.add("camera", "Включён режим камеры")
        self.camera_overlay = ctk.CTkFrame(self.content_container, fg_color="#000000", corner_radius=25, border_width=2, border_color="#00d9ff")
        self.camera_overlay.pack(fill="both", expand=True, padx=60, pady=20)
        self.camera_overlay.lift()
        self.camera_label = ctk.CTkLabel(self.camera_overlay, text="", font=("SF Pro Display", 14))
        self.camera_label.pack(expand=True, fill="both")
        self.camera_text_label = ctk.CTkLabel(self.camera_overlay, text="🎯 Наведите камеру...", font=("SF Pro Display", 18, "bold"), text_color="#00ff88", fg_color="#000000", corner_radius=20)
        self.camera_text_label.place(relx=0.5, rely=0.85, anchor="center")
        ctk.CTkButton(self.camera_overlay, text="✕ Закрыть", command=self.disable_camera_mode, width=150, height=45, corner_radius=22, fg_color="#ff0044").place(relx=0.5, rely=0.95, anchor="center")
        self.start_camera()

    def disable_camera_mode(self):
        self.camera_mode = False
        if self.camera_cap: self.camera_cap.release(); self.camera_cap = None
        if self.camera_overlay: self.camera_overlay.destroy(); self.camera_overlay = None
        self.camera_label = None; self.camera_text_label = None
        self.add_message("📸 Камера выключена", "ai")
        self.history.add("camera", "Выключен режим камеры")

    def start_camera(self):
        if not self.camera_cap:
            for i in range(3):
                cap = cv2.VideoCapture(i)
                if cap.isOpened(): self.camera_cap = cap; break
                cap.release()
        if self.camera_cap: self.update_camera_frame()
        else: self.add_message("❌ Камера не найдена", "ai")

    def update_camera_frame(self):
        if not self.camera_mode or not self.camera_cap or not self.camera_label: return
        ret, frame = self.camera_cap.read()
        if ret:
            frame = cv2.resize(frame, (800, 450))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 450))
            self.camera_label.configure(image=img_tk, text=""); self.camera_label.image = img_tk
        self.after(30, self.update_camera_frame)

    def send_photo(self):
        file_path = filedialog.askopenfilename(title="Выберите фото", filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.add_message("🖼️ Анализирую фото...", "ai")
            self.history.add("photo", "Отправлено фото на анализ", os.path.basename(file_path))
            threading.Thread(target=self.analyze_photo, args=(file_path,), daemon=True).start()

    def analyze_photo(self, file_path):
        try:
            response = ollama.chat(model='llava:7b', messages=[{'role': 'user', 'content': 'Опиши что на фото.', 'images': [file_path]}])
            self.after(0, lambda: self.add_message(f"👁️ {response['message']['content']}", "ai"))
            self.history.add("photo", "Фото проанализировано", response['message']['content'][:50])
        except Exception as e: self.after(0, lambda: self.add_message(f"Ошибка: {str(e)}", "ai"))

    def new_chat(self):
        chat_id = len(self.chats) + 1
        self.chats.append({"id": chat_id, "title": "Новый чат", "messages": []})
        self.current_chat_id = chat_id; self.current_chat = []
        self.chat_title.configure(text="Новый чат")
        for widget in self.chat_frame.winfo_children(): widget.destroy()
        self.add_message("Новый чат создан! 🚀", "ai", save=False)
        self.history.add("chat", "Создан новый чат", f"Чат #{chat_id}")

    def open_settings(self):
        self.history.add("settings", "Открыты настройки")
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("⚙️ Настройки"); settings_window.geometry("400x300")
        ctk.CTkLabel(settings_window, text="🎵 Громкость музыки", font=("SF Pro Display", 14)).pack(pady=10)
        music_slider = ctk.CTkSlider(settings_window, from_=0, to=100, command=lambda v: setattr(self, 'music_volume', int(v)))
        music_slider.set(self.music_volume); music_slider.pack(pady=10)
        ctk.CTkButton(settings_window, text="Закрыть", command=settings_window.destroy, width=200, height=40, corner_radius=20).pack(pady=20)

    def open_games_menu(self):
        self.history.add("game", "Открыто меню игр")
        self.add_message("🎮 Меню игр открыто", "ai")

    def add_message(self, text, sender, save=True):
        if not hasattr(self, 'chat_frame'): return
        theme = THEMES[self.current_theme]
        if save:
            self.current_chat.append({"text": text, "sender": sender})
            for chat in self.chats:
                if chat["id"] == self.current_chat_id:
                    chat["messages"] = self.current_chat
                    if len(text) > 30: chat["title"] = text[:30] + "..."
                    break
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=4, padx=60, anchor="e" if sender == "user" else "w")
        if sender == "user":
            msg_box = ctk.CTkFrame(msg_frame, fg_color=theme["message_user"], corner_radius=25)
            msg_box.pack(fill="x")
            ctk.CTkLabel(msg_box, text=text, font=("SF Pro Display", 14), text_color="#ffffff", wraplength=600, justify="left", fg_color="transparent").pack(pady=12, padx=18, anchor="w")
        else:
            outer = ctk.CTkFrame(msg_frame, fg_color="transparent"); outer.pack(fill="x")
            avatar = ctk.CTkFrame(outer, fg_color="#2a2a2a", corner_radius=20, width=40, height=40); avatar.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(avatar, text="🤖", font=("SF Pro Display", 20), fg_color="transparent").pack(expand=True)
            msg_container = ctk.CTkFrame(outer, fg_color=theme["message_ai"], corner_radius=25); msg_container.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(msg_container, text=text, font=("SF Pro Display", 14), text_color=theme["text"], wraplength=600, justify="left", fg_color="transparent").pack(pady=12, padx=18, anchor="w")
            copy_btn = ctk.CTkButton(msg_container, text="📋 Копировать", width=110, height=32, corner_radius=16, fg_color="#2a2a2a", hover_color="#3a3a3a", command=lambda t=text: self.copy_to_clipboard(t))
            copy_btn.pack(pady=(0, 12), padx=18, anchor="w")
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def copy_to_clipboard(self, text):
        self.clipboard_clear(); self.clipboard_append(text); self.update()
        self.history.add("system", "Скопирован текст в буфер", text[:50])

    def speak(self, text):
        def _do_speak():
            self.is_speaking = True; self.audio_playing = True
            try:
                clean_text = ''.join(c for c in text if ord(c) < 128 or c.isalpha() or c.isspace() or c in '.,!?-')
                subprocess.run(["say", "-v", "Milena", clean_text])
            except: pass
            finally:
                self.is_speaking = False; self.audio_playing = False; time.sleep(1)
        threading.Thread(target=_do_speak, daemon=True).start()

    def send_message(self):
        user_input = self.entry.get().strip()
        if not user_input: return
        self.entry.delete(0, "end")
        self.add_message(user_input, "user")
        self.history.add("message", "Отправлено сообщение", user_input[:50])
        self.send_btn.configure(text="💭")
        threading.Thread(target=self.process_ai_response, args=(user_input,), daemon=True).start()

    def process_ai_response(self, user_input):
        try:
            prompt = f"{SMART_PROMPT}\n\nПользователь: {user_input}\n\nТвой ответ:"
            response = ollama.chat(model='qwen2.5:7b', messages=[{'role': 'user', 'content': prompt}], options={'num_predict': 100, 'temperature': 0.7, 'keep_alive': '30m'})
            reply = response['message']['content']
            self.after(0, lambda: self.send_btn.configure(text="➤"))
            self.after(0, lambda: self.add_message(reply, "ai"))
            self.after(200, lambda: self.speak(reply))
            self.history.add("message", "Получен ответ ИИ", reply[:50])
        except Exception as e:
            self.after(0, lambda: self.send_btn.configure(text="➤"))
            self.after(0, lambda: self.add_message(f"❌ Ошибка: {str(e)}", "ai"))

    def toggle_listening(self):
        self.wake_word_active = not self.wake_word_active
        if self.wake_word_active:
            self.wake_indicator.configure(text="🎤 Слушаю 'Джарвис'...", text_color="#ffaa00")
            threading.Thread(target=self.wake_word_loop, daemon=True).start()
            self.history.add("system", "Включено голосовое прослушивание")
        else:
            self.wake_indicator.configure(text="🔇 Выключено", text_color="#ff0044")
            self.history.add("system", "Выключено голосовое прослушивание")

    def process_voice_command(self, text):
        text_lower = text.lower()
        self.add_message(f"🎤 Вы: {text}", "user")
        self.history.add("command", "Голосовая команда", text[:50])
        
        if "врем" in text_lower or "час" in text_lower:
            now = datetime.now(); msg = f"Сейчас {now.strftime('%H:%M')}"
            self.add_message(f"⏰ {msg}", "ai"); self.speak(msg); return
        
        for station_name, url in RADIO_STATIONS.items():
            if station_name in text_lower:
                self.add_message(f"📻 Включаю {station_name}", "ai")
                self.history.add("radio", f"Включено радио: {station_name}")
                return
        
        if "скрин" in text_lower:
            self.take_screenshot(); return
        if "мем" in text_lower:
            self.send_meme(); return
        
        self.entry.delete(0, "end"); self.entry.insert(0, text); self.send_message()

    def take_screenshot(self):
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        self.add_message(f"📷 Скриншот: {filename}", "ai")
        self.history.add("screenshot", "Сделан скриншот", filename)

    def send_meme(self):
        try:
            res = requests.get("https://meme-api.com/gimme", timeout=10)
            if res.status_code == 200:
                data = res.json(); self.add_message(f"😂 {data.get('title', 'Мем')}", "ai")
                self.history.add("meme", "Отправлен мем", data.get('title', '')[:50])
        except: self.add_message("Ошибка загрузки мема", "ai")

    def enter_robot_mode(self):
        self.add_message("🤖 Режим робота в разработке", "ai")
        self.history.add("system", "Попытка войти в режим робота")

if __name__ == "__main__":
    splash = SplashScreen(); splash.mainloop()
    app = AIAssistant(); app.mainloop()
