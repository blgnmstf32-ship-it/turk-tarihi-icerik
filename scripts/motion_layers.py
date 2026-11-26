"""Optional local CPU depth and alpha preparation. Importing this module creates no media."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.motion_toolkit import registry, sha256_file, verified_local

MAX_IMAGE_BYTES = 24_000_000
MAX_MODEL_BYTES = 68_000_000
DEPTH_MODEL_SHA256 = registry()["tools"]["depth-small"]["weight_sha256"]


def depth_model(path):
    path = Path(path).resolve(strict=True)
    if (not path.is_file() or path.suffix != ".onnx" or path.stat().st_size > MAX_MODEL_BYTES
            or sha256_file(path) != DEPTH_MODEL_SHA256):
        raise ValueError("Only the pinned Apache-2.0 Depth Anything V2 Small ONNX is accepted.")
    return path


def _read_image(path):
    from PIL import Image

    with Image.open(path) as source:
        if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 9_000_000:
            raise ValueError("Unsupported image or image dimensions.")
        return source.convert("RGB")


def _new_output(output):
    path = Path(output)
    if path.suffix.lower() != ".png" or path.exists():
        raise ValueError("Choose a new PNG output path.")
    return path


def estimate_depth(image, image_receipt, model, output):
    model = depth_model(model)
    source = verified_local(image, image_receipt, maximum_bytes=MAX_IMAGE_BYTES)
    output = _new_output(output)
    import numpy as np
    import onnxruntime as ort
    from PIL import Image

    picture = _read_image(source)
    # Use a fixed CPU input, preserving the aspect ratio with edge padding.
    ratio = 518 / max(picture.size)
    width, height = (max(1, round(extent * ratio)) for extent in picture.size)
    x, y = (518 - width) // 2, (518 - height) // 2
    resized = picture.resize((width, height), Image.Resampling.BICUBIC)
    values = np.asarray(resized, dtype=np.float32) / 255
    values = np.pad(values, ((y, 518 - height - y), (x, 518 - width - x), (0, 0)), mode="edge")
    mean = np.asarray([.485, .456, .406], dtype=np.float32)
    std = np.asarray([.229, .224, .225], dtype=np.float32)
    batch = np.ascontiguousarray(((values - mean) / std).transpose(2, 0, 1)[None])
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(model.read_bytes(), sess_options=options, providers=["CPUExecutionProvider"])
    depth = np.squeeze(session.run(None, {session.get_inputs()[0].name: batch})[0])
    if depth.ndim != 2 or min(depth.shape) < 2 or not np.isfinite(depth).all():
        raise ValueError("Unexpected depth tensor.")
    height_scale, width_scale = depth.shape[0] / 518, depth.shape[1] / 518
    depth = depth[round(y * height_scale):round((y + height) * height_scale),
                  round(x * width_scale):round((x + width) * width_scale)]
    if min(depth.shape) < 2:
        raise ValueError("Image aspect ratio leaves too little usable depth.")
    low, high = np.percentile(depth, [2, 98])
    if high <= low:
        raise ValueError("Depth range is flat.")
    normalized = np.clip((depth - low) / (high - low), 0, 1)
    Image.fromarray((normalized * 65535).astype(np.uint16)).save(output)
    return {"model": "depth-anything-v2-small-onnx", "model_sha256": DEPTH_MODEL_SHA256,
            "image_sha256": image_receipt["sha256"], "depth_sha256": sha256_file(output),
            "path": str(output), "kind": "relative_depth_not_metric"}


def prepare_parallax(image, image_receipt, depth, depth_report, output_dir):
    import numpy as np
    from PIL import Image

    image = verified_local(image, image_receipt, maximum_bytes=MAX_IMAGE_BYTES)
    if (depth_report.get("kind") != "relative_depth_not_metric"
            or depth_report.get("model_sha256") != DEPTH_MODEL_SHA256
            or depth_report.get("image_sha256") != image_receipt["sha256"]
            or depth_report.get("depth_sha256") != sha256_file(depth)):
        raise ValueError("Depth report does not match the approved original.")
    picture = _read_image(image)
    with Image.open(depth) as source:
        if source.format != "PNG" or source.mode not in {"I;16", "I"} or source.width * source.height > 1_000_000:
            raise ValueError("A bounded 16-bit depth PNG is required.")
        plane = np.asarray(source.convert("F").resize(picture.size, Image.Resampling.BILINEAR)) / 65535
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=False)
    layers = []
    # Two bounded near planes. The unchanged base fills all disoccluded pixels.
    for number, (minimum, maximum, travel) in enumerate(((.48, .76, 5), (.72, 1.1, 9)), 1):
        alpha = np.clip((plane - minimum) / .06, 0, 1) * np.clip((maximum - plane) / .05, 0, 1)
        layer = picture.copy()
        layer.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
        path = target / f"layer-{number}.png"
        layer.save(path)
        layers.append({"name": path.name, "sha256": sha256_file(path), "travel_px": travel})
    plan = {"image_sha256": image_receipt["sha256"], "layers": layers, "human_review_required": True}
    (target / "parallax.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def alpha_mask(image, image_receipt, weights, model_receipt, output):
    # rembg's default session can download weights. Override only the local model resolver.
    model = verified_local(weights, model_receipt, maximum_bytes=MAX_MODEL_BYTES)
    if model.suffix != ".onnx" or model_receipt.get("model_family") != "u2netp":
        raise ValueError("Reviewed local U2NetP ONNX is required.")
    source = verified_local(image, image_receipt, maximum_bytes=MAX_IMAGE_BYTES)
    output = _new_output(output)
    from rembg.sessions.u2netp import U2netpSession
    import onnxruntime as ort

    picture = _read_image(source)

    class LocalU2NetP(U2netpSession):
        @classmethod
        def download_models(cls, *args, **kwargs):
            return model

    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    LocalU2NetP("u2netp", options, ["CPUExecutionProvider"]).predict(picture)[0].save(output)
    return output


def reviewed_parallax(source, directory):
    """Resolve only the two local files from a plan for this exact original."""
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Expected a local parallax directory.")
    plan_file = directory / "parallax.json"
    if plan_file.stat().st_size > 8192:
        raise ValueError("Parallax plan is too large.")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if plan.get("image_sha256") != sha256_file(source) or plan.get("human_review_required") is not True:
        raise ValueError("Parallax assets must match the original scene image.")
    layers = plan.get("layers")
    if not isinstance(layers, list) or len(layers) != 2:
        raise ValueError("Expected two bounded depth layers.")
    resolved = []
    for number, entry in enumerate(layers, 1):
        name, travel = entry.get("name"), entry.get("travel_px")
        if name != f"layer-{number}.png" or type(travel) is not int or not 1 <= travel <= 10:
            raise ValueError("Invalid parallax plan entry.")
        layer = (directory / name).resolve(strict=True)
        if (layer.parent != directory or not layer.is_file() or layer.stat().st_size > MAX_IMAGE_BYTES
                or entry.get("sha256") != sha256_file(layer)):
            raise ValueError("Invalid parallax layer content or path.")
        resolved.append((layer, travel))
    return resolved
