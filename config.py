# -----------------------------
# File: config.py
# -----------------------------
# Description: Holds global state and loads user settings from config.ini.
# -----------------------------

import configparser

# --- Application State ---
sound_file_path = ""  # Path to the user-selected sound file
is_running = False    # Flag to check if the sound playing loop is active

# --- User-configurable Settings (DEFAULTS) ---
# These values will be used if config.ini is missing or has errors.
min_delay = 10
max_delay = 600

# --- CONFIGURATION LOADING LOGIC ---
# This code will now read from config.ini and overwrite the defaults.
config_parser = configparser.ConfigParser()

try:
    # Attempt to read the user's configuration file
    if config_parser.read('config.ini') and 'Settings' in config_parser:
        settings = config_parser['Settings']
        
        # Get values, falling back to the default if a specific setting is missing
        # The .getint() method safely converts the text value to an integer
        min_delay = settings.getint('min_delay', fallback=min_delay)
        max_delay = settings.getint('max_delay', fallback=max_delay)
        
        print("Successfully loaded settings from config.ini")

except Exception as e:
    # If anything goes wrong (file not found, bad format), use the defaults
    print(f"Could not load config.ini: {e}. Using default settings.")


# --- Final check to ensure logic is sound ---
if min_delay >= max_delay:
    print(f"Warning: min_delay ({min_delay}) is greater than or equal to max_delay ({max_delay}). Fixing.")
    min_delay = max_delay - 1
if min_delay < 1:
    min_delay = 1 # Prevent zero or negative delays
