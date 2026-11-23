import tempfile, unittest
from pathlib import Path
from PIL import Image
from scripts.run import ROOT, load_json
from scripts.auto_produce import production,verified_facts_only
from scripts.subtitles import create

class AutomaticProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.topic=load_json(ROOT/'data'/'topics.json')[0]
    def test_script_factual_guard(self):
        text=verified_facts_only(self.topic)
        self.assertTrue(all(f in text for f in self.topic['facts']))
    def test_subtitle_estimated_times(self):
        with tempfile.TemporaryDirectory() as d:
            f=create('İlk cümle. İkinci cümle.',26,Path(d)/'v.srt')
            self.assertIn('00:00:26,000',f.read_text())
    def test_five_unique_visuals_zero_pays_zero_publishes(self):
        with tempfile.TemporaryDirectory() as d:
            result=production(self.topic,Path(d)/'draft',Path(d)/'cache',skip_narration=True)
            self.assertEqual(result['roles'],20)
            self.assertFalse(result['ready_for_instagram'])
            self.assertFalse(result['instagram_published'])
            self.assertFalse(result['paid_api_services_enabled'])
            paths=list((Path(d)/'draft'/'scenes').glob('*_scene.jpg'))
            self.assertEqual(len(paths),5)
            self.assertEqual(len({p.read_bytes() for p in paths}),5)
            for p in paths:
                with Image.open(p) as img:self.assertEqual(img.size,(720,1280))
