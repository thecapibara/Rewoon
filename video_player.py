# -----------------------------
# File: video_player.py
# -----------------------------
# Description: Handles fullscreen video playback with "Always on Top" functionality.
# -----------------------------

import cv2
import time
import platform
import os
import sys
import subprocess
import threading

def _bring_to_front(window_name):
    """Attempt to bring the window to the front depending on the OS."""
    try:
        current_os = platform.system()
        if current_os == "Windows":
            import win32gui
            import win32con
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception as e:
        pass

def play_video_sync(video_path):
    """
    Plays a video in a fullscreen, topmost window.
    Runs synchronously in the current process.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return

    # Set cross-platform env var to avoid Wayland crashes
    os.environ['QT_QPA_PLATFORM'] = 'xcb'

    window_name = "RewoonScreamer"
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cv2.destroyWindow(window_name)
        return

    # Attempt to force the window to the front after a slight delay
    threading.Timer(0.1, _bring_to_front, args=[window_name]).start()

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps != fps: 
        fps = 30.0
    
    # Get screen resolution
    screen_width, screen_height = 1920, 1080 
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except Exception:
        pass

    # Look for a matching audio file (.mp3 or .wav) to play instead of the video file
    audio_path = None
    base_path = os.path.splitext(video_path)[0]
    if os.path.exists(base_path + ".mp3"):
        audio_path = base_path + ".mp3"
    elif os.path.exists(base_path + ".wav"):
        audio_path = base_path + ".wav"

        try:
            from playsound import playsound
            audio_thread = threading.Thread(target=playsound, args=(audio_path,), daemon=True)
            audio_thread.start()
            # Give the system media player a fraction of a second to actually start playing
            time.sleep(0.25)
        except Exception as e:
            print(f"Failed to play paired audio: {e}")
    else:
        print(f"Notice: No paired .mp3 or .wav found for {video_path}")

    start_time = time.time()
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break 
        
        try:
            frame = cv2.resize(frame, (screen_width, screen_height), interpolation=cv2.INTER_LINEAR)
        except Exception:
            pass

        frame_count += 1
        expected_time = frame_count / fps
        actual_time = time.time() - start_time
        sleep_time = expected_time - actual_time

        if sleep_time > 0:
            time.sleep(sleep_time)
        elif sleep_time < -0.03:
            # We are lagging behind the audio/time (more than 30ms).
            # Drop the imshow for this frame to catch up visually.
            continue
        
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break 

    cap.release()
    cv2.destroyWindow(window_name)
    for _ in range(4):
        cv2.waitKey(1)

def play_video_fullscreen(video_path, max_duration=5):
    """
    Starts the video playback in a SUBPROCESS to avoid GUI thread crashes.
    Uses a strict timeout limit to enforce video length and prevent overlap.
    """
    try:
        subprocess.run([sys.executable, __file__, video_path], timeout=max_duration)
    except subprocess.TimeoutExpired:
        pass # Expected if the video is longer than max_duration

if __name__ == "__main__":
    if len(sys.argv) > 1:
        play_video_sync(sys.argv[1])
    else:
        print("Usage: python video_player.py <path_to_video>")
