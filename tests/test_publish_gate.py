import unittest,tempfile,json
from pathlib import Path
from scripts.instagram_publish import safe_public_url,publish

class PublishGateTests(unittest.TestCase):
    def test_private_url_rejected(self):
        self.assertFalse(safe_public_url('http://localhost:3000/a.mp4'))
        self.assertFalse(safe_public_url('file:///tmp/a.mp4'))
    def test_requires_owner_review(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'approval.json';p.write_text(json.dumps({'approved_by_owner':False,'content_reviewed':False}))
            with self.assertRaises(PermissionError):publish('https://example.org/video.mp4','caption',p,False)
    def test_never_publish_default(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'approval.json';p.write_text(json.dumps({'approved_by_owner':True,'content_reviewed':True}))
            self.assertEqual(publish('https://example.org/video.mp4','caption',p,False)['published'],False)
