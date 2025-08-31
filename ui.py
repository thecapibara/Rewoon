# -----------------------------
# File: ui.py
# -----------------------------
# Description: Manages the graphical user interface (GUI) and system tray icon.
# -----------------------------

import tkinter as tk
from tkinter import filedialog, messagebox
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw
import os # <-- ADDED: To handle file paths correctly

# Import the other modules of our application
import config
import sound_player

class AppUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rewoon")
        self.root.geometry("400x220")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.tray_icon = None
        
        # --- ADDED: Define the path to our icon asset ---
        self.icon_path = os.path.join("assets", "icon.png")

        self._create_widgets()

    # ... (the _create_widgets, _select_sound, _start_app, and _on_closing methods are unchanged) ...
    def _create_widgets(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(expand=True, fill=tk.BOTH)
        self.select_button = tk.Button(main_frame, text="Select Sound", command=self._select_sound)
        self.select_button.pack(pady=5)
        self.sound_label = tk.Label(main_frame, text="No sound selected")
        self.sound_label.pack(pady=5)
        self.start_button = tk.Button(main_frame, text="Start", command=self._start_app)
        self.start_button.pack(pady=5)
        warning_label = tk.Label(
            main_frame,
            text="Warning: Closing this window will hide it in the system tray.\n"
                 "To exit completely, right-click the tray icon and select 'Exit'.",
            fg="red",
            wraplength=380
        )
        warning_label.pack(pady=10)

    def _select_sound(self):
        file_path = filedialog.askopenfilename(
            title="Select a Sound File",
            filetypes=(("Audio Files", "*.wav *.mp3"), ("All files", "*.*"))
        )
        if file_path:
            config.sound_file_path = file_path
            self.sound_label.config(text=f"Selected: ...{config.sound_file_path[-25:]}")

    def _start_app(self):
        if not config.sound_file_path:
            messagebox.showerror("Error", "Please select a sound file first!")
            return
        if sound_player.start():
            messagebox.showinfo("Started", "Rewoon is now active in the system tray!")
            self.root.withdraw()
            self._setup_tray()
        else:
            messagebox.showwarning("Warning", "Rewoon is already running or no sound file was selected.")

    def _on_closing(self):
        if config.is_running:
            self.root.withdraw()
            if not (self.tray_icon and self.tray_icon.visible):
                self._setup_tray()
        else:
            self.root.destroy()
    # ------------------------------------------------------------------------------------------

    def _setup_tray(self):
        if self.tray_icon and self.tray_icon.visible:
            return

        # --- CHANGED: Load icon from file with a fallback ---
        try:
            # Attempt to load the user-provided icon
            image = Image.open(self.icon_path)
        except FileNotFoundError:
            # If icon.png is not found, create the default one
            print(f"Warning: '{self.icon_path}' not found. Using default generated icon.")
            image = Image.new('RGB', (64, 64), 'black')
            dc = ImageDraw.Draw(image)
            dc.rectangle((32, 0, 64, 32), fill='red')
            dc.rectangle((0, 32, 32, 64), fill='red')
        # ----------------------------------------------------

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
