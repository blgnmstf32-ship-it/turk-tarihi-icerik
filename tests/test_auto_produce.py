import tempfile, unittest, json
from unittest.mock import patch
from pathlib import Path
from PIL import Image
from scripts.run import ROOT, load_json
from scripts.auto_produce import production,verified_facts_only,performance_script,audio_mix_command
from scripts.subtitles import create,create_timed
from scripts.illustrate import generate

class AutomaticProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.topic=next(t for t in load_json(ROOT/'data'/'topics.json') if t['id']=='malazgirt-1071')
    def test_script_factual_guard(self):
        text=verified_facts_only(self.topic)
        self.assertTrue(all(f in text for f in self.topic['facts']))
    def test_final_mix_maps_the_narration_file_not_remotion_silence(self):
        command=audio_mix_command('visuals.mp4','narration.wav','music.wav','final.mp4')
        self.assertEqual(command[command.index('-i')+1],'visuals.mp4')
        self.assertEqual(command[command.index('-i',command.index('-i')+1)+1],'narration.wav')
        graph=command[command.index('-filter_complex')+1]
        self.assertIn('[1:a]volume=1.0[voice]',graph)
        self.assertIn('[2:a]volume=0.12[music]',graph)
        self.assertIn('[voice][music]amix=',graph)
    def test_subtitle_estimated_times(self):
        with tempfile.TemporaryDirectory() as d:
            f=create('İlk cümle. İkinci cümle.',26,Path(d)/'v.srt')
            self.assertIn('00:00:26,000',f.read_text())
    def test_performance_script_uses_spoken_date_and_documentary_length(self):
        lines=performance_script(self.topic)
        self.assertGreaterEqual(len(lines),10)
        self.assertTrue(any('Yirmi altı Ağustos' in x['spoken'] for x in lines))
        self.assertTrue(any('!' in x['spoken'] or '...' in x['spoken'] for x in lines))
        words=sum(len(x['spoken'].split()) for x in lines)
        self.assertGreaterEqual(words,115)
        self.assertLessEqual(words,165)
    def test_timed_subtitles_follow_audio_cues(self):
        with tempfile.TemporaryDirectory() as d:
            f=create_timed([{'start':0.0,'end':1.35,'text':'Vurgu cümlesi.'},
                            {'start':1.8,'end':3.1,'text':'İkinci cümle.'}],Path(d)/'v.srt')
            text=f.read_text()
            self.assertIn('00:00:01,350',text)
            self.assertIn('00:00:01,800 --> 00:00:03,100',text)
    def test_twenty_four_roles_ten_scenes_and_malazgirt_3d_plan(self):
        with tempfile.TemporaryDirectory() as d:
            board={'coordinator_llm':{'actual_llm_used':False,'calls':0}}
            with patch('scripts.auto_produce.run_board',return_value=board):
                result=production(self.topic,Path(d)/'draft',Path(d)/'cache',skip_narration=True)
            self.assertEqual(result['roles'],24)
            self.assertFalse(result['ready_for_instagram'])
            self.assertFalse(result['instagram_published'])
            self.assertFalse(result['paid_api_services_enabled'])
            self.assertEqual(result['three_d']['scenes'][0]['kind'],'battle_map')
            self.assertTrue((Path(d)/'draft'/'3D_SCENE_PLAN.json').exists())
            self.assertEqual(result['editorial_decision_report'],'editorial/EDITORIAL_DECISION_REPORT.md')
            llm_report=json.loads((Path(d)/'draft'/'AI_AGENT_EXECUTION_REPORT.json').read_text())
            self.assertEqual(len(llm_report['roles']),24)
            self.assertEqual(llm_report['original_20_llm_calls'],0)
            self.assertFalse(llm_report['coordinator_actual_llm_used'])
            self.assertEqual(result['target_duration_seconds'],{'min':60,'max':75})
            paths=list((Path(d)/'draft'/'scenes').glob('*_scene.jpg'))
            self.assertEqual(len(paths),10)
            self.assertEqual(len({p.read_bytes() for p in paths}),10)
            for p in paths:
                with Image.open(p) as img:self.assertEqual(img.size,(1080,1920))
            stale=Path(d)/'draft'/'scenes'/'stale_commons.jpg'
            Image.new('RGB',(180,320),(0,0,0)).save(stale)
            generate(self.topic,Path(d)/'draft'/'scenes')
            self.assertFalse(stale.exists())
            self.assertEqual(len(list((Path(d)/'draft'/'scenes').glob('*.jpg'))),10)
