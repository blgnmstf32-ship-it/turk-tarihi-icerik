"""Explicit local media operations. No CLI is run by production or the agents."""
from __future__ import annotations

import json
from math import isfinite
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import tarfile
import wave

from scripts.motion_toolkit import ROOT, verified_local

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv"}


def _execute(command, *, cwd=None, timeout=240):
    env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "SYSTEMROOT", "TMPDIR") if key in os.environ}
    return subprocess.run(command, check=True, capture_output=True, text=True, shell=False,
                          cwd=cwd, env=env, timeout=timeout).stdout


def _path(path, suffixes):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in suffixes:
        raise ValueError("Expected a supported local media file.")
    return path


def video_shape(path):
    output = _execute(["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-select_streams", "v:0",
                       "-count_frames", "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames",
                       "-of", "json", str(_path(path, VIDEO_SUFFIXES))])
    streams = json.loads(output)["streams"]
    if len(streams) != 1:
        raise ValueError("Expected one primary video stream.")
    row = streams[0]
    count = int(row["nb_read_frames"])
    if count < 2 or row["avg_frame_rate"] in {"", "0/0"}:
        raise ValueError("Video timing or frame count is unavailable.")
    return row["width"], row["height"], row["avg_frame_rate"], count


def parse_vmaf(payload):
    mean = payload["pooled_metrics"]["vmaf"]["mean"]
    if type(mean) not in (int, float) or not isfinite(mean):
        raise ValueError("Invalid VMAF score.")
    return {"vmaf_mean": mean, "frames": len(payload["frames"]), "model": "libvmaf_builtin",
            "scope": "compression_relative_to_aligned_reference"}


def vmaf_report(reference, encoded, *, aligned=False):
    if aligned is not True:
        raise ValueError("Confirm frame alignment with the reference.")
    reference, encoded = (_path(value, VIDEO_SUFFIXES) for value in (reference, encoded))
    if reference == encoded or video_shape(reference) != video_shape(encoded):
        raise ValueError("Use distinct videos with matching dimensions, fps and frame counts.")
    if not re.search(r"\blibvmaf\b", _execute(["ffmpeg", "-hide_banner", "-filters"])):
        raise RuntimeError("This FFmpeg build does not include libvmaf.")
    graph = ("[0:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[d];"
             "[1:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[r];"
             "[d][r]libvmaf=log_fmt=json:log_path=vmaf.json:n_threads=2")
    with tempfile.TemporaryDirectory(prefix="local-vmaf-") as tmp:
        _execute(["ffmpeg", "-v", "error", "-nostdin", "-protocol_whitelist", "file", "-i", str(encoded),
                  "-protocol_whitelist", "file", "-i", str(reference), "-filter_complex", graph,
                  "-an", "-f", "null", "-"], cwd=tmp, timeout=600)
        return parse_vmaf(json.loads((Path(tmp) / "vmaf.json").read_text(encoding="utf-8")))


def inspect_glb(path):
    with Path(path).open("rb") as stream:
        header = stream.read(20)
        if len(header) != 20:
            raise ValueError("GLB header is incomplete.")
        magic, version, length, json_size, chunk = struct.unpack("<4sIII4s", header)
        if (magic, version, chunk) != (b"glTF", 2, b"JSON") or not 0 < json_size <= 5_000_000:
            raise ValueError("Expected a bounded GLB v2 manifest.")
        if length != Path(path).stat().st_size or json_size > length - 20:
            raise ValueError("Invalid GLB length.")
        model = json.loads(stream.read(json_size))
    if any("uri" in item for key in ("buffers", "images") for item in model.get(key, [])):
        raise ValueError("GLB must use internal buffers and images only.")
    # The optional job is for ordinary embedded GLB, without external codec downloads.
    if set(model.get("extensionsRequired", [])) & {"KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_texture_basisu"}:
        raise ValueError("The local lossless pipeline does not enable external codecs.")
    return model


def optimize_glb(source, receipt, output):
    source = verified_local(source, receipt, maximum_bytes=100_000_000)
    inspect_glb(source)
    output = Path(output).resolve()
    if output.exists() or output.suffix != ".glb":
        raise ValueError("Choose a new GLB destination.")
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="local-gltf-") as tmp:
        deduped, pruned = Path(tmp) / "dedup.glb", Path(tmp) / "prune.glb"
        _execute(["gltf-transform", "dedup", str(source), str(deduped)], cwd=tmp)
        _execute(["gltf-transform", "prune", str(deduped), str(pruned)], cwd=tmp)
        inspect_glb(pruned)
        # Exclusive creation protects an existing output if another task runs at the same time.
        with output.open("xb") as result:
            result.write(pruned.read_bytes())
    return {"method": "dedup_prune", "input_bytes": source.stat().st_size, "output_bytes": output.stat().st_size,
            "license": receipt["license"], "source": receipt["source"], "attribution": receipt["attribution"]}


def denoise_wav(source, weights, model_receipt, output_dir, *, noise_confirmed=False):
    if noise_confirmed is not True:
        raise ValueError("Use DeepFilterNet only after confirming audible noise.")
    source = _path(source, {".wav"})
    model = verified_local(weights, model_receipt, maximum_bytes=40_000_000)
    if not model.name.endswith(".tar.gz"):
        raise ValueError("Expected the reviewed local DeepFilterNet model archive.")
    with tarfile.open(model, "r:gz") as archive:
        size = 0
        for count, item in enumerate(archive, 1):
            size += item.size
            if (count > 64 or size > 60_000_000 or Path(item.name).is_absolute()
                    or ".." in Path(item.name).parts or not (item.isdir() or item.isreg())):
                raise ValueError("Unexpected model archive contents.")
    with wave.open(str(source), "rb") as signal:
        if signal.getframerate() != 48000 or signal.getnchannels() not in (1, 2):
            raise ValueError("DeepFilterNet requires an existing mono or stereo 48 kHz WAV.")
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=False)
    _execute(["deep-filter", "--compensate-delay", "--model", str(model), "--out-dir", str(target), str(source)], cwd=target)
    outputs = list(target.glob("*.wav"))
    if len(outputs) != 1:
        raise RuntimeError("Expected one local DeepFilterNet WAV output.")
    return {"path": str(outputs[0]), "replace_approved_voice": False, "listen_before_use": True}


DIAGRAMS = {"mechanism": "MechanismDiagram", "barrier": "SkinBarrierDiagram"}


def manim_command(kind, output_dir):
    if kind not in DIAGRAMS:
        raise ValueError("Choose an in-repository diagram.")
    output = Path(output_dir).resolve()
    return ["manim", "--renderer", "cairo", "-ql", "--disable_caching", "--format", "mp4",
            "--media_dir", str(output), str(ROOT / "scripts/motion_diagrams.py"), DIAGRAMS[kind]]


def render_science_diagram(kind, output_dir):
    command = manim_command(kind, output_dir)
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=False)
    _execute(command, cwd=target, timeout=600)
    media = [file for file in target.rglob(DIAGRAMS[kind] + ".mp4") if file.is_file()]
    if len(media) != 1:
        raise RuntimeError("Expected exactly one local Manim diagram.")
    return {"path": str(media[0]), "label": "TEMSİLÎ ŞEMA · ÖLÇEK DIŞI", "human_review_required": True}
