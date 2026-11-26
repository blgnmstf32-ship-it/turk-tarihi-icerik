from unittest import TestCase

from scripts.ai_agents import _media_advice
from scripts.media_tools import discover, options


class MediaToolsTests(TestCase):
    def test_only_role_allowlist_is_accepted(self):
        fields = '{"suggestion":"Öneri","caveat":"İnceleme","source_numbers":[],"%s":"%s"}'
        allowed = options("bakim", 17)
        result, error = _media_advice(fields % ("media_tool", "earshot"), 0, allowed)
        self.assertIsNone(error)
        self.assertEqual(result["media_tool"], "earshot")
        self.assertEqual(_media_advice(fields % ("media_tool", "yt-dlp"), 0, allowed),
                         (None, "invalid_media_tool"))

    def test_openverse_filters_metadata_and_never_claims_original_is_reviewed(self):
        class Reply:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                base = {"foreign_landing_url": "https://example.com/media", "creator": "Üretici",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/"}
                return {"results": [{**base, "license": "by"}, {**base, "license": "by-nc"},
                                    {**base, "license": "by", "foreign_landing_url": "file:///media"}]}

        value = discover("openverse", "test", get=lambda *_args, **_kw: Reply())
        self.assertEqual(value["status"], "found")
        self.assertEqual(len(value["candidates"]), 1)
        self.assertEqual(value["candidates"][0]["verification"], "original_page_review_required")
