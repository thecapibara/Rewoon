# -----------------------------
# File: sound_player.py
# -----------------------------
# Description: Handles the core logic of playing sounds randomly in a background thread.
# -----------------------------

import threading
import random
import time
from playsound import playsound
import config

def _random_sound_loop():
    while config.is_running:
        try:
            delay = random.randint(config.min_delay, config.max_delay)
            time.sleep(delay)

            # --- CHANGED: Logic to handle a list of sounds ---
            if config.is_running and config.sound_file_paths:
                # Randomly choose one sound from the list
                selected_sound = random.choice(config.sound_file_paths)
                playsound(selected_sound)
                # ----------------------------------------------------

        except Exception as e:
            print(f"Error playing sound: {e}")

def start():
    # --- CHANGED: Check the list instead of the single path ---
    if not config.is_running and config.sound_file_paths:
        config.is_running = True
        thread = threading.Thread(target=_random_sound_loop, daemon=True)
        thread.start()
        print("Sound player thread started.")
        return True
    return False

def stop():
    config.is_running = False
    print("Sound player thread stopped.")
