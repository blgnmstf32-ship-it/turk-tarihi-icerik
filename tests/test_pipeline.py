import json, tempfile, unittest
from pathlib import Path
from scripts.run import ROOT,load_json,build

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.topics=load_json(ROOT/'data'/'topics.json')
    def test_20_distinct_roles(self):
        roles=load_json(ROOT/'config'/'agents.json')
        self.assertEqual(len(roles),20)
        self.assertEqual([r['id'] for r in roles],list(range(1,21)))
    def test_source_guard(self):
        t=dict(self.topics[0]);t['sources']=[]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):build(t,d,False)
    def test_manual_gate_and_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=build(self.topics[0],d,False)
            self.assertEqual(p['n_roles'],20)
            self.assertFalse(p['approval']['approved'])
            self.assertFalse(p['approval']['publish_enabled'])
            self.assertTrue((Path(d)/'post_1080x1350.png').exists())
            self.assertTrue((Path(d)/'caption.txt').exists())
            self.assertEqual(p['cost']['paid_api_calls'],0)

    def test_silent_slides_never_marked_publish_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=build(self.topics[0],d,True)
            self.assertIsNone(p['files']['mp4'])
            self.assertFalse(p['files']['ready_for_instagram'])
            self.assertTrue((Path(d)/p['files']['silent_preview_only']).exists())
    def test_old_silent_reel_rejected_by_release_gate(self):
        from scripts.release_check import check
        with tempfile.TemporaryDirectory() as d:
            old=ROOT/'sample_output'/'malazgirt'/'reel_15sn_720x1280.mp4'
            with self.assertRaises(ValueError):check(old,Path(d)/'notthere.wav',Path(d)/'notthere.srt',Path(d))

if __name__=='__main__':unittest.main()
