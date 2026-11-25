from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import voice_lab


class VoiceComparisonTests(unittest.TestCase):
    def test_uses_the_published_workflow_script_without_editorial_calls(self):
        topic, segments, script = voice_lab.topic_and_script()
        self.assertEqual(topic["id"], "piri-reis-kayip-kaynak")
        self.assertEqual(script.splitlines(), topic["narration"])
        self.assertEqual(len(segments), len(topic["narration"]))
        workflow = (voice_lab.ROOT / ".github/workflows/voice_comparison.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("OPENROUTER", workflow)
        self.assertNotIn("editorial_board", workflow)
        self.assertNotIn("instagram_publish", workflow)

    def test_real_take_receipt_is_required_and_tied_to_audio_and_script(self):
        with TemporaryDirectory() as work:
            out = Path(work)
            _, _, script = voice_lab.topic_and_script()
            with self.assertRaises(FileNotFoundError):
                voice_lab.validate_gemini_take(out, script)
            with patch("voice_lab.request_audio", return_value=(b"test-fixture", 65)) as request:
                voice_lab.gemini_take(out, True)
            request.assert_called_once_with(script, True)
            self.assertEqual(voice_lab.validate_gemini_take(out, script)["voice"], "Charon")
            (out / "GEMINI_CHARON.wav").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                voice_lab.validate_gemini_take(out, script)

    def test_measures_cue_coverage_and_speech_pauses(self):
        captions = [{"start": 0, "end": 1}, {"start": 2, "end": 3}]
        words = [{"start": .2, "end": .5}, {"start": 2.2, "end": 2.5}]
        metrics = voice_lab.timing_metrics(captions, words, 4)
        self.assertEqual(metrics["speech_word_midpoints_in_captions"], 1)
        self.assertEqual(metrics["pause_count_at_least_250ms"], 1)
        self.assertEqual(metrics["longest_detected_pause_seconds"], 1.7)
        with self.assertRaises(ValueError):
            voice_lab.timing_metrics([{"start": 0, "end": 4.5}], words, 4)
        self.assertEqual(voice_lab.word_error_rate("Piri Reis, Gelibolu.", "Piri Reis, Gelibolu."), 0)
