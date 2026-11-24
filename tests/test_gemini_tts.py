import base64
import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from scripts import gemini_tts
from scripts.voice_provider import select_provider


def gemini_wav(seconds=65):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\x01\x00" * int(24000 * seconds))
    return buffer.getvalue()


def audio_response(raw):
    response = Mock(status_code=200)
    response.json.return_value = {"status": "completed", "steps": [{"type": "model_output", "content": [
        {"type": "audio", "data": base64.b64encode(raw).decode("ascii")}
    ]}]}
    return response


class GeminiNarrationTests(unittest.TestCase):
    def test_plain_provider_configuration_cannot_start_gemini(self):
        with patch.dict("os.environ", {"TURK_TARIHI_VOICE_PROVIDER": "gemini_tts"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "açık"):
                select_provider({"voice_provider": "piper"})

    def test_absence_of_free_project_confirmation_or_key_stops_before_request(self):
        request = Mock()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "confirm-gemini-free-project"):
                gemini_tts.request_audio("Metin", False, request)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY eksik"):
                gemini_tts.request_audio("Metin", True, request)
        request.assert_not_called()

    def test_one_take_uses_fixed_model_voice_and_separate_style(self):
        text = "Bir taş konuşuyor.\nRosetta Taşı'nın hikâyesi."
        raw = gemini_wav()
        request = Mock(return_value=audio_response(raw))
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
            actual, length = gemini_tts.request_audio(text, True, request)
        self.assertEqual((actual, length), (raw, 65))
        request.assert_called_once()
        url = request.call_args.args[0]
        args = request.call_args.kwargs
        self.assertNotIn("test-key", url)
        self.assertEqual(args["headers"], {"x-goog-api-key": "test-key"})
        self.assertFalse(args["allow_redirects"])
        self.assertFalse(args["json"]["store"])
        self.assertEqual(args["json"]["model"], "gemini-3.8-flash-tts")
        self.assertEqual(args["json"]["generation_config"]["speech_config"], [{"voice": "Charon"}])
        turn = args["json"]["input"][0]["content"][0]
        self.assertEqual(turn["text"], text)
        self.assertIn("kendin belirle", turn["annotations"][0]["style"])

    def test_unsafe_duration_and_quota_error_do_not_retry_or_leak_key(self):
        request = Mock(return_value=audio_response(gemini_wav(seconds=55)))
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaisesRegex(ValueError, "55.0 saniye"):
                gemini_tts.request_audio("Bir cümle.", True, request)
            request.assert_called_once()
            response = Mock(status_code=429)
            response.raise_for_status.side_effect = requests.HTTPError("test-key", response=response)
            failing = Mock(return_value=response)
            with self.assertRaisesRegex(RuntimeError, r"\(HTTP 429\)") as raised:
                gemini_tts.request_audio("Başka cümle.", True, failing)
            self.assertNotIn("test-key", str(raised.exception))
            failing.assert_called_once()

    def test_aligns_single_take_to_real_words_without_inventing_pause_timing(self):
        segments = [{"spoken":"Işık geldi.", "caption":"Işık geldi."},
                    {"spoken":"İşte eski taş.", "caption":"ESKİ TAŞ"}]
        words = [{"start":start, "end":end, "text":word} for start, end, word in [
            (0.10, 0.40, "ışık"), (0.55, 0.95, "geldi."),
            (3.10, 3.50, "işte"), (3.56, 3.75, "eski"), (3.80, 4.20, "taş.")
        ]]
        cues = gemini_tts.align_captions(segments, words, 65)
        self.assertEqual(cues, [{"start":0.1, "end":0.95, "text":"Işık geldi."},
                                {"start":3.1, "end":4.2, "text":"ESKİ TAŞ"}])
        with self.assertRaises(ValueError):
            gemini_tts.align_captions(segments, words[2:], 65)

    def test_missing_whisper_model_stops_before_cloud(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"GEMINI_API_KEY":"test-key"}, clear=True), \
                patch("scripts.speech_audit.load_local_model", side_effect=RuntimeError("missing")), \
                patch("scripts.gemini_tts.request_audio") as request:
            with self.assertRaisesRegex(RuntimeError, "missing"):
                gemini_tts.narrate([{"spoken":"Bir cümle", "caption":"Bir cümle"}], Path(tmp) / "voice.wav", True)
            request.assert_not_called()
