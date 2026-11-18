"""Audio playback backends and background random-scare scheduler."""

from __future__ import annotations

import logging
import os
import random
import shutil
import sys
import threading
import time
from typing import Callable

import config
import video_player

logger = logging.getLogger(__name__)


def detect_audio_backend() -> str | None:
    """Return the preferred installed CLI audio backend, or None."""
    candidates = ["ffplay", "mpv"]
    if sys.platform == "darwin":
        candidates.append("afplay")
    elif sys.platform.startswith("linux"):
        candidates.append("paplay")

    for name in candidates:
        if shutil.which(name):
            return name
    return None


def build_audio_command(
    audio_path: str,
    max_duration: int = 30,
    volume: int = 100,
    backend: str | None = None,
) -> tuple[str, list[str]] | None:
    """Build a CLI audio playback command with volume and duration limits."""
    chosen = backend or detect_audio_backend()
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
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
            "-volume",
            str(vol),
            "-t",
            str(dur),
            str(audio_path),
        ]

    if chosen == "mpv":
        return chosen, [
            exe,
            "--no-video",
            "--no-terminal",
            "--really-quiet",
            f"--volume={vol}",
            f"--end={dur}",
            str(audio_path),
        ]

    if chosen == "afplay":
        return chosen, [
            exe,
            "-v",
            f"{vol / 100:.2f}",
            "-t",
            str(dur),
            str(audio_path),
        ]

    if chosen == "paplay":
        pa_vol = int(round((vol / 100.0) * 65536))
        return chosen, [exe, f"--volume={pa_vol}", str(audio_path)]

    raise ValueError(f"Unsupported audio backend: {chosen!r}")


def _play_audio_pygame(
    audio_path: str,
    max_duration: int,
    volume: int,
    stop_event: threading.Event | None,
) -> bool:
    """Fallback audio player using pygame / pygame-ce if installed."""
    try:
        import pygame.mixer as mixer
    except ImportError:
        return False

    try:
        if not mixer.get_init():
            mixer.init()
        mixer.music.load(audio_path)
        mixer.music.set_volume(max(0.0, min(1.0, volume / 100.0)))
        mixer.music.play()

        deadline = time.monotonic() + max(1, int(max_duration))
        while mixer.music.get_busy():
            if stop_event is not None and stop_event.is_set():
                mixer.music.stop()
                return False
            if time.monotonic() >= deadline:
                mixer.music.stop()
                return True
            time.sleep(0.05)
        return True
    except Exception as exc:
        logger.error("pygame audio playback failed for %s: %s", audio_path, exc)
        return False


def play_audio(
    audio_path: str,
    max_duration: int = 30,
    volume: int = 100,
    stop_event: threading.Event | None = None,
) -> bool:
    """Play an audio file with volume control, duration cap, and instant cancellation."""
    if not os.path.isfile(audio_path):
        logger.warning("Audio file not found: %s", audio_path)
        return False

    built = build_audio_command(audio_path, max_duration=max_duration, volume=volume)
    if built is not None:
        backend, cmd = built
        logger.info("Playing audio via %s: %s", backend, audio_path)
        return video_player.run_cancellable_process(
            cmd, timeout=max_duration + 2.0, stop_event=stop_event
        )

    if _play_audio_pygame(audio_path, max_duration=max_duration, volume=volume, stop_event=stop_event):
        return True

    if sys.platform == "win32" and audio_path.lower().endswith(".wav"):
        try:
            import winsound

            winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            deadline = time.monotonic() + max(1, int(max_duration))
            while time.monotonic() < deadline:
                if stop_event is not None and stop_event.is_set():
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    return False
                time.sleep(0.1)
            winsound.PlaySound(None, winsound.SND_PURGE)
            return True
        except Exception as exc:
            logger.error("winsound playback failed: %s", exc)

    logger.error(
        "No audio backend available. Install FFmpeg (ffplay), mpv, or pygame-ce."
    )
    return False


class ScareScheduler:
    """Manages the background random-scare loop with instant stop, pause, and test triggers."""

    def __init__(
        self,
        app_config: config.AppConfig,
        audio_fn: Callable[..., bool] = play_audio,
        video_fn: Callable[..., bool] = video_player.play_video_fullscreen,
        on_status_change: Callable[[str], None] | None = None,
    ) -> None:
        self._config = app_config
        self._audio_fn = audio_fn
        self._video_fn = video_fn
        self._on_status_change = on_status_change

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._thread: threading.Thread | None = None
        self._test_stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._config.is_running

    @property
    def is_paused(self) -> bool:
        return self._config.is_paused

    @staticmethod
    def choose_scare(snap: dict) -> tuple[str, str] | None:
        """Select ('sound', path) or ('video', path) according to current mode and files."""
        mode = snap["scare_mode"]
        sounds = snap["sound_file_paths"]
        videos = snap["video_file_paths"]

        if mode == "sound":
            return ("sound", random.choice(sounds)) if sounds else None
        if mode == "video":
            return ("video", random.choice(videos)) if videos else None

        choices: list[str] = []
        if sounds:
            choices.append("sound")
        if videos:
            choices.append("video")
        if not choices:
            return None

        picked = random.choice(choices)
        if picked == "sound":
            return ("sound", random.choice(sounds))
        return ("video", random.choice(videos))

    def start(self) -> bool:
        """Start the background scare loop if not already running and media is available."""
        with self._lock:
            if self._config.is_running and self._thread and self._thread.is_alive():
                return False
            if not self._config.can_start():
                return False

            self._stop_event.clear()
            self._resume_event.set()
            self._config.is_running = True
            self._config.is_paused = False

            self._thread = threading.Thread(
                target=self._scare_loop, name="RewoonScareLoop", daemon=True
            )
            self._thread.start()
            logger.info("Scare loop started in '%s' mode.", self._config.scare_mode)
            self._notify("running")
            return True

    def stop(self, join_timeout: float = 2.0) -> None:
        """Stop the background scare loop and cancel any active playback immediately."""
        with self._lock:
            self._config.is_running = False
            self._config.is_paused = False
            self._stop_event.set()
            self._test_stop_event.set()
            self._resume_event.set()
            thread = self._thread

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=join_timeout)

        with self._lock:
            if self._thread is thread:
                self._thread = None

        logger.info("Scare loop stopped.")
        self._notify("stopped")

    def pause(self) -> bool:
        """Pause the countdown timer without exiting the background thread."""
        with self._lock:
            if not self._config.is_running or self._config.is_paused:
                return False
            self._config.is_paused = True
            self._resume_event.clear()
        logger.info("Scare loop paused.")
        self._notify("paused")
        return True

    def resume(self) -> bool:
        """Resume a paused scare loop."""
        with self._lock:
            if not self._config.is_running or not self._config.is_paused:
                return False
            self._config.is_paused = False
            self._resume_event.set()
        logger.info("Scare loop resumed.")
        self._notify("running")
        return True

    def trigger_test_scare(self, on_done: Callable[[bool], None] | None = None) -> bool:
        """Immediately play one random scare in a background thread for testing."""
        snap = self._config.snapshot()
        choice = self.choose_scare(snap)
        if choice is None:
            return False

        self._test_stop_event.clear()

        def _worker() -> None:
            ok = self._execute_scare(choice, snap, self._test_stop_event)
            if on_done is not None:
                try:
                    on_done(ok)
                except Exception:
                    pass

        threading.Thread(target=_worker, name="RewoonTestScare", daemon=True).start()
        return True

    def _wait_interruptible(self, seconds: float) -> bool:
        """Wait `seconds`, honoring pause and stop events. Returns False if stopped."""
        remaining = max(0.0, float(seconds))
        step = 0.2
        while remaining > 0:
            if self._stop_event.is_set():
                return False
            if not self._resume_event.is_set():
                # Block efficiently until resumed or stopped
                while not self._resume_event.is_set() and not self._stop_event.is_set():
                    self._resume_event.wait(timeout=step)
                continue

            chunk = min(step, remaining)
            if self._stop_event.wait(timeout=chunk):
                return False
            remaining -= chunk
        return not self._stop_event.is_set()

    def _execute_scare(
        self,
        choice: tuple[str, str],
        snap: dict,
        stop_event: threading.Event,
    ) -> bool:
        kind, path = choice
        if kind == "sound":
            return self._audio_fn(
                path,
                max_duration=snap["max_sound_duration"],
                volume=snap["volume"],
                stop_event=stop_event,
            )
        return self._video_fn(
            path,
            max_duration=snap["max_video_duration"],
            volume=snap["volume"],
            stop_event=stop_event,
        )

    def _scare_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snap = self._config.snapshot()
                min_d = snap["min_delay"]
                max_d = max(min_d, snap["max_delay"])
                delay = random.randint(min_d, max_d)
                logger.debug("Next scare scheduled in %ss", delay)

                if not self._wait_interruptible(delay):
                    break

                # Re-read snapshot in case user edited mode/volume/files while waiting
                snap = self._config.snapshot()
                choice = self.choose_scare(snap)
                if choice is None:
                    logger.warning("No playable media available for mode '%s'.", snap["scare_mode"])
                    if self._stop_event.wait(timeout=2.0):
                        break
                    continue

                self._execute_scare(choice, snap, self._stop_event)
            except Exception as exc:
                logger.exception("Unexpected error in scare loop: %s", exc)
                # Backoff prevents 100% CPU spin on persistent errors
                if self._stop_event.wait(timeout=1.0):
                    break

    def _notify(self, status: str) -> None:
        if self._on_status_change is not None:
            try:
                self._on_status_change(status)
            except Exception:
                pass


# Module-level default scheduler
scheduler = ScareScheduler(config.state)


def start() -> bool:
    return scheduler.start()


def stop() -> None:
    scheduler.stop()


def pause() -> bool:
    return scheduler.pause()


def resume() -> bool:
    return scheduler.resume()


def trigger_test_scare(on_done: Callable[[bool], None] | None = None) -> bool:
    return scheduler.trigger_test_scare(on_done=on_done)
