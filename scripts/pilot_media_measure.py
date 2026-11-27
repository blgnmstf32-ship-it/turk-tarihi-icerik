"""Read-only measurements of locked pilot MP4s for the video quality lab."""
from __future__ import annotations

import itertools
from pathlib import Path
import subprocess

from scripts import video_quality_lab as lab


def _observation(check, values, frames=None, *, collector=None):
    row = {"collector": collector or lab.RULES[check][0], "values": values}
    return {**row, "frames": frames} if frames is not None else row


def _pcm(path):
    result = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(Path(path).resolve()),
                             "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                            check=True, capture_output=True, timeout=35)
    import numpy as np

    return np.frombuffer(result.stdout, dtype="<f4").astype("float64")


def audio_separation(video, voice, starts):
    """Estimate speech-to-residual ratio against the original approved waveform."""
    import numpy as np
    from scipy.signal import correlate

    dry, mixed = _pcm(voice), _pcm(video)
    anchor = int(starts[0] * 16000) if starts else 0
    start, end, lag = anchor + 1600, anchor + 97600, 1600
    sample = dry[start:end]
    if len(sample) != end - start or len(mixed) < end + lag or np.linalg.norm(sample) < 0.01:
        return None
    shift = int(np.argmax(correlate(mixed[start-lag:end+lag], sample, mode="valid", method="fft"))) - lag
    end = min(len(dry), len(mixed)-shift)
    dry, mixed = dry[max(0, -shift):end], mixed[max(0, shift):end+shift]
    size = 320
    n = len(dry) // size
    blocks = dry[:size*n].reshape(n, size)
    active = np.repeat(np.sqrt(np.mean(blocks**2, axis=1)) > .025, size)
    x, y = dry[:size*n][active], mixed[:size*n][active]
    if len(x) < 16000 or np.std(y) < .001:
        return None
    confidence = float(np.corrcoef(x, y)[0, 1])
    if not .75 <= confidence <= 1:
        return None
    fitted = x * (float(x @ y) / float(x @ x))
    residual = np.linalg.norm(y - fitted)
    ratio = min(70., 20 * np.log10(np.linalg.norm(fitted) / max(1e-8, float(residual))))
    return {"voice_over_bed_db": round(float(ratio), 2), "waveform_correlation": round(confidence, 4),
            "offset_ms": round(shift / 16, 3), "speech_samples": len(x),
            "method": "approved_voice_projection_vs_final_mix_residual_includes_processing_and_encoding"}


def _hash(gray, cv2):
    miniature = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return sum(int(bit) << i for i, bit in enumerate((miniature[:, 1:] > miniature[:, :-1]).ravel()))


def _caption_pixels(frame, brand, cv2):
    import numpy as np

    # Expected caption band, converted from 1080×1920 to 360×640 phone pixels.
    view = cv2.resize(frame, (360, 640), interpolation=cv2.INTER_AREA)
    top, bottom = (482, 543) if brand == "tarih" else (480, 527)
    strip = view[top:bottom]
    blue, green, red = cv2.split(strip)
    warm = (red >= 215) & (green >= 167) & (green >= blue)
    # White and warm subtitle styles. Reject background-heavy crops rather than scoring them.
    count = int(warm.sum())
    if not 22 <= count <= 1650:
        return None
    n, _, stats, _ = cv2.connectedComponentsWithStats(warm.astype("uint8"))
    letters = [x for x in stats[1:n] if 5 <= x[4] <= 450 and 4 <= x[3] <= 28]
    if len(letters) < 4:
        return None
    xs = min(x[0] for x in letters)
    end = max(x[0] + x[2] for x in letters)
    safe_violations = int(xs < 18 or end > 342)
    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    near = cv2.dilate(warm.astype("uint8"), np.ones((5, 5), dtype="uint8")).astype(bool) & ~warm
    if not near.any():
        return None

    def luminance(level):
        return ((level / 255 + .055) / 1.055) ** 2.4 if level > 10.3 else level / 255 / 12.92

    fg = luminance(float(np.median(gray[warm])))
    bg = luminance(float(np.median(gray[near])))
    return {"safe_area_violations": safe_violations,
            "min_contrast_ratio": round((max(fg, bg) + .05)/(min(fg, bg) + .05), 2)}


def pixel_samples(path, plan, cues):
    import cv2
    import numpy as np

    cv2.setNumThreads(2)
    capture = cv2.VideoCapture(str(path))

    def frame_at(frame):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok:
            raise ValueError(f"Could not decode frame {frame}")
        return image

    fps = plan["fps"]
    duration = plan["duration_frames"]
    first = None
    try:
        for frame in range(16):
            gray = cv2.cvtColor(frame_at(frame), cv2.COLOR_BGR2GRAY)
            if float(np.mean(gray > 24)) >= .2:
                first = frame
                break
        sampled = []
        for scene in plan["scenes"]:
            at = (scene["start_frame"] + scene["end_frame"]) // 2
            gray = cv2.cvtColor(frame_at(at), cv2.COLOR_BGR2GRAY)
            visual = scene["approved_visual"]
            # Several timeline rows can refer to the same continuous insert or dissolve.
            source = (scene["kind"] if plan["brand"] == "tarih" and scene["kind"] in {"collage", "map"}
                      else visual.get("archive_index") if plan["brand"] == "tarih" else visual["shot"])
            sampled.append((at, _hash(gray, cv2), source))
        repeats = []
        for (left, a, left_source), (right, b, right_source) in itertools.combinations(sampled, 2):
            if left_source == right_source:
                continue
            repeats.append({"frames": [left, right], "distance": (a ^ b).bit_count()})
        mobile = []
        for cue in cues:
            start = round(cue["start"] * fps)
            end = min(duration, round(cue["end"] * fps))
            at = (start + end) // 2
            measured = _caption_pixels(frame_at(at), plan["brand"], cv2)
            mobile.append({"frame": at, "cue_frames": [start, end], "sampled_phone_pixels": measured})
    finally:
        capture.release()
    return {"first_picture_frame": first, "repeat_pairs": sorted(repeats, key=lambda p: p["distance"]),
            "mobile_subtitle_samples": mobile, "mobile_scope": "sampled_caption_pixels_360x640_not_ocr"}


def collect(path, plan, cues, metrics, voice):
    import numpy as np

    evidence = lab.collect_ffmpeg(path, plan)
    rows = evidence["observations"]
    duration, fps = plan["duration_frames"], plan["fps"]
    for check in ("black_frames", "frozen_frames"):
        for index, item in enumerate(rows[check]):
            if item.get("candidate"):
                start, end = item["frames"]
                key, = lab.RULES[check][1]
                # Every detected interval is a technical warning at this threshold. Intent is adjudicated separately.
                rows[check][index] = _observation(check, {key: end-start}, item["frames"])
    pixels = pixel_samples(path, plan, cues)
    starts = metrics["word_starts"]
    picture = pixels["first_picture_frame"]
    if picture is not None and starts:
        rows["opening"] = [_observation("opening", {"first_picture_frame": picture,
                                                    "first_word_frame": round(starts[0]*fps)})]
    elif starts:
        rows["opening"] = [_observation("opening", {"first_picture_frame": 16,
                                                    "first_word_frame": round(starts[0]*fps)})]
    if starts:
        rows["narration"] = [_observation("narration", {"words_per_minute": round(len(starts)*60*fps/duration, 2)})]
    for scene in plan["scenes"]:
        bounds = [scene["start_frame"], scene["end_frame"]]
        matches = [m["offset_ms"] for m in metrics["cue_matches"] if bounds[0] <= m["frame"] < bounds[1]]
        offsets = [m for m in matches if m is not None]
        if offsets:
            rows.setdefault("subtitle_sync", []).append(_observation("subtitle_sync", {
                "matched_fraction": len(offsets)/len(matches), "p95_offset_ms": round(float(np.percentile(offsets, 95)), 2),
            }, bounds))
    for pair in pixels["repeat_pairs"]:
        if pair["distance"] < 6:
            for frame in pair["frames"]:
                rows.setdefault("visual_repeat", []).append(_observation("visual_repeat", {
                    "min_hamming_distance": pair["distance"]}, [frame, frame+1]))
    if pixels["repeat_pairs"] and "visual_repeat" not in rows:
        # This is coverage of the fixed one-frame-per-scene sampling protocol.
        rows["visual_repeat"] = [_observation("visual_repeat", {
            "min_hamming_distance": pixels["repeat_pairs"][0]["distance"]})]
    for sample in pixels["mobile_subtitle_samples"]:
        if value := sample["sampled_phone_pixels"]:
            rows.setdefault("mobile_readability", []).append(_observation("mobile_readability", value,
                sample["cue_frames"], collector="opencv-caption-pixels"))
    separation = audio_separation(path, voice, starts)
    if separation:
        rows["audio_balance"] = [_observation("audio_balance", {
            "integrated_lufs": metrics["levels"]["input_i"], "true_peak_dbtp": metrics["levels"]["input_tp"],
            "voice_over_bed_db": separation["voice_over_bed_db"]}, collector="ffmpeg-loudnorm+waveform")]
    # SceneDetect shot candidates are retained as observed evidence. Dissolves and overlays need human adjudication.
    return evidence, {**pixels, "audio_separation": separation,
                      "transition_candidates_seconds": metrics["scenes"]["starts_s"]}
