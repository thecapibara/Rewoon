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
        # --- CHANGED: Adjusted size for the new compact layout ---
        self.root.geometry("450x150")
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
        # Create 3 columns of equal weight so they space out evenly
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # --- CHANGED: All buttons are now themed ttk.Buttons placed on the grid ---
        self.select_button = ttk.Button(
            main_frame,
            text="Select Sounds",
            command=self._select_sounds,
            bootstyle="secondary" # A neutral style
        )
        self.select_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.clear_button = ttk.Button(
            main_frame,
            text="Clear Selection",
            command=self._clear_selection,
            bootstyle="secondary"
        )
        self.clear_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        self.start_button = ttk.Button(
            main_frame,
            text="Start",
            command=self._start_app,
            state=DISABLED,
            bootstyle="success" # A prominent green style
        )
        self.start_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

        # --- CHANGED: Themed label, centered under the buttons ---
        self.sound_label = ttk.Label(
            main_frame,
            text="No sounds selected",
            anchor="center"
        )
        self.sound_label.grid(row=1, column=0, columnspan=3, padx=5, pady=10)


    def _select_sounds(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Sound Files",
            filetypes=(("Audio Files", "*.wav *.mp3"), ("All files", "*.*"))
        )
        if file_paths:
            config.sound_file_paths.extend(list(file_paths))
            count = len(config.sound_file_paths)
            self.sound_label.config(text=f"{count} sound(s) selected")
            self.start_button.config(state=NORMAL)

    def _clear_selection(self):
        config.sound_file_paths.clear()
        self.sound_label.config(text="No sounds selected")
        self.start_button.config(state=DISABLED)
        print("Sound selection cleared.")

    def _start_app(self):
        if not config.sound_file_paths:
            messagebox.showerror("Error", "Please select at least one sound file!")
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
        sound_player.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
