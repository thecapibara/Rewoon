# -----------------------------
# File: ui.py (Modern Themed Version)
# -----------------------------
# Description: Manages the graphical user interface (GUI) and system tray icon.
# -----------------------------

import tkinter as tk
from tkinter import filedialog, messagebox
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw
import os

# --- NEW: Import ttkbootstrap instead of standard tkinter ---
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import config
import sound_player

class AppUI:
    def __init__(self):
        # --- CHANGED: Use a themed Window. 'superhero' is a great dark theme. ---
        # Other good themes: 'darkly', 'cyborg', 'vapor'
        self.root = ttk.Window(themename="superhero")
        self.root.title("Rewoon")
        self.root.geometry("600x320")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.tray_icon = None
        self.icon_path = os.path.join("assets", "icon.png")
        self._create_widgets()

    def _create_widgets(self):
        # Use a main frame with some padding
        main_frame = ttk.Frame(self.root, padding=(20, 20))
        main_frame.pack(expand=True, fill=BOTH)

        # --- NEW: Configure the grid layout ---
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # --- Mode Selection (Row 0) ---
        mode_frame = ttk.LabelFrame(main_frame, text="Scare Mode", padding=(10, 5))
        mode_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        
        self.mode_var = tk.StringVar(value=config.scare_mode)
        self.radio_all = ttk.Radiobutton(mode_frame, text="All (Mixed)", variable=self.mode_var, value="all", command=self._mode_changed)
        self.radio_all.pack(side=LEFT, expand=True)
        self.radio_sound = ttk.Radiobutton(mode_frame, text="Sound Only", variable=self.mode_var, value="sound", command=self._mode_changed)
        self.radio_sound.pack(side=LEFT, expand=True)
        self.radio_video = ttk.Radiobutton(mode_frame, text="Video Only", variable=self.mode_var, value="video", command=self._mode_changed)
        self.radio_video.pack(side=LEFT, expand=True)

        # --- File Controls (Row 1) ---
        self.select_sound_button = ttk.Button(
            main_frame,
            text="Add Sounds",
            command=self._select_sounds,
            bootstyle="secondary"
        )
        self.select_sound_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.select_video_button = ttk.Button(
            main_frame,
            text="Add Videos",
            command=self._select_videos,
            bootstyle="secondary"
        )
        self.select_video_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # --- Timer Controls (Row 2) ---
        timer_frame = ttk.Frame(main_frame)
        timer_frame.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        
        ttk.Label(timer_frame, text="Min Delay (s):").pack(side=LEFT, padx=(0,5))
        self.min_var = tk.StringVar(value=str(config.min_delay))
        ttk.Entry(timer_frame, textvariable=self.min_var, width=5).pack(side=LEFT)
        
        ttk.Label(timer_frame, text="Max Delay (s):").pack(side=LEFT, padx=(15,5))
        self.max_var = tk.StringVar(value=str(config.max_delay))
        ttk.Entry(timer_frame, textvariable=self.max_var, width=5).pack(side=LEFT)
        
        ttk.Button(timer_frame, text="Reset", command=self._reset_timers, bootstyle="outline-secondary").pack(side=RIGHT, padx=(10,0))

        # --- Start Button (Row 3) ---
        self.start_button = ttk.Button(
            main_frame,
            text="Start Rewoon",
            command=self._start_app,
            state=DISABLED,
            bootstyle="success" 
        )
        self.start_button.grid(row=3, column=0, columnspan=2, padx=5, pady=(10, 5), sticky="ew")

        # --- Status Label (Row 4) ---
        self.status_label = ttk.Label(
            main_frame,
            text="0 sound(s), 0 video(s) selected",
            anchor="center"
        )
        self.status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Update initial state in case files were auto-loaded
        self._update_status_label()

    def _reset_timers(self):
        self.min_var.set("10")
        self.max_var.set("600")

    def _mode_changed(self):
        config.scare_mode = self.mode_var.get()
        self._update_status_label()
        
    def _update_status_label(self):
        s_count = len(config.sound_file_paths)
        v_count = len(config.video_file_paths)
        
        if config.scare_mode == "sound":
            text = f"{s_count} sound(s) selected"
        elif config.scare_mode == "video":
            text = f"{v_count} video(s) selected"
        else:
            text = f"{s_count} sound(s), {v_count} video(s) selected"
            
        self.status_label.config(text=text)
        self._update_start_button_state()

    def _update_start_button_state(self):
        s_count = len(config.sound_file_paths)
        v_count = len(config.video_file_paths)
        
        # Enable/Disable radiobuttons based on file counts
        self.radio_sound.config(state=NORMAL if s_count > 0 else DISABLED)
        self.radio_video.config(state=NORMAL if v_count > 0 else DISABLED)
        # "All" mode implies both should be available to mix, but if only one exists we disable it
        self.radio_all.config(state=NORMAL if (s_count > 0 and v_count > 0) else DISABLED)

        # Auto-switch mode if the current mode just became disabled
        if config.scare_mode == "video" and v_count == 0:
            config.scare_mode = "sound" if s_count > 0 else "all"
            self.mode_var.set(config.scare_mode)
        elif config.scare_mode == "sound" and s_count == 0:
            config.scare_mode = "video" if v_count > 0 else "all"
            self.mode_var.set(config.scare_mode)
        elif config.scare_mode == "all" and (s_count == 0 or v_count == 0):
            if s_count > 0:
                config.scare_mode = "sound"
                self.mode_var.set("sound")
            elif v_count > 0:
                config.scare_mode = "video"
                self.mode_var.set("video")
        
        # Finally determine if the app can start
        can_start = False
        if config.scare_mode == "all" and (s_count > 0 and v_count > 0):
            can_start = True
        elif config.scare_mode == "sound" and s_count > 0:
            can_start = True
        elif config.scare_mode == "video" and v_count > 0:
            can_start = True
            
        self.start_button.config(state=NORMAL if can_start else DISABLED)

    def _select_sounds(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Sound Files",
            filetypes=(("Audio Files", "*.wav *.mp3"), ("All files", "*.*"))
        )
        if file_paths:
            existing_abs = [os.path.abspath(p) for p in config.sound_file_paths]
            for path in file_paths:
                abs_p = os.path.abspath(path)
                if abs_p not in existing_abs:
                    config.sound_file_paths.append(path)
                    existing_abs.append(abs_p)
            self._update_status_label()

    def _select_videos(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=(("Video Files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*"))
        )
        if file_paths:
            existing_abs = [os.path.abspath(p) for p in config.video_file_paths]
            for path in file_paths:
                abs_p = os.path.abspath(path)
                if abs_p not in existing_abs:
                    config.video_file_paths.append(path)
                    existing_abs.append(abs_p)
            self._update_status_label()

    def _start_app(self):
        if not self._save_settings():
            return
        
        # Validation is handled by the button state, but good to check anyway
        if config.scare_mode == "sound" and not config.sound_file_paths:
            messagebox.showerror("Error", "Please select at least one sound file for Sound Mode!")
            return
        elif config.scare_mode == "video" and not config.video_file_paths:
            messagebox.showerror("Error", "Please select at least one video file for Video Mode!")
            return
        elif config.scare_mode == "all" and not config.sound_file_paths and not config.video_file_paths:
            messagebox.showerror("Error", "Please select at least one sound or video file!")
            return
        
        if sound_player.start():
            info_message = (
                "Rewoon is now active in the system tray.\n\n"
                "To exit completely, right-click the tray icon and select 'Exit'."
            )
            messagebox.showinfo("Rewoon is Active", info_message)

            self.root.withdraw()
            self._setup_tray()
        else:
            messagebox.showwarning("Warning", "Rewoon is already running.")

    def _on_closing(self):
        if config.is_running:
            self.root.withdraw()
            if not (self.tray_icon and self.tray_icon.visible):
                self._setup_tray()
        else:
            self.root.destroy()

    def _setup_tray(self):
        if self.tray_icon and self.tray_icon.visible:
            return
        try:
            image = Image.open(self.icon_path)
        except FileNotFoundError:
            print(f"Warning: '{self.icon_path}' not found. Using default generated icon.")
            image = Image.new('RGB', (64, 64), 'black')
            dc = ImageDraw.Draw(image)
            dc.rectangle((32, 0, 64, 32), fill='red')
            dc.rectangle((0, 32, 32, 64), fill='red')
        menu = (item('Show', self._show_window), item('Exit', self._quit_window))
        self.tray_icon = pystray.Icon("Rewoon", image, "Rewoon", menu)
        self.tray_icon.run()

    def _show_window(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.deiconify()
        self.root.lift()

    def _quit_window(self):
        self._save_settings(show_errors=False)
        sound_player.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        
    def _save_settings(self, show_errors=True):
        try:
            min_d_str = self.min_var.get()
            max_d_str = self.max_var.get()
            
            if not min_d_str.isdigit() or not max_d_str.isdigit():
                if show_errors: messagebox.showerror("Error", "Timers must be valid numbers!")
                return False
                
            min_d = int(min_d_str)
            max_d = int(max_d_str)
            
            # Strict Validation
            if min_d < 10:
                if show_errors: messagebox.showerror("Error", "Minimum delay cannot be less than 10 seconds.")
                return False
            if max_d > 1200:
                if show_errors: messagebox.showerror("Error", "Maximum delay cannot be greater than 1200 seconds.")
                return False
            if max_d - min_d < 30:
                if show_errors: messagebox.showerror("Error", "The gap between Min and Max must be at least 30 seconds.")
                return False
            
            config.min_delay = min_d
            config.max_delay = max_d
            
            import configparser
            config_parser = configparser.ConfigParser()
            config_parser.read('config.ini')
            if 'Settings' not in config_parser:
                config_parser['Settings'] = {}
            config_parser['Settings']['min_delay'] = str(min_d)
            config_parser['Settings']['max_delay'] = str(max_d)
            with open('config.ini', 'w') as configfile:
                config_parser.write(configfile)
                
            return True
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False

    def run(self):
        self.root.mainloop()
