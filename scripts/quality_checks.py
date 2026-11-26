"""Run the standard unittest suite without media generation or network calls."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import unittest
from unittest.mock import patch
import wave


# Fixture tests remain available with the repository's ordinary unittest command.
MEDIA_FIXTURES = {
    "test_auto_produce.AutomaticProductionTests.test_twenty_four_roles_ten_scenes_and_malazgirt_3d_plan": "image",
    "test_beauty_studio.BeautyStudioTest.test_brand_identity_calendar_and_silent_review_drafts": "image",
    "test_commons_media.CommonsLicenseTests.test_wide_framing_preserves_both_edges_and_resize_is_near_duplicate": "image",
    "test_daily_editorial.DailyEditorialTests.test_real_silent_vertical_story_package_and_date_guard": "image",
    "test_dual_provider.DualProviderTests.test_completed_documented_rest_batch_shape_is_decoded": "image",
    "test_gemini_tts.GeminiNarrationTests.test_approved_recording_is_bound_to_both_hashes_and_skips_api": "audio",
    "test_gemini_tts.GeminiNarrationTests.test_one_take_uses_fixed_model_voice_and_separate_style": "audio",
    "test_gemini_tts.GeminiNarrationTests.test_unsafe_duration_and_quota_error_do_not_retry_or_leak_key": "audio",
    "test_gemini_tts.GeminiNarrationTests.test_same_verified_live_take_is_reused_without_second_paid_or_free_call": "audio",
    "test_pipeline.PipelineTests.test_manual_gate_and_outputs": "image",
    "test_pipeline.PipelineTests.test_silent_preview_gracefully_skips_without_ffmpeg": "image",
    "test_pipeline.PipelineTests.test_silent_slides_never_marked_publish_ready": "image+video",
    "test_video_render.VideoRenderTests.test_duplicate_scenes_rejected": "image",
    "test_video_render.VideoRenderTests.test_ten_unique_scenes_required": "image",
    "test_voice_lab.VoiceComparisonTests.test_real_take_receipt_is_required_and_tied_to_audio_and_script": "audio",
}


def _tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _tests(item)
        else:
            yield item


def main():
    all_tests = {case.id(): case for case in _tests(unittest.defaultTestLoader.discover("tests"))}
    if missing := MEDIA_FIXTURES.keys() - all_tests.keys():
        raise RuntimeError(f"Review the media fixture list: {sorted(missing)}")
    suite = unittest.TestSuite(case for key, case in all_tests.items() if key not in MEDIA_FIXTURES)
    print(f"Python tests discovered: {len(all_tests)}", flush=True)
    deferred = Counter(MEDIA_FIXTURES.values())
    print(f"Media fixture tests deferred: {len(MEDIA_FIXTURES)} ({dict(sorted(deferred.items()))})", flush=True)
    for test, kind in sorted(MEDIA_FIXTURES.items()):
        print(f"  {kind}: {test}", flush=True)

    open_wave = wave.open

    def read_wave(file, mode=None):
        if mode != "rb":
            raise AssertionError("The quality suite allows only explicit read-only WAV access.")
        return open_wave(file, mode)

    blocked_calls = ("socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo",
                     "PIL.Image.new", "PIL.Image.Image.save", "subprocess.Popen")
    with ExitStack() as guard:
        for operation in blocked_calls:
            guard.enter_context(patch(operation, side_effect=AssertionError(f"Offline quality: {operation}")))
        guard.enter_context(patch("wave.open", side_effect=read_wave))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.testsRun != suite.countTestCases() or not result.wasSuccessful():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
