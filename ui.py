"""Graphical user interface (ttkbootstrap) and thread-safe system tray integration."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as MenuItem
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, END, LEFT, NORMAL, RIGHT, VERTICAL, Y

import config
import sound_player

logger = logging.getLogger(__name__)


class AppUI:
    """Main Tkinter/ttkbootstrap window and non-blocking pystray tray controller."""

    def __init__(
        self,
        app_config: config.AppConfig | None = None,
        scheduler: sound_player.ScareScheduler | None = None,
    ) -> None:
        self.config = app_config or config.state
        self.scheduler = scheduler or sound_player.scheduler

        self.root = ttk.Window(themename="superhero")
        self.root.title("Rewoon")
        self.root.geometry("640x520")
        self.root.minsize(580, 460)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.tray_icon: pystray.Icon | None = None
        self._tray_hint_shown: bool = False
        self._icon_path = config.ICON_PATH
        self._tree_item_map: dict[str, tuple[str, str]] = {}

        self._create_widgets()
        self._refresh_media_list()
        self._refresh_controls()

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding=(16, 14))
        main_frame.pack(expand=True, fill=BOTH)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # --- Row 0: Scare Mode ---
        mode_frame = ttk.LabelFrame(main_frame, text="Scare Mode", padding=(10, 6))
        mode_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.mode_var = tk.StringVar(value=self.config.scare_mode)
        self.radio_all = ttk.Radiobutton(
            mode_frame,
            text="All (Mixed)",
            variable=self.mode_var,
            value="all",
            command=self._mode_changed,
        )
        self.radio_all.pack(side=LEFT, expand=True)
        self.radio_sound = ttk.Radiobutton(
            mode_frame,
            text="Sound Only",
            variable=self.mode_var,
            value="sound",
            command=self._mode_changed,
        )
        self.radio_sound.pack(side=LEFT, expand=True)
        self.radio_video = ttk.Radiobutton(
            mode_frame,
            text="Video Only",
            variable=self.mode_var,
            value="video",
            command=self._mode_changed,
        )
        self.radio_video.pack(side=LEFT, expand=True)

        # --- Row 1: Media Library ---
        media_frame = ttk.LabelFrame(main_frame, text="Media Library", padding=(10, 8))
        media_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        media_frame.grid_columnconfigure(0, weight=1)
        media_frame.grid_rowconfigure(1, weight=1)

        btn_bar = ttk.Frame(media_frame)
        btn_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Button(
            btn_bar, text="Add Sounds", command=self._select_sounds, bootstyle="secondary"
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            btn_bar, text="Add Videos", command=self._select_videos, bootstyle="secondary"
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            btn_bar,
            text="Remove Selected",
            command=self._remove_selected_media,
            bootstyle="outline-danger",
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            btn_bar,
            text="Rescan Folders",
            command=self._rescan_media,
            bootstyle="outline-secondary",
        ).pack(side=RIGHT)

        tree_container = ttk.Frame(media_frame)
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.media_tree = ttk.Treeview(
            tree_container,
            columns=("kind", "name"),
            show="headings",
            selectmode="extended",
            height=6,
        )
        self.media_tree.heading("kind", text="Type")
        self.media_tree.heading("name", text="File")
        self.media_tree.column("kind", width=80, minwidth=70, stretch=False, anchor="center")
        self.media_tree.column("name", width=440, minwidth=200, stretch=True)
        self.media_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_container, orient=VERTICAL, command=self.media_tree.yview)
        self.media_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Row 2: Timers & Volume ---
        settings_frame = ttk.LabelFrame(main_frame, text="Timers & Volume", padding=(10, 8))
        settings_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        timer_row = ttk.Frame(settings_frame)
        timer_row.pack(fill="x", pady=(0, 8))

        ttk.Label(timer_row, text="Min Delay (s):").pack(side=LEFT, padx=(0, 5))
        self.min_var = tk.StringVar(value=str(self.config.min_delay))
        ttk.Entry(timer_row, textvariable=self.min_var, width=6).pack(side=LEFT)

        ttk.Label(timer_row, text="Max Delay (s):").pack(side=LEFT, padx=(16, 5))
        self.max_var = tk.StringVar(value=str(self.config.max_delay))
        ttk.Entry(timer_row, textvariable=self.max_var, width=6).pack(side=LEFT)

        ttk.Button(
            timer_row,
            text="Reset Defaults",
            command=self._reset_timers,
            bootstyle="outline-secondary",
        ).pack(side=RIGHT)

        volume_row = ttk.Frame(settings_frame)
        volume_row.pack(fill="x")

        ttk.Label(volume_row, text="Volume:").pack(side=LEFT, padx=(0, 8))
        self.volume_var = tk.IntVar(value=self.config.volume)
        self.volume_label = ttk.Label(volume_row, text=f"{self.config.volume}%", width=5)
        self.volume_scale = ttk.Scale(
            volume_row,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.volume_var,
            command=self._on_volume_changed,
        )
        self.volume_scale.pack(side=LEFT, fill="x", expand=True, padx=(0, 8))
        self.volume_label.pack(side=RIGHT)

        # --- Row 3: Action Controls ---
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        action_frame.grid_columnconfigure(0, weight=2)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)
        action_frame.grid_columnconfigure(3, weight=1)

        self.start_stop_button = ttk.Button(
            action_frame,
            text="Start Rewoon",
            command=self._toggle_start_stop,
            bootstyle="success",
        )
        self.start_stop_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.pause_button = ttk.Button(
            action_frame,
            text="Pause",
            command=self._toggle_pause,
            state=DISABLED,
            bootstyle="warning",
        )
        self.pause_button.grid(row=0, column=1, padx=(0, 6), sticky="ew")

        self.test_button = ttk.Button(
            action_frame,
            text="Test Scare",
            command=self._test_scare,
            bootstyle="info",
        )
        self.test_button.grid(row=0, column=2, padx=(0, 6), sticky="ew")

        self.tray_button = ttk.Button(
            action_frame,
            text="Hide to Tray",
            command=self._hide_to_tray,
            state=DISABLED,
            bootstyle="outline-secondary",
        )
        self.tray_button.grid(row=0, column=3, sticky="ew")

        # --- Row 4: Status Bar ---
        self.status_label = ttk.Label(main_frame, text="", anchor="center")
        self.status_label.grid(row=4, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Media & Settings Handlers
    # ------------------------------------------------------------------

    def _on_volume_changed(self, _value: str) -> None:
        vol = int(round(float(self.volume_var.get())))
        self.config.set_volume(vol)
        self.volume_label.config(text=f"{vol}%")

    def _reset_timers(self) -> None:
        self.min_var.set(str(config.DEFAULT_MIN_DELAY))
        self.max_var.set(str(config.DEFAULT_MAX_DELAY))
        self.volume_var.set(config.DEFAULT_VOLUME)
        self._on_volume_changed(str(config.DEFAULT_VOLUME))
        self._save_settings(show_errors=True)

    def _mode_changed(self) -> None:
        self.config.set_mode(self.mode_var.get())
        self._refresh_controls()

    def _refresh_media_list(self) -> None:
        for item_id in self.media_tree.get_children():
            self.media_tree.delete(item_id)
        self._tree_item_map.clear()

        snap = self.config.snapshot()
        for path in snap["sound_file_paths"]:
            item_id = self.media_tree.insert("", END, values=("Sound", os.path.basename(path)))
            self._tree_item_map[item_id] = ("sound", path)

        for path in snap["video_file_paths"]:
            item_id = self.media_tree.insert("", END, values=("Video", os.path.basename(path)))
            self._tree_item_map[item_id] = ("video", path)

    def _refresh_controls(self) -> None:
        snap = self.config.snapshot()
        s_count = len(snap["sound_file_paths"])
        v_count = len(snap["video_file_paths"])
        has_any = s_count > 0 or v_count > 0

        self.radio_sound.config(state=NORMAL if s_count > 0 else DISABLED)
        self.radio_video.config(state=NORMAL if v_count > 0 else DISABLED)
        self.radio_all.config(state=NORMAL if has_any else DISABLED)

        # Auto-switch away from an empty single-type mode if needed
        mode = snap["scare_mode"]
        if mode == "video" and v_count == 0 and s_count > 0:
            self.config.set_mode("sound")
            self.mode_var.set("sound")
        elif mode == "sound" and s_count == 0 and v_count > 0:
            self.config.set_mode("video")
            self.mode_var.set("video")

        can_start = self.config.can_start()
        running = self.scheduler.is_running
        paused = self.scheduler.is_paused

        if running:
            self.start_stop_button.config(
                text="Stop Rewoon", bootstyle="danger", state=NORMAL
            )
            self.pause_button.config(
                text="Resume" if paused else "Pause",
                state=NORMAL,
                bootstyle="info" if paused else "warning",
            )
            self.tray_button.config(state=NORMAL)
        else:
            self.start_stop_button.config(
                text="Start Rewoon",
                bootstyle="success",
                state=NORMAL if can_start else DISABLED,
            )
            self.pause_button.config(text="Pause", state=DISABLED, bootstyle="warning")
            self.tray_button.config(state=DISABLED)

        self.test_button.config(state=NORMAL if can_start else DISABLED)

        state_text = "Paused" if paused else ("Running" if running else "Idle")
        self.status_label.config(
            text=f"Status: {state_text}  |  {s_count} sound(s), {v_count} video(s)"
        )

    def _select_sounds(self) -> None:
        ext_patterns = " ".join(f"*{ext}" for ext in config.AUDIO_EXTENSIONS)
        file_paths = filedialog.askopenfilenames(
            title="Select Sound Files",
            filetypes=(("Audio Files", ext_patterns), ("All files", "*.*")),
        )
        if file_paths:
            self.config.add_sounds(file_paths)
            self._refresh_media_list()
            self._refresh_controls()

    def _select_videos(self) -> None:
        ext_patterns = " ".join(f"*{ext}" for ext in config.VIDEO_EXTENSIONS)
        file_paths = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=(("Video Files", ext_patterns), ("All files", "*.*")),
        )
        if file_paths:
            self.config.add_videos(file_paths)
            self._refresh_media_list()
            self._refresh_controls()

    def _remove_selected_media(self) -> None:
        selected = self.media_tree.selection()
        if not selected:
            return
        for item_id in selected:
            entry = self._tree_item_map.get(item_id)
            if not entry:
                continue
            kind, path = entry
            if kind == "sound":
                self.config.remove_sound(path)
            else:
                self.config.remove_video(path)
        self._refresh_media_list()
        self._refresh_controls()

    def _rescan_media(self) -> None:
        self.config.rescan_media()
        self._refresh_media_list()
        self._refresh_controls()

    # ------------------------------------------------------------------
    # Playback & Lifecycle Handlers
    # ------------------------------------------------------------------

    def _toggle_start_stop(self) -> None:
        if self.scheduler.is_running:
            self._stop_app()
        else:
            self._start_app()

    def _start_app(self) -> None:
        if not self._save_settings(show_errors=True):
            return

        if not self.config.can_start():
            messagebox.showerror(
                "Error", "Please add at least one media file for the selected mode."
            )
            return

        if self.scheduler.start():
            self._refresh_controls()
            self._ensure_tray_running()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                messagebox.showinfo(
                    "Rewoon is Active",
                    "Rewoon is now active in the system tray.\n\n"
                    "You can pause, stop, or exit at any time from the tray menu.",
                )
            self.root.withdraw()
        else:
            messagebox.showwarning("Warning", "Rewoon is already running.")

    def _stop_app(self) -> None:
        self.scheduler.stop()
        self._refresh_controls()

    def _toggle_pause(self) -> None:
        if not self.scheduler.is_running:
            return
        if self.scheduler.is_paused:
            self.scheduler.resume()
        else:
            self.scheduler.pause()
        self._refresh_controls()

    def _test_scare(self) -> None:
        if not self.config.can_start():
            messagebox.showerror("Error", "No media available to test for the selected mode.")
            return

        self.test_button.config(state=DISABLED, text="Playing...")

        def _on_done(_ok: bool) -> None:
            self.root.after(0, self._restore_test_button)

        if not self.scheduler.trigger_test_scare(on_done=_on_done):
            self._restore_test_button()

    def _restore_test_button(self) -> None:
        if self.root.winfo_exists():
            self.test_button.config(text="Test Scare")
            self._refresh_controls()

    def _hide_to_tray(self) -> None:
        self._ensure_tray_running()
        self.root.withdraw()

    def _on_closing(self) -> None:
        if self.scheduler.is_running:
            self._hide_to_tray()
        else:
            self._quit_app()

    # ------------------------------------------------------------------
    # Thread-Safe System Tray (non-blocking run_detached)
    # ------------------------------------------------------------------

    def _load_tray_image(self) -> Image.Image:
        try:
            return Image.open(self._icon_path)
        except OSError:
            logger.warning("Tray icon '%s' not found; using generated fallback.", self._icon_path)
            image = Image.new("RGB", (64, 64), "black")
            draw = ImageDraw.Draw(image)
            draw.rectangle((32, 0, 64, 32), fill="red")
            draw.rectangle((0, 32, 32, 64), fill="red")
            return image

    def _ensure_tray_running(self) -> None:
        if self.tray_icon is not None:
            return

        image = self._load_tray_image()
        menu = pystray.Menu(
            MenuItem("Show Window", self._tray_show_window, default=True),
            MenuItem(
                lambda _item: "Resume" if self.scheduler.is_paused else "Pause",
                self._tray_toggle_pause,
                enabled=lambda _item: self.scheduler.is_running,
            ),
            MenuItem(
                "Stop",
                self._tray_stop,
                enabled=lambda _item: self.scheduler.is_running,
            ),
            MenuItem("Test Scare", self._tray_test_scare),
            pystray.Menu.SEPARATOR,
            MenuItem("Exit", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("Rewoon", image, "Rewoon", menu)
        try:
            self.tray_icon.run_detached()
        except Exception as exc:
            logger.error("Failed to start system tray icon: %s", exc)
            self.tray_icon = None

    def _stop_tray(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None

    # All pystray callbacks run on the tray backend thread -> marshal to Tk main thread!
    def _tray_show_window(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._show_window_on_main_thread)

    def _tray_toggle_pause(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._toggle_pause)

    def _tray_stop(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._stop_app)

    def _tray_test_scare(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._test_scare)

    def _tray_quit(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._quit_app)

    def _show_window_on_main_thread(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._refresh_controls()

    def _quit_app(self) -> None:
        self._save_settings(show_errors=False)
        self.scheduler.stop()
        self._stop_tray()
        if self.root.winfo_exists():
            self.root.destroy()

    # ------------------------------------------------------------------
    # Settings Persistence
    # ------------------------------------------------------------------

    def _save_settings(self, show_errors: bool = True) -> bool:
        try:
            min_d = int(self.min_var.get().strip())
            max_d = int(self.max_var.get().strip())
        except ValueError:
            if show_errors:
                messagebox.showerror("Error", "Timers must be valid whole numbers.")
            return False

        ok, err_msg = config.validate_delays(min_d, max_d)
        if not ok:
            if show_errors:
                messagebox.showerror("Error", err_msg or "Invalid timer settings.")
            return False

        try:
            self.config.set_delays(min_d, max_d)
            self.config.set_mode(self.mode_var.get())
            self.config.set_volume(int(round(float(self.volume_var.get()))))
            self.config.save_settings()
            return True
        except OSError as exc:
            logger.error("Failed to write config.ini: %s", exc)
            if show_errors:
                messagebox.showerror("Error", f"Could not save settings:\n{exc}")
            return False
        except Exception as exc:
            logger.exception("Unexpected error saving settings: %s", exc)
            if show_errors:
                messagebox.showerror("Error", f"Failed to save settings:\n{exc}")
            return False

    def run(self) -> None:
        self.root.mainloop()
