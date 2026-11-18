"""Application configuration, media discovery, and thread-safe runtime state."""

from __future__ import annotations

import configparser
import json
import logging
import os
import threading
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# --- Paths (always resolved relative to this file, never CWD) ---
BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
VIDEOS_DIR: Path = BASE_DIR / "videos"
CONFIG_PATH: Path = BASE_DIR / "config.ini"
ICON_PATH: Path = ASSETS_DIR / "icon.png"

# --- Supported Media Extensions (matched case-insensitively) ---
AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".avi", ".mkv", ".mov", ".webm")

# --- Validation & Default Constants ---
VALID_MODES: tuple[str, ...] = ("all", "sound", "video")
DEFAULT_SCARE_MODE: str = "all"
DEFAULT_MIN_DELAY: int = 10
DEFAULT_MAX_DELAY: int = 600
MIN_ALLOWED_DELAY: int = 10
MAX_ALLOWED_DELAY: int = 1200
MIN_DELAY_GAP: int = 30
DEFAULT_VOLUME: int = 100
DEFAULT_MAX_SOUND_DURATION: int = 30
DEFAULT_MAX_VIDEO_DURATION: int = 5


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def discover_media_files(directory: Path, extensions: tuple[str, ...]) -> list[str]:
    """Return sorted absolute paths of files in `directory` matching `extensions` (case-insensitive)."""
    if not directory.is_dir():
        return []

    ext_set = {ext.lower() for ext in extensions}
    found: list[str] = []
    try:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_file() and entry.suffix.lower() in ext_set:
                found.append(str(entry.resolve()))
    except OSError as exc:
        logger.warning("Failed to scan directory %s: %s", directory, exc)
    return found


def validate_delays(min_delay: int, max_delay: int) -> tuple[bool, str | None]:
    """Validate user-supplied delay bounds strictly."""
    if min_delay < MIN_ALLOWED_DELAY:
        return False, f"Minimum delay cannot be less than {MIN_ALLOWED_DELAY} seconds."
    if max_delay > MAX_ALLOWED_DELAY:
        return False, f"Maximum delay cannot be greater than {MAX_ALLOWED_DELAY} seconds."
    if max_delay - min_delay < MIN_DELAY_GAP:
        return False, f"The gap between Min and Max must be at least {MIN_DELAY_GAP} seconds."
    return True, None


def normalize_delays(min_delay: int, max_delay: int) -> tuple[int, int]:
    """Clamp loaded delay values into a guaranteed-valid range with min_delay < max_delay."""
    min_d = max(MIN_ALLOWED_DELAY, min(min_delay, MAX_ALLOWED_DELAY - MIN_DELAY_GAP))
    max_d = max(min_d + MIN_DELAY_GAP, min(max_delay, MAX_ALLOWED_DELAY))
    if max_d > MAX_ALLOWED_DELAY:
        max_d = MAX_ALLOWED_DELAY
        min_d = max(MIN_ALLOWED_DELAY, max_d - MIN_DELAY_GAP)
    return min_d, max_d


def clamp_volume(volume: int) -> int:
    """Clamp volume percentage to [0, 100]."""
    return max(0, min(100, int(volume)))


class AppConfig:
    """Thread-safe holder for Rewoon configuration and loaded media lists."""

    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        assets_dir: Path = ASSETS_DIR,
        videos_dir: Path = VIDEOS_DIR,
    ) -> None:
        self._lock = threading.RLock()
        self.config_path: Path = Path(config_path)
        self.assets_dir: Path = Path(assets_dir)
        self.videos_dir: Path = Path(videos_dir)

        self.sound_file_paths: list[str] = []
        self.video_file_paths: list[str] = []
        self._custom_sound_paths: list[str] = []
        self._custom_video_paths: list[str] = []

        self.scare_mode: str = DEFAULT_SCARE_MODE
        self.min_delay: int = DEFAULT_MIN_DELAY
        self.max_delay: int = DEFAULT_MAX_DELAY
        self.volume: int = DEFAULT_VOLUME
        self.max_sound_duration: int = DEFAULT_MAX_SOUND_DURATION
        self.max_video_duration: int = DEFAULT_MAX_VIDEO_DURATION

        self.is_running: bool = False
        self.is_paused: bool = False

    def initialize(self) -> None:
        """Load persisted settings and discover bundled/user media files."""
        self.load_settings()
        self.rescan_media()

    def rescan_media(self) -> None:
        """Discover sounds in assets/ and videos in videos/ (never mixing video audio into sounds)."""
        bundled_sounds = discover_media_files(self.assets_dir, AUDIO_EXTENSIONS)
        bundled_videos = discover_media_files(self.videos_dir, VIDEO_EXTENSIONS)

        with self._lock:
            self.sound_file_paths = self._merge_unique_existing(
                bundled_sounds, self._custom_sound_paths
            )
            self.video_file_paths = self._merge_unique_existing(
                bundled_videos, self._custom_video_paths
            )

    @staticmethod
    def _merge_unique_existing(*groups: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for raw_path in group:
                abs_path = os.path.abspath(raw_path)
                if abs_path not in seen and os.path.isfile(abs_path):
                    seen.add(abs_path)
                    result.append(abs_path)
        return result

    def add_sounds(self, paths: Iterable[str]) -> int:
        """Add sound file paths, returning how many new files were added."""
        added = 0
        with self._lock:
            seen = {os.path.abspath(p) for p in self.sound_file_paths}
            for raw in paths:
                abs_p = os.path.abspath(raw)
                if abs_p not in seen and os.path.isfile(abs_p):
                    self.sound_file_paths.append(abs_p)
                    if abs_p not in self._custom_sound_paths:
                        self._custom_sound_paths.append(abs_p)
                    seen.add(abs_p)
                    added += 1
        return added

    def add_videos(self, paths: Iterable[str]) -> int:
        """Add video file paths, returning how many new files were added."""
        added = 0
        with self._lock:
            seen = {os.path.abspath(p) for p in self.video_file_paths}
            for raw in paths:
                abs_p = os.path.abspath(raw)
                if abs_p not in seen and os.path.isfile(abs_p):
                    self.video_file_paths.append(abs_p)
                    if abs_p not in self._custom_video_paths:
                        self._custom_video_paths.append(abs_p)
                    seen.add(abs_p)
                    added += 1
        return added

    def remove_sound(self, path: str) -> bool:
        """Remove a sound file from the active session list."""
        abs_p = os.path.abspath(path)
        with self._lock:
            before = len(self.sound_file_paths)
            self.sound_file_paths = [p for p in self.sound_file_paths if os.path.abspath(p) != abs_p]
            self._custom_sound_paths = [p for p in self._custom_sound_paths if os.path.abspath(p) != abs_p]
            return len(self.sound_file_paths) < before

    def remove_video(self, path: str) -> bool:
        """Remove a video file from the active session list."""
        abs_p = os.path.abspath(path)
        with self._lock:
            before = len(self.video_file_paths)
            self.video_file_paths = [p for p in self.video_file_paths if os.path.abspath(p) != abs_p]
            self._custom_video_paths = [p for p in self._custom_video_paths if os.path.abspath(p) != abs_p]
            return len(self.video_file_paths) < before

    def set_mode(self, mode: str) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported scare mode: {mode!r}")
        with self._lock:
            self.scare_mode = mode

    def set_volume(self, volume: int) -> None:
        with self._lock:
            self.volume = clamp_volume(volume)

    def set_delays(self, min_delay: int, max_delay: int) -> None:
        ok, err = validate_delays(min_delay, max_delay)
        if not ok:
            raise ValueError(err)
        with self._lock:
            self.min_delay = min_delay
            self.max_delay = max_delay

    def can_start(self) -> bool:
        """Return True if there is at least one playable file for the selected mode."""
        with self._lock:
            if self.scare_mode == "sound":
                return bool(self.sound_file_paths)
            if self.scare_mode == "video":
                return bool(self.video_file_paths)
            return bool(self.sound_file_paths or self.video_file_paths)

    def snapshot(self) -> dict:
        """Return a thread-safe copy of playback-relevant state."""
        with self._lock:
            return {
                "scare_mode": self.scare_mode,
                "min_delay": self.min_delay,
                "max_delay": self.max_delay,
                "volume": self.volume,
                "max_sound_duration": self.max_sound_duration,
                "max_video_duration": self.max_video_duration,
                "sound_file_paths": list(self.sound_file_paths),
                "video_file_paths": list(self.video_file_paths),
            }

    def load_settings(self) -> None:
        """Load persisted settings from config.ini with safe fallback & normalization."""
        parser = configparser.ConfigParser()
        try:
            read_files = parser.read(self.config_path, encoding="utf-8")
            if not read_files or "Settings" not in parser:
                return

            settings = parser["Settings"]
            raw_min = settings.getint("min_delay", fallback=DEFAULT_MIN_DELAY)
            raw_max = settings.getint("max_delay", fallback=DEFAULT_MAX_DELAY)
            norm_min, norm_max = normalize_delays(raw_min, raw_max)
            if (norm_min, norm_max) != (raw_min, raw_max):
                logger.warning(
                    "Normalized invalid delays from config.ini (%s, %s) -> (%s, %s)",
                    raw_min,
                    raw_max,
                    norm_min,
                    norm_max,
                )

            raw_mode = settings.get("scare_mode", fallback=DEFAULT_SCARE_MODE).strip().lower()
            mode = raw_mode if raw_mode in VALID_MODES else DEFAULT_SCARE_MODE

            volume = clamp_volume(settings.getint("volume", fallback=DEFAULT_VOLUME))
            max_sound = max(1, settings.getint("max_sound_duration", fallback=DEFAULT_MAX_SOUND_DURATION))
            max_video = max(1, settings.getint("max_video_duration", fallback=DEFAULT_MAX_VIDEO_DURATION))

            custom_sounds = self._parse_json_list(settings.get("custom_sounds", fallback="[]"))
            custom_videos = self._parse_json_list(settings.get("custom_videos", fallback="[]"))

            with self._lock:
                self.min_delay = norm_min
                self.max_delay = norm_max
                self.scare_mode = mode
                self.volume = volume
                self.max_sound_duration = max_sound
                self.max_video_duration = max_video
                self._custom_sound_paths = custom_sounds
                self._custom_video_paths = custom_videos

            logger.info("Loaded settings from %s", self.config_path)
        except Exception as exc:
            logger.warning("Could not load %s (%s); using defaults.", self.config_path, exc)

    def save_settings(self) -> None:
        """Persist current settings to config.ini."""
        parser = configparser.ConfigParser()
        with self._lock:
            parser["Settings"] = {
                "min_delay": str(self.min_delay),
                "max_delay": str(self.max_delay),
                "scare_mode": self.scare_mode,
                "volume": str(self.volume),
                "max_sound_duration": str(self.max_sound_duration),
                "max_video_duration": str(self.max_video_duration),
                "custom_sounds": json.dumps(self._custom_sound_paths),
                "custom_videos": json.dumps(self._custom_video_paths),
            }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            parser.write(fh)
        logger.info("Saved settings to %s", self.config_path)

    @staticmethod
    def _parse_json_list(raw: str) -> list[str]:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(item) for item in data if isinstance(item, str)]
        except json.JSONDecodeError:
            pass
        return []


# Shared application state instance (no I/O happens until initialize() is called)
state = AppConfig()


def initialize() -> AppConfig:
    """Initialize and return the shared application configuration."""
    state.initialize()
    return state
