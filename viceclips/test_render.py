import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from viceclips.process_video import build_video_filter, select_speech_dense_window


class SelectionTests(unittest.TestCase):
    def test_sweep_matches_brute_force(self):
        random.seed(7)
        rows = []
        cursor = 0.0
        for _ in range(250):
            cursor += random.random() * 2.0
            rows.append((cursor, cursor + random.uniform(0.08, 0.5), "word"))
        duration, clip_len = 240.0, 35.0
        candidates = [max(0.0, min(duration - clip_len, s - clip_len / 2))
                      for s, _, _ in rows]
        candidates += [0.0, duration - clip_len]
        expected = max(
            ((sum(1 for s, e, _ in rows if s < start + clip_len and e > start), -start)
             for start in candidates)
        )
        start, score = select_speech_dense_window(rows, duration, clip_len)
        self.assertEqual(score, expected[0])
        self.assertAlmostEqual(start, -expected[1])

    def test_empty_rows_still_returns_valid_window(self):
        self.assertEqual(select_speech_dense_window([], 100.0, 35.0), (0.0, 0))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg is not installed")
class RenderSmokeTests(unittest.TestCase):
    def test_vertical_render_and_subtitle_path(self):
        with tempfile.TemporaryDirectory(prefix="viceclips-smoke-") as folder:
            root = Path(folder)
            source = root / "source.mp4"
            captions = root / "captions.srt"
            output = root / "rendered.mp4"
            captions.write_text(
                "1\n00:00:00,200 --> 00:00:01,200\nVICECLIPS TEST\n\n",
                encoding="utf-8",
            )
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(source),
            ], check=True)
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-i", str(source),
                "-vf", build_video_filter(captions),
                "-t", "2", "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", str(output),
            ], check=True)
            probe = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0", str(output),
            ], text=True).strip()
            self.assertEqual(probe, "1080x1920")


if __name__ == "__main__":
    unittest.main()
