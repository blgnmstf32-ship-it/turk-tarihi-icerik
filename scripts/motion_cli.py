"""Operator-only CLI for the optional motion toolkit. Tool advice never calls these commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import motion_atlas, motion_layers, motion_quality, motion_toolkit


def read_record(path):
    path = Path(path)
    if path.stat().st_size > 8_000_000:
        raise ValueError("JSON input is too large.")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object.")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="tool", required=True)
    spec = {
        "atlas": ("geojson", "receipt"),
        "depth": ("image", "receipt", "model", "output"),
        "parallax": ("image", "receipt", "depth", "depth_report", "output_dir"),
        "alpha": ("image", "receipt", "model", "model_receipt", "output"),
        "vmaf": ("reference", "encoded"),
        "denoise": ("audio", "model", "model_receipt", "output_dir"),
        "glb": ("source", "receipt", "output"),
    }
    commands = {}
    for tool, paths in spec.items():
        command = sub.add_parser(tool)
        commands[tool] = command
        for path in paths:
            command.add_argument(path, type=Path)
    commands["atlas"].add_argument("--year", required=True, type=int)
    commands["vmaf"].add_argument("--aligned", action="store_true")
    commands["denoise"].add_argument("--noise-confirmed", action="store_true")
    artwork = sub.add_parser("manim")
    artwork.add_argument("diagram", choices=list(motion_quality.DIAGRAMS))
    artwork.add_argument("output_dir", type=Path)
    catalogue = sub.add_parser("catalogue")
    catalogue.add_argument("kind", choices=["models", "textures", "hdris"])
    source = catalogue.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--live", action="store_true")
    guidance = sub.add_parser("guidance")
    guidance.add_argument("brand", choices=["tarih", "bakim"])
    guidance.add_argument("--role", type=int)
    args = parser.parse_args(argv)

    match args.tool:
        case "atlas":
            result = motion_atlas.read_atlas(args.geojson, args.receipt, args.year)
        case "depth":
            result = motion_layers.estimate_depth(args.image, read_record(args.receipt), args.model, args.output)
        case "parallax":
            result = motion_layers.prepare_parallax(args.image, read_record(args.receipt), args.depth,
                                                   read_record(args.depth_report), args.output_dir)
        case "alpha":
            result = {"mask": str(motion_layers.alpha_mask(args.image, read_record(args.receipt), args.model,
                                                           read_record(args.model_receipt), args.output))}
        case "vmaf":
            result = motion_quality.vmaf_report(args.reference, args.encoded, aligned=args.aligned)
        case "denoise":
            result = motion_quality.denoise_wav(args.audio, args.model, read_record(args.model_receipt),
                                                args.output_dir, noise_confirmed=args.noise_confirmed)
        case "glb":
            result = motion_quality.optimize_glb(args.source, read_record(args.receipt), args.output)
        case "manim":
            result = motion_quality.render_science_diagram(args.diagram, args.output_dir)
        case "catalogue":
            result = (motion_toolkit.load_poly_haven(args.kind, enabled=args.live) if args.live
                      else motion_toolkit.poly_haven_catalogue(read_record(args.file), kind=args.kind))
        case "guidance":
            result = motion_toolkit.role_guidance(args.brand, args.role)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
