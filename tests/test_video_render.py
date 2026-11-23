"""Offline-only tests. Synthetic audio is a test tone, NOT usable narration."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.create_reel import collect_scenes

class VideoRenderTests(unittest.TestCase):
    def test_ten_unique_scenes_required(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(9):
                Image.new('RGB',(180,320),(i*20,20,20)).save(d/f'{i:02d}.png')
            with self.assertRaisesRegex(ValueError,'10'):
                collect_scenes(d)
            Image.new('RGB',(180,320),(220,20,20)).save(d/'09.png')
            self.assertEqual(len(collect_scenes(d)),10)
    def test_duplicate_scenes_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(10): Image.new('RGB',(180,320),(2,15,30)).save(d/f'{i:02d}.png')
            with self.assertRaisesRegex(ValueError,'farklı'):
                collect_scenes(d)

if __name__=='__main__':unittest.main()
