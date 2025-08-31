# -----------------------------
# File: sound_player.py
# -----------------------------
# Description: Handles the core logic of playing sounds randomly in a background thread.
# -----------------------------

import threading
import random
import time
from playsound import playsound
import config  # Import the shared configuration

def _random_sound_loop():
    """The main loop that plays the sound at random intervals. Meant to be run in a thread."""
    while config.is_running:
        try:
            # Choose a random delay based on the settings in config.py
            delay = random.randint(config.min_delay, config.max_delay)
            time.sleep(delay)

            # Check again if it's still running and a sound file is selected
            if config.is_running and config.sound_file_path:
                playsound(config.sound_file_path)
        except Exception as e:
            # Print errors to the console for debugging
            print(f"Error playing sound: {e}")

def start():
    """Starts the random sound player thread if it's not already running."""
    if not config.is_running and config.sound_file_path:
        config.is_running = True
        # Use a daemon thread so it automatically closes when the main app exits
        thread = threading.Thread(target=_random_sound_loop, daemon=True)
        thread.start()
        print("Sound player thread started.") # For debugging
        return True
    return False

def stop():
    """Stops the random sound player loop."""
    config.is_running = False
    print("Sound player thread stopped.") # For debugging
