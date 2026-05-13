import os
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pyglet
from pyglet.media import Player
import webbrowser
import threading
import gc

CONFIG_DIR = os.path.expanduser("~/.config/kolocplayer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)
TEXTS = {
    "ru": {
        "no_track": "Нет трека",
        "stop": "Стоп",
        "play": "Играть",
        "pause": "Пауза",
        "settings": "Настройки",
        "add": "Добавить",
        "settings_title": "Настройки",
        "language": "Язык",
        "about": "О программе",
        "close": "Закрыть",
        "about_title": "О программе",
        "version": "Версия 0.4.1",
        "author": "Автор: koloc",
        "description": "Простой и удобный музыкальный плеер",
        "loading": "Загрузка...",
        "error": "Ошибка",
        "play_error": "Не удалось воспроизвести:",
        "github": "Открыть GitHub",
        "github_url": "github.com"  # Укажите тут полную ссылку, например: github.com
    },
    "en": {
        "no_track": "No track",
        "stop": "Stop",
        "play": "Play",
        "pause": "Pause",
        "settings": "Settings",
        "add": "Add",
        "settings_title": "Settings",
        "language": "Language",
        "about": "About",
        "close": "Close",
        "about_title": "About",
        "version": "Version 0.4.1",
        "author": "Author: koloc",
        "description": "Simple and convenient music player",
        "loading": "Loading...",
        "error": "Error",
        "play_error": "Failed to play:",
        "github": "Open GitHub",
        "github_url": "github.com"  # И тут тоже полную ссылку
    }
}

def get_system_language():
    try:
        lang = os.environ.get('LANG', 'en_US').split('.')
        if lang.startswith('ru'):
            return 'ru'
    except:
        pass
    return 'en'

def load_config():
    default = {"volume": 80, "lang": get_system_language()}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if config.get("volume", 0) == 0:
                config["volume"] = 80
            if config.get("lang") not in ["ru", "en"]:
                config["lang"] = get_system_language()
            return {**default, **config}
    except Exception:
        return default

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = ctk.CTkToplevel()
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        ctk.CTkLabel(
            tw, text=self.text,
            fg_color="#2D2D2D", text_color="#FFFFFF",
            corner_radius=4, font=("Arial", 10)
        ).pack(padx=4, pady=2)

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class MusicPlayer:
    def __init__(self):
        self.config = load_config()
        
        # Настройка темы
        ctk.set_appearance_mode("dark")
        self.lang = self.config.get("lang", "en")
        
        # Чистая инициализация стандартного CustomTkinter окна
        self.window = ctk.CTk()
        self.window.title("KolocPlayer")
        self.window.geometry("340x190")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.accent = "#D4782F"
        self.slider_bg = "#3A3A3A"
        
        # Один глобальный плеер на всё время работы
        self.player = Player()
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.current_volume = self.config.get("volume", 80)
        self.loading = False
        self.current_sound = None
        
        self.player.volume = self.current_volume / 100
        
        # Бегущая строка
        self.marquee_text = TEXTS[self.lang]["no_track"]
        self.marquee_offset = 0
        self.marquee_running = False
        self.marquee_after_id = None
        
        self.build_ui()
        self.setup_hotkeys()
        self.apply_config()
        self.update_progress()

    def _(self, key):
        return TEXTS[self.lang].get(key, key)

    def build_ui(self):
        self.marquee_label = ctk.CTkLabel(
            self.window, text=self.marquee_text,
            font=("Arial", 11, "bold"), text_color="#FFFFFF",
            anchor="center", width=340
        )
        self.marquee_label.place(x=0, y=10)
        
        btn_width = 50
        play_width = 80
        total_width = btn_width*2 + play_width + 20
        start_x = (340 - total_width) // 2
        
        self.stop_btn = ctk.CTkButton(
            self.window, text="⏹", width=btn_width, height=35,
            fg_color=self.slider_bg, command=self.stop_music,
            font=("Arial", 16)
        )
        self.stop_btn.place(x=start_x, y=45)
        Tooltip(self.stop_btn, self._("stop"))
        
        self.play_btn = ctk.CTkButton(
            self.window, text="▶", width=play_width, height=35,
            fg_color=self.accent, command=self.play_music,
            font=("Arial", 16)
        )
        self.play_btn.place(x=start_x + btn_width + 10, y=45)
        Tooltip(self.play_btn, self._("play"))
        
        self.pause_btn = ctk.CTkButton(
            self.window, text="⏸", width=btn_width, height=35,
            fg_color=self.slider_bg, command=self.pause_music,
            font=("Arial", 16)
        )
        self.pause_btn.place(x=start_x + btn_width + play_width + 20, y=45)
        Tooltip(self.pause_btn, self._("pause"))
        
        self.progress_slider = ctk.CTkSlider(
            self.window, from_=0, to=100, width=320,
            fg_color=self.slider_bg, progress_color=self.accent,
            command=self.on_seek
        )
        self.progress_slider.place(x=10, y=95)
        self.progress_slider.set(0)
        
        self.time_left = ctk.CTkLabel(
            self.window, text="00:00", font=("Arial", 8), text_color="gray"
        )
        self.time_left.place(x=10, y=110)
        self.time_right = ctk.CTkLabel(
            self.window, text="00:00", font=("Arial", 8), text_color="gray"
        )
        self.time_right.place(x=300, y=110)
        
        self.settings_btn = ctk.CTkButton(
            self.window, text="⚙️", width=30, fg_color=self.slider_bg,
            command=self.open_settings
        )
        self.settings_btn.place(x=10, y=145)
        Tooltip(self.settings_btn, self._("settings"))
        
        self.volume_slider = ctk.CTkSlider(
            self.window, from_=0, to=100, width=170,
            fg_color=self.slider_bg, progress_color=self.accent,
            command=self.on_volume_change
        )
        self.volume_slider.place(x=50, y=150)
        
        self.volume_value = ctk.CTkLabel(
            self.window, text="", font=("Arial", 9), text_color="gray"
        )
        self.volume_value.place(x=225, y=148)
        
        self.add_btn = ctk.CTkButton(
            self.window, text="+", width=30, height=30,
            fg_color=self.accent, command=self.add_music,
            font=("Arial", 14, "bold")
        )
        self.add_btn.place(x=290, y=143)
        Tooltip(self.add_btn, self._("add"))

    def setup_hotkeys(self):
        self.window.bind("<space>", lambda event: self.play_music())
        self.window.bind("<Escape>", lambda event: self.stop_music())
        self.window.bind("<Up>", lambda event: self.change_volume_step(5))
        self.window.bind("<Down>", lambda event: self.change_volume_step(-5))

    def change_volume_step(self, step):
        new_vol = max(0, min(100, self.current_volume + step))
        self.volume_slider.set(new_vol)
        self.on_volume_change(new_vol)

    def on_volume_change(self, value):
        vol = int(float(value))
        self.volume_value.configure(text=f"{vol}%")
        self.current_volume = vol
        if self.player:
            self.player.volume = vol / 100
        self.config["volume"] = vol
        save_config(self.config)

    def set_track_label(self, text_with_icon):
        self.stop_marquee()
        self.marquee_text = text_with_icon
        if len(self.marquee_text) > 30:
            self.start_marquee()
        else:
            self.marquee_label.configure(text=self.marquee_text)

    def start_marquee(self):
        if self.marquee_running:
            return
        if len(self.marquee_text) > 30:
            self.marquee_running = True
            self.marquee_offset = 0
            self.marquee_display_text = self.marquee_text + "   " + self.marquee_text
            self._animate_marquee()

    def _animate_marquee(self):
        if not self.marquee_running:
            return
        displayed = self.marquee_display_text[self.marquee_offset:self.marquee_offset+30]
        self.marquee_label.configure(text=displayed)
        self.marquee_offset += 1
        if self.marquee_offset >= len(self.marquee_display_text) - 30:
            self.marquee_offset = 0
        self.marquee_after_id = self.window.after(200, self._animate_marquee)

    def stop_marquee(self):
        self.marquee_running = False
        if self.marquee_after_id:
            self.window.after_cancel(self.marquee_after_id)
            self.marquee_after_id = None
        self.marquee_label.configure(text=self.marquee_text)

    def apply_config(self):
        self.volume_slider.set(self.current_volume)
        self.volume_value.configure(text=f"{self.current_volume}%")

    def add_music(self):
        if self.loading:
            return
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a")]
        )
        if file_path:
            self.current_file = file_path
            self.reset_and_prepare_track()

    def reset_and_prepare_track(self):
        """Полная выгрузка из ОЗУ и подготовка трека БЕЗ автоигры"""
        if self.player:
            try:
                self.player.pause()
                while self.player.source is not None:
                    self.player.next_source()
            except:
                pass

        self.current_sound = None
        self.is_playing = False
        self.is_paused = False
        self.progress_slider.set(0)
        self.time_left.configure(text="00:00")
        self.time_right.configure(text="00:00")
        
        self.loading = True
        self.set_track_label(self._("loading"))
        
        threading.Thread(target=self._load_and_play, args=(self.current_file, False), daemon=True).start()

    def stop_music(self):
        if self.player:
            try:
                self.player.pause()
                if self.player.source is not None:
                    self.player.next_source()
            except Exception as e:
                print(f"Ошибка остановки: {e}")
        
        self.is_playing = False
        self.is_paused = False
        self.progress_slider.set(0)
        self.time_left.configure(text="00:00")
        self.time_right.configure(text="00:00")
        
        self.current_sound = None
        gc.collect()
        
        if self.current_file:
            self.set_track_label(f"⏹ {os.path.basename(self.current_file)}")
        else:
            self.set_track_label(self._("no_track"))

    def play_music(self):
        if not self.current_file or self.loading:
            return
        
        if self.is_playing:
            return
        
        if self.is_paused:
            self.player.play()
            self.is_playing = True
            self.is_paused = False
            self.set_track_label(f"▶ {os.path.basename(self.current_file)}")
        else:
            if self.player:
                try:
                    self.player.pause()
                    while self.player.source is not None:
                        self.player.next_source()
                except:
                    pass

            self.current_sound = None
            self.loading = True
            self.set_track_label(self._("loading"))
            
            threading.Thread(target=self._load_and_play, args=(self.current_file, True), daemon=True).start()

    def pause_music(self):
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.is_paused = True
            self.set_track_label(f"⏸ {os.path.basename(self.current_file)}")

    def _load_and_play(self, file_path, start_immediately):
        try:
            loaded_sound = pyglet.media.load(file_path, streaming=True)
            self.window.after(0, self._finalize_and_start_play, loaded_sound, file_path, start_immediately)
        except Exception as e:
            self.window.after(0, self._on_load_error, str(e))

    def _finalize_and_start_play(self, loaded_sound, file_path, start_immediately):
        try:
            if self.player:
                try:
                    while self.player.source is not None:
                        self.player.next_source()
                except:
                    pass

            self.current_sound = loaded_sound
            self.player.queue(self.current_sound)
            
            if start_immediately:
                self.player.play()
                self.is_playing = True
                self.is_paused = False
                song_name = f"▶ {os.path.basename(file_path)}"
            else:
                self.is_playing = False
                self.is_paused = False
                song_name = f"⏹ {os.path.basename(file_path)}"
                
                if self.player.source:
                    self.time_right.configure(text=self.format_time(self.player.source.duration))
            
            self._on_load_success(song_name)
        except Exception as e:
            self._on_load_error(str(e))
        finally:
            self.loading = False
            gc.collect()

    def _on_load_success(self, song_name):
        self.set_track_label(song_name)

    def _on_load_error(self, err_msg):
        self.set_track_label(self._("no_track"))
        messagebox.showerror(self._("error"), f"{self._('play_error')}\n{err_msg}")
        self.current_file = None
        self.is_playing = False
        self.is_paused = False

    def on_seek(self, value):
        if self.player and self.player.source:
            duration = self.player.source.duration
            target_time = (float(value) / 100) * duration
            self.player.seek(target_time)

    def format_time(self, seconds):
        if seconds is None:
            return "00:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def update_progress(self):
        if self.player and self.player.source and self.is_playing:
            try:
                time_curr = self.player.time
                duration = self.player.source.duration
                
                if duration and time_curr >= duration - 0.5:
                    self.stop_music()
                    return
                
                if duration and duration > 0:
                    progress = (time_curr / duration) * 100
                    self.progress_slider.set(progress)
                    self.time_left.configure(text=self.format_time(time_curr))
                    self.time_right.configure(text=self.format_time(duration))
            except:
                pass
        self.window.after(500, self.update_progress)

    def open_settings(self):
        """Открытие окна настроек и информации о программе"""
        self.settings_win = ctk.CTkToplevel(self.window)
        self.settings_win.title(self._("settings_title"))
        self.settings_win.geometry("280x260")
        self.settings_win.resizable(False, False)
        
        self.settings_win.transient(self.window)
        self.settings_win.wait_visibility()
        self.settings_win.grab_set()
        
        lang_label = ctk.CTkLabel(
            self.settings_win, text=self._("language"), 
            font=("Arial", 12, "bold"), text_color=self.accent
        )
        lang_label.pack(pady=(15, 5))
        
        current_lang_name = "Русский" if self.lang == "ru" else "English"
        self.lang_combo = ctk.CTkComboBox(
            self.settings_win, values=["Русский", "English"],
            width=160, fg_color=self.slider_bg, border_color=self.accent,
            button_color=self.accent, button_hover_color="#B56221",
            command=self.change_language
        )
        self.lang_combo.set(current_lang_name)
        self.lang_combo.pack(pady=5)
        
        separator = ctk.CTkFrame(self.settings_win, height=2, width=240, fg_color="#404040")
        separator.pack(pady=15)
        
        about_label = ctk.CTkLabel(
            self.settings_win, text=self._("about_title"), 
            font=("Arial", 11, "bold"), text_color="gray"
        )
        about_label.pack(pady=2)
        
        version_label = ctk.CTkLabel(self.settings_win, text=self._("version"), font=("Arial", 10))
        version_label.pack(pady=1)
        
        author_label = ctk.CTkLabel(self.settings_win, text=self._("author"), font=("Arial", 10))
        author_label.pack(pady=1)
        
        github_btn = ctk.CTkButton(
            self.settings_win, text=self._("github"), width=160, height=28,
            fg_color="#24292E", hover_color="#333A42", border_width=1, border_color="#444D56",
            command=lambda: webbrowser.open(TEXTS[self.lang]["github_url"])
        )
        github_btn.pack(pady=(12, 5))

    def change_language(self, selected_value):
        """Обработчик смены языка на лету"""
        new_lang = "ru" if selected_value == "Русский" else "en"
        if new_lang == self.lang:
            return
            
        self.lang = new_lang
        self.config["lang"] = new_lang
        save_config(self.config)
        
        self.settings_win.title(self._("settings_title"))
        self.stop_btn.configure(text="⏹")
        Tooltip(self.stop_btn, self._("stop"))
        Tooltip(self.play_btn, self._("play"))
        Tooltip(self.pause_btn, self._("pause"))
        Tooltip(self.settings_btn, self._("settings"))
        Tooltip(self.add_btn, self._("add"))
        
        self.settings_win.destroy()
        self.open_settings()
        
        if not self.current_file:
            self.set_track_label(self._("no_track"))
        elif self.loading:
            self.set_track_label(self._("loading"))

    def quit_app(self):
        self.stop_music()
        self.window.destroy()

if __name__ == "__main__":
    app = MusicPlayer()
    app.window.mainloop()

