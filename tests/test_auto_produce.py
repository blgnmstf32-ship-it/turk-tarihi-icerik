import tempfile, unittest
from pathlib import Path
from PIL import Image
from scripts.run import ROOT, load_json
from scripts.auto_produce import production,verified_facts_only,performance_script
from scripts.subtitles import create,create_timed

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
    def test_performance_script_uses_spoken_date_and_rhythm(self):
        lines=performance_script(self.topic)
        self.assertGreaterEqual(len(lines),8)
        self.assertTrue(any('Yirmi altı Ağustos' in x['spoken'] for x in lines))
        self.assertTrue(any('!' in x['spoken'] or '...' in x['spoken'] for x in lines))
        self.assertIn('İki ordu... Ve', ' '.join(x['spoken'] for x in lines))
    def test_timed_subtitles_follow_audio_cues(self):
        with tempfile.TemporaryDirectory() as d:
            f=create_timed([{'start':0.0,'end':1.35,'text':'Vurgu cümlesi.'},
                            {'start':1.8,'end':3.1,'text':'İkinci cümle.'}],Path(d)/'v.srt')
            text=f.read_text()
            self.assertIn('00:00:01,350',text)
            self.assertIn('00:00:01,800 --> 00:00:03,100',text)
    def test_ten_unique_visuals_zero_pays_zero_publishes(self):
        with tempfile.TemporaryDirectory() as d:
            result=production(self.topic,Path(d)/'draft',Path(d)/'cache',skip_narration=True)
            self.assertEqual(result['roles'],20)
            self.assertFalse(result['ready_for_instagram'])
            self.assertFalse(result['instagram_published'])
            self.assertFalse(result['paid_api_services_enabled'])
            paths=list((Path(d)/'draft'/'scenes').glob('*_scene.jpg'))
            self.assertEqual(len(paths),10)
            self.assertEqual(len({p.read_bytes() for p in paths}),10)
            for p in paths:
                with Image.open(p) as img:self.assertEqual(img.size,(720,1280))
