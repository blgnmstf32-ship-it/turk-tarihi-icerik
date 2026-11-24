import json, tempfile, unittest, shutil
from unittest.mock import patch
from pathlib import Path
from scripts.run import ROOT,load_json,build

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.topics=load_json(ROOT/'data'/'topics.json')
    def test_twenty_original_roles_and_four_3d_roles(self):
        roles=load_json(ROOT/'config'/'agents.json')
        self.assertEqual(len(roles),24)
        self.assertEqual([r['id'] for r in roles],list(range(1,25)))
        self.assertEqual([r['name'] for r in roles[:20]][:2],['Konu Avcısı','Kronolog'])
        self.assertEqual([r['name'] for r in roles[20:]],['3D Sahne Planlayıcı','3D Animasyon Ajanı','3D Render Ajanı','3D Kalite Kontrol Ajanı'])
    def test_source_guard(self):
        t=dict(self.topics[0]);t['sources']=[]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):build(t,d,False)
    def test_manual_gate_and_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=build(self.topics[0],d,False)
            self.assertEqual(p['n_roles'],24)
            self.assertFalse(p['approval']['approved'])
            self.assertFalse(p['approval']['publish_enabled'])
            self.assertTrue((Path(d)/'post_1080x1350.png').exists())
            self.assertTrue((Path(d)/'caption.txt').exists())
            self.assertEqual(p['cost']['paid_api_calls'],0)
            self.assertEqual(p['three_d_scene_plan']['scenes'][0]['kind'],'artifact_gears')

    def test_silent_slides_never_marked_publish_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=build(self.topics[0],d,True)
            self.assertIsNone(p['files']['mp4'])
            self.assertFalse(p['files']['ready_for_instagram'])
            if shutil.which('ffmpeg'):
                self.assertTrue((Path(d)/p['files']['silent_preview_only']).exists())
            else:
                self.assertIsNone(p['files']['silent_preview_only'])
    def test_silent_preview_gracefully_skips_without_ffmpeg(self):
        with tempfile.TemporaryDirectory() as d, patch('scripts.run.shutil.which',return_value=None):
            p=build(self.topics[0],d,True)
            self.assertIsNone(p['files']['silent_preview_only'])
            self.assertFalse(p['files']['ready_for_instagram'])
    def test_old_silent_reel_rejected_by_release_gate(self):
        from scripts.release_check import check
        with tempfile.TemporaryDirectory() as d:
            old=ROOT/'sample_output'/'malazgirt'/'reel_15sn_720x1280.mp4'
            with self.assertRaises(ValueError):check(old,Path(d)/'notthere.wav',Path(d)/'notthere.srt',Path(d))

if __name__=='__main__':unittest.main()
