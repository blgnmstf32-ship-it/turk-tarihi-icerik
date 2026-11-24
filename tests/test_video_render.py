"""Offline-only tests. Synthetic audio is a test tone, NOT usable narration."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.create_reel import collect_scenes
from scripts.three_scene import plan_3d_scenes, render_with_2d_fallback
from scripts.run import load_json, ROOT

class VideoRenderTests(unittest.TestCase):
    def test_automatic_scene_plans_for_battles_and_city_captures(self):
        topics=load_json(ROOT/'data'/'topics.json')
        malazgirt=plan_3d_scenes(next(t for t in topics if t['id']=='malazgirt-1071'))
        istanbul=plan_3d_scenes(next(t for t in topics if t['id']=='istanbul-1453'))
        self.assertEqual(malazgirt['scenes'][0]['kind'],'battle_map')
        self.assertIn('SELÇUKLU ORDUSU',malazgirt['scenes'][0]['labels'])
        self.assertEqual([s['kind'] for s in istanbul['scenes']],['city_flyover','siege'])
        self.assertEqual(malazgirt['paid_api_calls'],0)
        self.assertEqual(malazgirt['fallback'],'existing 2D scene sequence')

    def test_3d_failure_retries_with_existing_2d_renderer(self):
        calls=[]
        def render(*args,three_scenes):
            calls.append(three_scenes)
            if three_scenes:raise RuntimeError('WebGL unavailable')
            return {'renderer':'2D Remotion'}
        video,status=render_with_2d_fallback(render,'scene-dir',three_scenes=[{'kind':'battle_map'}])
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[1],[])
        self.assertEqual(video['renderer'],'2D Remotion')
        self.assertEqual(status['status'],'fallback_2d_after_3d_failure')
        self.assertTrue(status['fallback_used'])

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
