"""Offline-only tests. Synthetic audio is a test tone, NOT usable narration."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.create_reel import collect_scenes

class VideoRenderTests(unittest.TestCase):
    def test_five_unique_scenes_required(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(4):
                Image.new('RGB',(180,320),(i*45,20,20)).save(d/f'{i:02d}.png')
            with self.assertRaisesRegex(ValueError,'5'):
                collect_scenes(d)
            Image.new('RGB',(180,320),(180,20,20)).save(d/'04.png')
            self.assertEqual(len(collect_scenes(d)),5)
    def test_duplicate_scenes_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(5): Image.new('RGB',(180,320),(2,15,30)).save(d/f'{i:02d}.png')
            with self.assertRaisesRegex(ValueError,'farklı'):
                collect_scenes(d)

if __name__=='__main__':unittest.main()
