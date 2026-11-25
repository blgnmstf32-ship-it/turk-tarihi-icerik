import json, tempfile, unittest
from pathlib import Path
from scripts.voice_provider import select_provider
from scripts.ai_image_provider import generate
from scripts.task_observer import record
from scripts.instagram_insights import get_insights

class ProviderSafetyTests(unittest.TestCase):
    def settings(self):
        return {'billing_enabled':False,'paid_services_enabled':False,'cloud_voice_enabled':False,'voice_provider':'gemini_tts',
                'cloud_voice':{'google_chirp3_hd':{'enabled':False},'azure_speech':{'enabled':False}},
                'ai_image_provider':{'enabled':False}}
    def test_cloud_voice_fails_closed_without_paid_fallback(self):
        with self.assertRaisesRegex(RuntimeError,'otomatik geçiş yok'):
            select_provider(self.settings(),'google_chirp3_hd')
    def test_charon_is_the_only_provider(self):
        self.assertEqual(select_provider(self.settings()),'gemini_tts')
        for provider in ("piper","azure_speech","google_chirp3_hd","human_recording"):
            with self.subTest(provider=provider),self.assertRaises(RuntimeError):
                select_provider(self.settings(),provider)
    def test_image_adapter_is_disabled(self):
        self.assertEqual(generate('historical image','unused.png',self.settings())['status'],'disabled')
    def test_observer_redacts_secret_fields(self):
        with tempfile.TemporaryDirectory() as d:
            row=record('failed',{'api_key':'do-not-log','error':'token=do-not-log'},Path(d)/'e.jsonl')
            raw=(Path(d)/'e.jsonl').read_text()
            self.assertNotIn('do-not-log',raw)
            self.assertIn('[REDACTED]',raw)
    def test_insights_scaffold_disabled_and_read_only(self):
        self.assertEqual(get_insights(),{'status':'disabled','read_only':True,'published':False,'records':[]})
    def test_optional_local_audits_report_missing_dependencies(self):
        import builtins
        from unittest.mock import patch
        from scripts.speech_audit import transcribe_local
        from scripts.scene_audit import audit
        original=builtins.__import__
        def blocked(name,*args,**kwargs):
            if name=='faster_whisper' or name=='scenedetect': raise ImportError('optional dependency absent')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=blocked):
            with self.assertRaisesRegex(RuntimeError,'faster-whisper'):
                transcribe_local('not-used.wav')
            with self.assertRaisesRegex(RuntimeError,'PySceneDetect'):
                audit('not-used.mp4')
    def test_default_settings_keep_paid_and_publish_gates_off(self):
        settings=json.loads(Path('config/settings.json').read_text())
        self.assertFalse(settings['paid_services_enabled'])
        self.assertFalse(settings['billing_enabled'])
        self.assertFalse(settings['cloud_voice_enabled'])
        self.assertFalse(settings['instagram_auto_publish_enabled'])
        self.assertEqual(settings['monthly_spend_limit_try'],0)
        self.assertEqual(settings['video_resolution'],'1080x1920')
    def test_twenty_existing_roles_preserved_and_3d_roles_added(self):
        roles=json.loads(Path('config/agents.json').read_text())
        self.assertEqual(len(roles),24)
        self.assertEqual([x['id'] for x in roles],list(range(1,25)))
        self.assertEqual([x['name'] for x in roles[-4:]],['3D Sahne Planlayıcı','3D Animasyon Ajanı','3D Render Ajanı','3D Kalite Kontrol Ajanı'])
        settings=json.loads(Path('config/settings.json').read_text())
        self.assertFalse(settings['three_d_generation']['paid_ai_generation_enabled'])
        self.assertTrue(settings['three_d_generation']['render_failure_fallback']=='2d')
