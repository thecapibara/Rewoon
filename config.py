# -----------------------------
# File: config.py
# -----------------------------
# Description: Holds global state and loads user settings from config.ini.
# -----------------------------

import configparser
import os
import glob

# --- Application State ---
sound_file_paths = []
video_file_paths = []
scare_mode = "all" # Options: 'all', 'sound', 'video'
is_running = False

# Auto-load files from predetermined folders
for ext in ('*.mp3', '*.wav'):
    sound_file_paths.extend(glob.glob(os.path.join("assets", ext)))
    sound_file_paths.extend(glob.glob(os.path.join("videos", ext)))
for ext in ('*.mp4', '*.avi', '*.mkv', '*.mov'):
    video_file_paths.extend(glob.glob(os.path.join("videos", ext)))

# --- NEW: Auto-extract missing audio for videos ---
moviepy_imported = False
for video_path in video_file_paths:
    base_path = os.path.splitext(video_path)[0]
    expected_audio = base_path + ".mp3"
    if not os.path.exists(expected_audio) and not os.path.exists(base_path + ".wav"):
        print(f"Extracting missing audio for: {video_path}")
        try:
            if not moviepy_imported:
                from moviepy import VideoFileClip
                moviepy_imported = True
                
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                # write_audiofile is noisy, we can silence it with logger=None
                clip.audio.write_audiofile(expected_audio, logger=None)
                sound_file_paths.append(expected_audio) # Add to list so it is instantly available
            clip.close()
            print(f"Successfully extracted: {expected_audio}")
        except Exception as e:
            print(f"Failed to extract audio from {video_path}: {e}")


# --- User-configurable Settings (DEFAULTS) ---
min_delay = 10
max_delay = 600

# --- CONFIGURATION LOADING LOGIC ---
config_parser = configparser.ConfigParser()
try:
    if config_parser.read('config.ini') and 'Settings' in config_parser:
        settings = config_parser['Settings']
        min_delay = settings.getint('min_delay', fallback=min_delay)
        max_delay = settings.getint('max_delay', fallback=max_delay)
        print("Successfully loaded settings from config.ini")
except Exception as e:
    print(f"Could not load config.ini: {e}. Using default settings.")

if min_delay >= max_delay:
    print(f"Warning: min_delay ({min_delay}) is >= max_delay ({max_delay}). Fixing.")
    min_delay = max_delay - 1
if min_delay < 1:
    min_delay = 1
