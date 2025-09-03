# -----------------------------
# File: config.py
# -----------------------------
# Description: Holds global state and loads user settings from config.ini.
# -----------------------------

import configparser

# --- Application State ---
# --- CHANGED: Now a list to hold multiple sound files ---
sound_file_paths = []
is_running = False

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
