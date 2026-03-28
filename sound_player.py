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
import video_player
import multiprocessing

def _play_audio_process(path):
    from playsound import playsound
    try:
        playsound(path)
    except Exception:
        pass

def _random_scare_loop():
    while config.is_running:
        try:
            delay = random.randint(config.min_delay, config.max_delay)
            time.sleep(delay)

            if not config.is_running:
                break # Exit if stopped during sleep

            # --- Determine which scare to play based on mode ---
            play_type = None
            s_count = len(config.sound_file_paths)
            v_count = len(config.video_file_paths)

            if config.scare_mode == "sound" and s_count > 0:
                play_type = "sound"
            elif config.scare_mode == "video" and v_count > 0:
                play_type = "video"
            elif config.scare_mode == "all":
                choices = []
                if s_count > 0: choices.append("sound")
                if v_count > 0: choices.append("video")
                if choices:
                    play_type = random.choice(choices)

            # --- Execute Scare ---
            if play_type == "sound":
                selected_sound = random.choice(config.sound_file_paths)
                print(f"Playing sound: {selected_sound}")
                
                p = multiprocessing.Process(target=_play_audio_process, args=(selected_sound,))
                p.start()
                # Block the loop and enforce a 30 second limit
                p.join(timeout=30)
                if p.is_alive():
                    p.terminate()
                    p.join()
            elif play_type == "video":
                selected_video = random.choice(config.video_file_paths)
                print(f"Playing video: {selected_video}")
                video_player.play_video_fullscreen(selected_video, max_duration=5)

        except Exception as e:
            print(f"Error playing sound: {e}")

def start():
    # Only start if we have files for the selected mode
    can_start = False
    if config.scare_mode == "sound" and config.sound_file_paths:
        can_start = True
    elif config.scare_mode == "video" and config.video_file_paths:
        can_start = True
    elif config.scare_mode == "all" and (config.sound_file_paths or config.video_file_paths):
        can_start = True

    if not config.is_running and can_start:
        config.is_running = True
        thread = threading.Thread(target=_random_scare_loop, daemon=True)
        thread.start()
        print(f"Scare loop started in '{config.scare_mode}' mode.")
        return True
    return False

def stop():
    config.is_running = False
    print("Scare loop stopped.")
