"""Fullscreen video screamer playback with native A/V sync and instant cancellation."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Sequence

logger = logging.getLogger(__name__)

_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def detect_video_backend() -> str | None:
    """Return the preferred installed CLI video backend ('ffplay' or 'mpv'), or None."""
    for name in ("ffplay", "mpv"):
        if shutil.which(name):
            return name
    return None


def build_video_command(
    video_path: str,
    max_duration: int = 5,
    volume: int = 100,
    backend: str | None = None,
) -> tuple[str, list[str]] | None:
    """Build a fullscreen, always-on-top CLI playback command with native audio sync."""
    chosen = backend or detect_video_backend()
    if chosen is None:
        return None

    exe = shutil.which(chosen)
    if not exe and backend is None:
        return None
    exe = exe or chosen

    vol = max(0, min(100, int(volume)))
    dur = max(1, int(max_duration))

    if chosen == "ffplay":
        return chosen, [
            exe,
            "-fs",
            "-alwaysontop",
            "-autoexit",
            "-loglevel",
            "quiet",
            "-volume",
            str(vol),
            "-t",
            str(dur),
            str(video_path),
        ]

    if chosen == "mpv":
        return chosen, [
            exe,
            "--fs",
            "--ontop",
            "--no-terminal",
            "--really-quiet",
            f"--volume={vol}",
            f"--end={dur}",
            str(video_path),
        ]

    raise ValueError(f"Unsupported video backend: {chosen!r}")


def run_cancellable_process(
    cmd: Sequence[str],
    timeout: float,
    stop_event: threading.Event | None = None,
    poll_interval: float = 0.05,
) -> bool:
    """Run a subprocess that terminates immediately on `timeout` or `stop_event`."""
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except OSError as exc:
        logger.error("Failed to launch media process %s: %s", cmd[0], exc)
        return False

    deadline = time.monotonic() + max(0.5, float(timeout))
    try:
        while proc.poll() is None:
            if stop_event is not None and stop_event.is_set():
                _terminate_process(proc)
                return False
            if time.monotonic() >= deadline:
                _terminate_process(proc)
                return True
            time.sleep(poll_interval)
        return True
    finally:
        if proc.poll() is None:
            _terminate_process(proc)


def _terminate_process(proc: subprocess.Popen) -> None:
    """Gracefully terminate a subprocess, escalating to kill if needed."""
    try:
        proc.terminate()
        proc.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=1.0)
        except OSError:
            pass
    except OSError:
        pass


def _play_video_opencv_fallback(
    video_path: str,
    max_duration: int = 5,
    stop_event: threading.Event | None = None,
) -> bool:
    """Fallback fullscreen video player using OpenCV if neither ffplay nor mpv is installed."""
    try:
        import cv2
    except ImportError:
        logger.error(
            "No video backend available. Install FFmpeg (ffplay), mpv, or opencv-python."
        )
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("OpenCV could not open video: %s", video_path)
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or fps > 120:
        fps = 30.0
    frame_duration = 1.0 / fps

    window_name = "RewoonScare"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    start_time = time.monotonic()
    deadline = start_time + max(1, int(max_duration))
    frame_idx = 0

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            if time.monotonic() >= deadline:
                break

            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            target_time = start_time + (frame_idx * frame_duration)
            remaining = target_time - time.monotonic()

            if remaining < -0.05:
                # Drop stale frame, but STILL pump GUI events so Esc / 'q' always work.
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                continue

            cv2.imshow(window_name, frame)
            if frame_idx == 1:
                try:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
                except cv2.error:
                    pass

            wait_ms = max(1, int(remaining * 1000)) if remaining > 0 else 1
            key = cv2.waitKey(wait_ms) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return True


def play_video_fullscreen(
    video_path: str,
    max_duration: int = 5,
    volume: int = 100,
    stop_event: threading.Event | None = None,
) -> bool:
    """Play a video fullscreen with synced audio, capped to `max_duration` seconds."""
    if not os.path.isfile(video_path):
        logger.warning("Video file not found: %s", video_path)
        return False

    built = build_video_command(video_path, max_duration=max_duration, volume=volume)
    if built is not None:
        backend, cmd = built
        logger.info("Playing video via %s: %s", backend, video_path)
        # Allow a brief startup margin beyond -t/--end before hard-killing
        return run_cancellable_process(cmd, timeout=max_duration + 3.0, stop_event=stop_event)

    logger.info("ffplay/mpv not found; falling back to OpenCV for %s", video_path)
    return _play_video_opencv_fallback(video_path, max_duration=max_duration, stop_event=stop_event)
