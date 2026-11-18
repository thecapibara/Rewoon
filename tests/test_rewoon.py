"""Unit tests for Rewoon configuration, media command builders, and scare scheduler."""

from __future__ import annotations

import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import config
import sound_player
import video_player


class TestConfig(unittest.TestCase):
    def test_normalize_delays_handles_negative_and_inverted_values(self) -> None:
        # Regression: previously max_delay=0 produced min_delay=1 > max_delay=0 -> ValueError loop
        min_d, max_d = config.normalize_delays(10, 0)
        self.assertGreaterEqual(min_d, config.MIN_ALLOWED_DELAY)
        self.assertLessEqual(max_d, config.MAX_ALLOWED_DELAY)
        self.assertGreaterEqual(max_d - min_d, config.MIN_DELAY_GAP)

        min_d, max_d = config.normalize_delays(9999, -50)
        self.assertLess(min_d, max_d)
        self.assertGreaterEqual(max_d - min_d, config.MIN_DELAY_GAP)

    def test_validate_delays_rules(self) -> None:
        self.assertEqual(config.validate_delays(10, 40), (True, None))
        self.assertFalse(config.validate_delays(9, 40)[0])
        self.assertFalse(config.validate_delays(10, 1201)[0])
        self.assertFalse(config.validate_delays(10, 39)[0])

    def test_case_insensitive_discovery_and_video_audio_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            videos = root / "videos"
            assets.mkdir()
            videos.mkdir()

            (assets / "scare.MP3").write_bytes(b"mp3")
            (assets / "boom.wav").write_bytes(b"wav")
            (assets / "ignore.txt").write_text("nope", encoding="utf-8")

            # Audio placed in videos/ must NOT pollute sound_file_paths
            (videos / "clip.MP4").write_bytes(b"mp4")
            (videos / "clip.mp3").write_bytes(b"extracted")

            cfg = config.AppConfig(
                config_path=root / "config.ini",
                assets_dir=assets,
                videos_dir=videos,
            )
            cfg.initialize()

            sound_names = {Path(p).name for p in cfg.sound_file_paths}
            video_names = {Path(p).name for p in cfg.video_file_paths}

            self.assertEqual(sound_names, {"scare.MP3", "boom.wav"})
            self.assertEqual(video_names, {"clip.MP4"})

    def test_settings_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            videos = root / "videos"
            assets.mkdir()
            videos.mkdir()
            custom_sound = root / "custom.ogg"
            custom_sound.write_bytes(b"ogg")

            cfg_path = root / "config.ini"
            cfg = config.AppConfig(config_path=cfg_path, assets_dir=assets, videos_dir=videos)
            cfg.set_delays(25, 120)
            cfg.set_mode("sound")
            cfg.set_volume(65)
            cfg.add_sounds([str(custom_sound)])
            cfg.save_settings()

            reloaded = config.AppConfig(config_path=cfg_path, assets_dir=assets, videos_dir=videos)
            reloaded.initialize()

            self.assertEqual(reloaded.min_delay, 25)
            self.assertEqual(reloaded.max_delay, 120)
            self.assertEqual(reloaded.scare_mode, "sound")
            self.assertEqual(reloaded.volume, 65)
            self.assertIn(str(custom_sound.resolve()), reloaded.sound_file_paths)

    def test_can_start_all_mode_with_only_sounds_or_only_videos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            videos = root / "videos"
            assets.mkdir()
            videos.mkdir()
            (assets / "only_sound.mp3").write_bytes(b"mp3")

            cfg = config.AppConfig(config_path=root / "config.ini", assets_dir=assets, videos_dir=videos)
            cfg.initialize()
            cfg.set_mode("all")
            self.assertTrue(cfg.can_start())

            cfg.set_mode("video")
            self.assertFalse(cfg.can_start())


class TestMediaCommands(unittest.TestCase):
    def test_build_video_command_ffplay_and_mpv(self) -> None:
        backend, cmd = video_player.build_video_command(
            "/tmp/clip.mp4", max_duration=7, volume=80, backend="ffplay"
        )
        self.assertEqual(backend, "ffplay")
        self.assertIn("-fs", cmd)
        self.assertIn("-alwaysontop", cmd)
        self.assertIn("-autoexit", cmd)
        self.assertIn("-volume", cmd)
        self.assertIn("80", cmd)
        self.assertIn("-t", cmd)
        self.assertIn("7", cmd)

        backend2, cmd2 = video_player.build_video_command(
            "/tmp/clip.mp4", max_duration=5, volume=50, backend="mpv"
        )
        self.assertEqual(backend2, "mpv")
        self.assertIn("--fs", cmd2)
        self.assertIn("--ontop", cmd2)
        self.assertIn("--volume=50", cmd2)
        self.assertIn("--end=5", cmd2)

    def test_build_audio_command_ffplay_and_mpv(self) -> None:
        backend, cmd = sound_player.build_audio_command(
            "/tmp/scare.mp3", max_duration=30, volume=45, backend="ffplay"
        )
        self.assertEqual(backend, "ffplay")
        self.assertIn("-nodisp", cmd)
        self.assertIn("-volume", cmd)
        self.assertIn("45", cmd)
        self.assertIn("-t", cmd)
        self.assertIn("30", cmd)

        backend2, cmd2 = sound_player.build_audio_command(
            "/tmp/scare.mp3", max_duration=15, volume=90, backend="mpv"
        )
        self.assertEqual(backend2, "mpv")
        self.assertIn("--no-video", cmd2)
        self.assertIn("--volume=90", cmd2)
        self.assertIn("--end=15", cmd2)

    def test_run_cancellable_process_stops_immediately(self) -> None:
        stop_event = threading.Event()
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]

        def _trigger_stop() -> None:
            time.sleep(0.15)
            stop_event.set()

        t = threading.Thread(target=_trigger_stop, daemon=True)
        t.start()

        start = time.monotonic()
        completed = video_player.run_cancellable_process(cmd, timeout=10.0, stop_event=stop_event)
        elapsed = time.monotonic() - start

        self.assertFalse(completed)
        self.assertLess(elapsed, 2.0)


class TestScareScheduler(unittest.TestCase):
    def _make_config(self, tmp: str) -> config.AppConfig:
        root = Path(tmp)
        assets = root / "assets"
        videos = root / "videos"
        assets.mkdir()
        videos.mkdir()
        (assets / "a.mp3").write_bytes(b"mp3")
        (videos / "v.mp4").write_bytes(b"mp4")
        cfg = config.AppConfig(config_path=root / "config.ini", assets_dir=assets, videos_dir=videos)
        cfg.initialize()
        return cfg

    def test_choose_scare_respects_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_config(tmp)
            cfg.set_mode("sound")
            choice = sound_player.ScareScheduler.choose_scare(cfg.snapshot())
            self.assertIsNotNone(choice)
            self.assertEqual(choice[0], "sound")

            cfg.set_mode("video")
            choice = sound_player.ScareScheduler.choose_scare(cfg.snapshot())
            self.assertIsNotNone(choice)
            self.assertEqual(choice[0], "video")

    def test_start_pause_resume_and_instant_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_config(tmp)
            # Large delay to prove stop() interrupts immediately instead of sleeping
            cfg.set_delays(100, 200)
            played: list[str] = []

            scheduler = sound_player.ScareScheduler(
                cfg,
                audio_fn=lambda path, **kw: played.append(path) or True,
                video_fn=lambda path, **kw: played.append(path) or True,
            )

            self.assertTrue(scheduler.start())
            self.assertFalse(scheduler.start())  # Duplicate start blocked
            self.assertTrue(scheduler.is_running)

            self.assertTrue(scheduler.pause())
            self.assertTrue(scheduler.is_paused)
            self.assertTrue(scheduler.resume())
            self.assertFalse(scheduler.is_paused)

            start = time.monotonic()
            scheduler.stop(join_timeout=2.0)
            elapsed = time.monotonic() - start

            self.assertFalse(scheduler.is_running)
            self.assertLess(elapsed, 1.5)

    def test_trigger_test_scare_executes_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_config(tmp)
            cfg.set_mode("sound")
            done_event = threading.Event()
            played: list[tuple[str, int]] = []

            def fake_audio(path: str, max_duration: int, volume: int, stop_event=None) -> bool:
                played.append((path, volume))
                return True

            cfg.set_volume(77)
            scheduler = sound_player.ScareScheduler(cfg, audio_fn=fake_audio)
            ok = scheduler.trigger_test_scare(on_done=lambda _res: done_event.set())

            self.assertTrue(ok)
            self.assertTrue(done_event.wait(timeout=2.0))
            self.assertEqual(len(played), 1)
            self.assertEqual(played[0][1], 77)


if __name__ == "__main__":
    unittest.main()
