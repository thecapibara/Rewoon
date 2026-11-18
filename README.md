# Rewoon - The Random Scare Generator

Ever wanted to add a little unexpected excitement to your streams, gaming, or coding sessions? **Rewoon** is a lightweight, cross-platform desktop app that runs in your system tray and triggers random audio and fullscreen video screamers at randomized intervals.

## Features

- **Audio & Fullscreen Video Screamers**: Supports `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a` audio and `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm` video (matched case-insensitively).
- **Native A/V Sync**: Uses `ffplay` (FFmpeg) or `mpv` for fullscreen, always-on-top video playback with synchronized audio, volume control, and instant `Esc`/`q` dismissal — no temporary `.mp3` extraction required.
- **System Tray Controls**: Non-blocking tray menu with **Show Window**, **Pause / Resume**, **Stop**, **Test Scare**, and **Exit**.
- **Built-in Media Library & Volume Control**: Inspect, add, remove, or rescan media files directly in the GUI, adjust volume (`0–100%`), and preview scares immediately with **Test Scare**.
- **Persistent Settings**: Saves timers, scare mode, volume, duration caps, and custom file paths in `config.ini`.
- **Isolated Virtual Environment**: `run.sh` and `run.bat` automatically create and manage a local `.venv` (PEP 668 compliant on modern Linux).

## Prerequisites

- **Python 3.10+** (with `tkinter` installed — on Fedora: `sudo dnf install python3-tkinter`, on Ubuntu/Debian: `sudo apt install python3-tk`, on Arch: `sudo pacman -S tk`).
- **FFmpeg (`ffplay`)** or **`mpv`** on your `PATH` for audio/video playback:
  - Fedora: `sudo dnf install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Arch: `sudo pacman -S ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` (or install `mpv`)

## Installation & Launch

```bash
git clone https://github.com/thecapibara/Rewoon.git
cd Rewoon
```

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

### Windows

Double-click **`run.bat`** or run it from PowerShell / Command Prompt.

### Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python rewoon.py
```

## How to Use

1. Drop audio files into `assets/` and/or video files into `videos/`, or click **Add Sounds** / **Add Videos** in the GUI.
2. Pick a **Scare Mode** (`All (Mixed)`, `Sound Only`, or `Video Only`).
3. Adjust **Min Delay** (`>= 10s`), **Max Delay** (`<= 1200s`, at least a `30s` gap), and **Volume** (`0–100%`).
4. Optionally click **Test Scare** to preview playback right away.
5. Click **Start Rewoon** — the app minimizes to the system tray and waits for the next randomized interval.
6. Right-click the tray icon at any time to **Show Window**, **Pause / Resume**, **Stop**, **Test Scare**, or **Exit**.

> Audio scares are capped at **30 seconds** and video scares at **5 seconds** by default (`max_sound_duration` / `max_video_duration` in `config.ini`). Press `Esc` or `q` to dismiss a fullscreen video early.

## Configuration (`config.ini`)

Settings are managed automatically from the UI, or can be edited manually:

```ini
[Settings]
min_delay = 10
max_delay = 600
scare_mode = all
volume = 100
max_sound_duration = 30
max_video_duration = 5
custom_sounds = []
custom_videos = []
```

## Project Structure

```text
Rewoon/
├── assets/                # Bundled audio files & icon.png
├── videos/                # Drop fullscreen video screamers here
├── tests/
│   └── test_rewoon.py     # Unit tests (unittest)
├── .gitignore
├── config.ini             # Persisted user settings
├── config.py              # Thread-safe AppConfig & media discovery
├── rewoon.py              # Application entry point
├── requirements.txt       # Python GUI & tray dependencies
├── run.sh                 # Linux/macOS .venv launcher
├── run.bat                # Windows .venv launcher
├── sound_player.py        # Audio playback backends & ScareScheduler
├── video_player.py        # Fullscreen video playback backends
└── ui.py                  # ttkbootstrap GUI & thread-safe pystray tray
```

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
