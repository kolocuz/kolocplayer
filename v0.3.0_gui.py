import os
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pyglet
from pyglet.media import Player
import glob
import webbrowser

player = Player()

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
        "version": "Версия 0.6.0",
        "author": "Автор: koloc",
        "description": "Простой и удобный музыкальный плеер",
        "error": "Ошибка",
        "play_error": "Не удалось воспроизвести:",
        "github": "Открыть GitHub",
        "github_url": "https://github.com/kolocuz/kolocplayer"
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
        "version": "Version 0.6.0",
        "author": "Author: koloc",
        "description": "Simple and convenient music player",
        "error": "Error",
        "play_error": "Failed to play:",
        "github": "Open GitHub",
        "github_url": "https://github.com/kolocuz/kolocplayer"
    }
}

def get_system_language():
    try:
        lang = os.environ.get('LANG', 'en_US').split('.')[0]
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
        
        ctk.set_appearance_mode("dark")
        self.lang = self.config.get("lang", "en")
        
        self.window = ctk.CTk()
        self.window.title("KolocPlayer")
        self.window.geometry("340x190")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)

        self.accent = "#D4782F"
        self.slider_bg = "#3A3A3A"

        self.current_file = None
        self.is_playing = False
        self.is_paused = False

        self.marquee_text = TEXTS[self.lang]["no_track"]
        self.marquee_offset = 0
        self.marquee_running = False

        self.build_ui()
        self.apply_config()
        self.update_progress()

    def _(self, key):
        return TEXTS[self.lang].get(key, key)

    def build_ui(self):
        # Бегущая строка
        self.marquee_label = ctk.CTkLabel(
            self.window, text=self.marquee_text,
            font=("Arial", 11, "bold"), text_color="#FFFFFF",
            anchor="center", width=340
        )
        self.marquee_label.place(x=0, y=10)

        # Кнопки управления - растянутые
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

        # Прогресс
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

        # Нижняя панель
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

    def on_volume_change(self, value):
        vol = int(float(value))
        self.volume_value.configure(text=f"{vol}%")
        player.volume = vol / 100
        self.config["volume"] = vol
        save_config(self.config)

    # === Бегущая строка ===
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
        self.window.after(400, self._animate_marquee)

    def stop_marquee(self):
        self.marquee_running = False

    def set_track_label(self, text):
        self.marquee_text = text
        self.stop_marquee()
        self.marquee_label.configure(text=text)
        self.start_marquee()

    # === Управление музыкой ===
    def add_music(self):
        file = filedialog.askopenfilename(
            title=self._("add"),
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a"), ("All files", "*")]
        )
        if not file:
            return
        self.stop_music(keep_file=False)
        self.current_file = file
        self.set_track_label(f"⏸ {os.path.basename(file)}")

    def play_music(self):
        if not self.current_file:
            self.add_music()
            if not self.current_file:
                return
        if self.is_playing:
            return
        if self.is_paused:
            player.play()
            self.is_playing = True
            self.is_paused = False
            return
        self.stop_music(keep_file=True)
        try:
            sound = pyglet.media.load(self.current_file)
            player.queue(sound)
            player.play()
            self.is_playing = True
            self.is_paused = False
            self.set_track_label(f"▶ {os.path.basename(self.current_file)}")
            player.push_handlers(on_eos=self.on_track_end)
        except Exception as e:
            messagebox.showerror(self._("error"), f"{self._('play_error')}\n{e}")

    def on_track_end(self):
        player.pause()
        player.seek(0)
        self.is_playing = False
        self.is_paused = False
        self.set_track_label(f"⏹ {os.path.basename(self.current_file)}")

    def pause_music(self):
        if player.playing:
            player.pause()
            self.is_paused = True
            self.is_playing = False

    def stop_music(self, keep_file=True):
        try:
            player.pause()
            player.seek(0)
            player.pause()
            player.pop_handlers()
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.progress_slider.set(0)
        self.time_left.configure(text="00:00")
        self.time_right.configure(text="00:00")
        if not keep_file:
            self.current_file = None
            self.set_track_label(self._("no_track"))
        else:
            if self.current_file:
                self.set_track_label(f"⏹ {os.path.basename(self.current_file)}")
            else:
                self.set_track_label(self._("no_track"))

    def on_seek(self, value):
        if player.source and (player.playing or self.is_paused):
            try:
                duration = player.source.duration
                if duration > 0:
                    seek_time = (float(value) / 100.0) * duration
                    player.seek(seek_time)
            except Exception:
                pass

    def update_progress(self):
        if player.playing and player.source:
            try:
                duration = player.source.duration
                current = player.time
                if duration > 0:
                    percent = (current / duration) * 100
                    self.progress_slider.set(percent)
                    c_m = int(current // 60)
                    c_s = int(current % 60)
                    d_m = int(duration // 60)
                    d_s = int(duration % 60)
                    self.time_left.configure(text=f"{c_m:02d}:{c_s:02d}")
                    self.time_right.configure(text=f"{d_m:02d}:{d_s:02d}")
            except Exception:
                pass
        else:
            if not self.is_paused:
                self.progress_slider.set(0)
                self.time_left.configure(text="00:00")
                self.time_right.configure(text="00:00")
        self.window.after(500, self.update_progress)

    def open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        
        self.settings_window = ctk.CTkToplevel(self.window)
        self.settings_window.title(self._("settings_title"))
        self.settings_window.geometry("280x180")
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self.window)

        ctk.CTkLabel(self.settings_window, text=self._("settings_title"),
                     font=("Arial", 14, "bold"), text_color=self.accent).pack(pady=10)

        # Настройка языка
        lang_frame = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        lang_frame.pack(pady=15)
        ctk.CTkLabel(lang_frame, text=self._("language") + ":", font=("Arial", 11)).pack(side="left", padx=10)
        
        lang_var = ctk.StringVar(value=self.lang)
        lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["ru", "en"],
            variable=lang_var,
            command=self.change_language,
            width=100
        )
        lang_menu.pack(side="left", padx=10)

        # Кнопки
        btn_frame = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        btn_frame.pack(pady=20)

        def show_about():
            about_window = ctk.CTkToplevel(self.settings_window)
            about_window.title(self._("about_title"))
            about_window.geometry("320x220")
            about_window.resizable(False, False)
            about_window.transient(self.settings_window)
            about_window.focus_force()

            ctk.CTkLabel(about_window, text="🎵 KolocPlayer", font=("Arial", 16, "bold"), text_color=self.accent).pack(pady=10)
            ctk.CTkLabel(about_window, text=self._("version"), font=("Arial", 11)).pack()
            ctk.CTkLabel(about_window, text=self._("author"), font=("Arial", 11)).pack(pady=3)
            ctk.CTkLabel(about_window, text=self._("description"), font=("Arial", 10), justify="center").pack(pady=5)
            
            github_btn = ctk.CTkButton(
                about_window, 
                text=self._("github"), 
                fg_color=self.accent,
                command=lambda: webbrowser.open(self._("github_url"))
            )
            github_btn.pack(pady=10)
            
            ctk.CTkButton(about_window, text=self._("close"), fg_color=self.slider_bg, 
                         command=about_window.destroy).pack(pady=5)

        ctk.CTkButton(btn_frame, text=self._("about"), fg_color=self.slider_bg,
                      command=show_about, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text=self._("close"), fg_color=self.accent,
                      command=self.settings_window.destroy, width=100).pack(side="left", padx=10)

    def change_language(self, lang):
        if lang == self.lang:
            return
        self.lang = lang
        self.config["lang"] = lang
        save_config(self.config)
        
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        
        self.update_tooltips()
        
        if not self.current_file:
            self.set_track_label(self._("no_track"))
        
        messagebox.showinfo(self._("settings_title"), 
                           "Language changed. Please restart the app for full effect.\n"
                           "Язык изменён. Перезапустите приложение для полного эффекта.")

    def update_tooltips(self):
        for btn, tip_text in [
            (self.stop_btn, self._("stop")),
            (self.play_btn, self._("play")),
            (self.pause_btn, self._("pause")),
            (self.settings_btn, self._("settings")),
            (self.add_btn, self._("add"))
        ]:
            for event in ["<Enter>", "<Leave>"]:
                try:
                    btn.unbind(event)
                except:
                    pass
            Tooltip(btn, tip_text)

    def apply_config(self):
        vol = self.config.get("volume", 80)
        if vol == 0:
            vol = 80
        self.volume_slider.set(vol)
        player.volume = vol / 100
        self.volume_value.configure(text=f"{vol}%")

    def quit_app(self):
        save_config(self.config)
        self.window.destroy()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = MusicPlayer()
    app.run()
