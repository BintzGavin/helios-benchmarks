#!/usr/bin/env python3
"""Fail-closed video structure/decode and optional per-engine quality gate.

Example:
  python validate_video.py result.mp4 --engine helios --scene vector_motion \
    --reference helios-reference.nut --reference-engine helios --output quality.json

Defaults: 1920x1080, 300 frames, 30 fps, exact PTS n/30 from zero. Use smaller
--width/--height/--frames fixtures for smoke tests. A reference must have matching
frame dimensions/count and caller-declared engine; it is paired by frame ordinal,
not its original timestamps. Known intrinsically lossless codecs are recognized;
otherwise --reference-lossless-attested is required (a caller assertion, not proof).

Both inputs are converted by FFmpeg to --metric-pixel-format (default yuv420p,
8-bit) with FFmpeg's default pixel-format conversion, without resizing or explicit
range/matrix/transfer overrides. This can subsample chroma or reduce bit depth.
No colorimetric equivalence, source-render accuracy, or cross-engine pixel identity
is asserted. Each engine needs its own lossless reference for a quality verdict.
A run without a reference can pass structure/decode only; quality is NOT evaluated.

Exit 0: requested checks passed; 1: validation failed; 2: invalid CLI arguments.
JSON and command stdout/stderr/metric logs are retained, including on failures.
Only the first video stream is evaluated. Requires FFmpeg/ffprobe on PATH.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

LOSSLESS_CODECS = {"ffv1", "rawvideo", "huffyuv", "ffvhuff", "utvideo", "png", "qtrle"}
COLOR_KEYS = ("pix_fmt", "color_range", "color_space", "color_transfer", "color_primaries", "chroma_location")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rational(value: Any) -> Fraction:
    """Reject absent, zero, negative, and malformed rates/time bases."""
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid positive rational: {value!r}") from exc
    if result <= 0:
        raise ValueError("rational must be positive")
    return result


def integer(value: Any) -> int:
    # Do not silently truncate floats or accept best-effort/rounded PTS strings.
    if isinstance(value, bool) or not re.fullmatch(r"[+-]?\d+", str(value)):
        raise ValueError(f"not an integer: {value!r}")
    return int(value)


def fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


class Recorder:
    def __init__(self, directory: Path, timeout: float):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.commands: list[dict[str, Any]] = []

    def run(self, label: str, command: list[str]) -> dict[str, Any]:
        record: dict[str, Any] = {"label": label, "argv": command,
            "shell_command_for_display": shlex.join(command), "cwd": str(self.directory),
            "started_at": utc_now(), "timeout_seconds": self.timeout}
        stdout = self.directory / f"{label}.stdout.txt"
        stderr = self.directory / f"{label}.stderr.txt"
        record.update(stdout_path=str(stdout), stderr_path=str(stderr))
        started = time.monotonic()
        try:
            with stdout.open("wb") as out, stderr.open("wb") as err:
                process = subprocess.run(command, cwd=self.directory, stdout=out, stderr=err,
                                         timeout=self.timeout, check=False)
            record["returncode"] = process.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            record.update(returncode=None, error=str(exc))
        record["elapsed_seconds"] = time.monotonic() - started
        self.commands.append(record)
        return record


def inspect_probe(probe: dict[str, Any], width: int, height: int, frames: int,
                  fps: Fraction, strict_timing: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    streams = probe.get("streams", [])
    actual_frames = probe.get("frames", [])
    if len(streams) != 1:
        errors.append(f"Expected exactly one selected video stream; got {len(streams)}")
    stream = streams[0] if streams else {}
    if (stream.get("width"), stream.get("height")) != (width, height):
        errors.append(f"Stream dimensions are {stream.get('width')}x{stream.get('height')}; expected {width}x{height}")
    if len(actual_frames) != frames:
        errors.append(f"Decoded frame count {len(actual_frames)} != expected {frames}")
    time_base: Fraction | None = None
    if strict_timing:
        try:
            time_base = rational(stream.get("time_base"))
        except (ValueError, ZeroDivisionError):
            errors.append("Missing or invalid stream time_base")
        for key in ("avg_frame_rate", "r_frame_rate"):
            try:
                if rational(stream.get(key)) != fps:
                    errors.append(f"{key}={stream.get(key)} != expected {fps}")
            except (ValueError, ZeroDivisionError):
                errors.append(f"Missing or invalid {key}")
    pts_audit = []
    for n, frame in enumerate(actual_frames):
        if (frame.get("width"), frame.get("height")) != (width, height):
            errors.append(f"Frame {n} dimensions differ from expected {width}x{height}")
        if strict_timing:
            try:
                pts = integer(frame.get("pts"))
                presentation = pts * time_base if time_base is not None else None
                expected = Fraction(n, 1) / fps
                pts_audit.append({"frame_zero_based": n, "pts": pts,
                                  "seconds_exact": str(presentation), "expected_seconds_exact": str(expected)})
                if presentation != expected:
                    errors.append(f"Frame {n}: PTS*time_base={presentation} != expected {expected}")
            except ValueError:
                errors.append(f"Frame {n}: missing or non-integer pts; best_effort_timestamp is not a substitute")
    return {"passed": not errors, "errors": errors, "decoded_frame_count": len(actual_frames),
            "stream": stream, "strict_timing": strict_timing, "pts_audit": pts_audit}


def probe_input(path: Path, label: str, args: argparse.Namespace, recorder: Recorder,
                strict_timing: bool = True) -> dict[str, Any]:
    command = [args.ffprobe, "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_frames",
               "-show_entries", "stream=codec_name,width,height,pix_fmt,time_base,avg_frame_rate,r_frame_rate,nb_frames,color_range,color_space,color_transfer,color_primaries,chroma_location:frame=pts,width,height",
               "-of", "json", str(path)]
    record = recorder.run(label + "_probe", command)
    errors = []
    if record["returncode"] != 0:
        errors.append(f"ffprobe failed: {record.get('error', record['returncode'])}")
    stderr = Path(record["stderr_path"])
    if stderr.exists() and stderr.read_text(errors="replace").strip():
        errors.append("ffprobe reported errors; see retained stderr")
    try:
        data = json.loads(Path(record["stdout_path"]).read_text())
        result = inspect_probe(data, args.width, args.height, args.frames, args.fps, strict_timing)
    except (OSError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        result = {"passed": False, "errors": [f"Invalid ffprobe JSON: {exc}"], "stream": {}}
    result["errors"].extend(errors)
    result["passed"] = not result["errors"]
    return result


def full_decode(path: Path, label: str, args: argparse.Namespace, recorder: Recorder) -> dict[str, Any]:
    # No -t or frame limit: decode the full selected stream and fail on decoder errors.
    command = [args.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror",
               "-err_detect", "explode", "-i", str(path), "-map", "0:v:0", "-an", "-sn", "-dn",
               "-fps_mode", "passthrough", "-f", "null", "-"]
    record = recorder.run(label + "_decode", command)
    stderr = Path(record["stderr_path"])
    reported_errors = stderr.exists() and bool(stderr.read_text(errors="replace").strip())
    passed = record["returncode"] == 0 and not reported_errors
    return {"passed": passed, "errors": [] if passed else ["Full decode failed or reported errors; see retained command and stderr"]}


def parse_metric_log(path: Path, expected_frames: int, keys: tuple[str, ...],
                     thresholds: dict[str, float]) -> dict[str, Any]:
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    minima: dict[str, float] = {key: math.inf for key in keys}
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return {"passed": False, "errors": [f"Missing metric log: {exc}"], "frames": []}
    for line in lines:
        fields = dict(re.findall(r"([A-Za-z_]+):([^\s]+)", line))
        if "n" not in fields:  # FFmpeg PSNR v2 header is not a frame.
            if line.startswith("psnr_log_version:") or not line.strip():
                continue
            errors.append(f"Unrecognized metric line: {line}")
            continue
        row: dict[str, Any] = {"raw": line}
        try:
            n = integer(fields["n"])
            row["frame_one_based"] = n
            if n != len(records) + 1:
                errors.append(f"Metric frame index {n} is not expected index {len(records) + 1}")
            for key in keys:
                value = float(fields[key])
                # +inf PSNR is the correct value for identical samples, NaN never passes.
                if math.isnan(value) or value == -math.inf:
                    errors.append(f"Frame {n}: invalid {key}={fields[key]}")
                elif value < thresholds[key]:
                    errors.append(f"Frame {n}: {key}={value} < {thresholds[key]}")
                if key == "Y" and (not math.isfinite(value) or value > 1):
                    errors.append(f"Frame {n}: invalid SSIM Y={fields[key]}")
                minima[key] = min(minima[key], value)
                row[key] = "inf" if value == math.inf else (None if not math.isfinite(value) else value)
        except (ValueError, KeyError) as exc:
            errors.append(f"Malformed metric line: {line} ({exc})")
        records.append(row)
    if len(records) != expected_frames:
        errors.append(f"Metric count {len(records)} != expected {expected_frames}")
    return {"passed": not errors, "errors": errors, "frame_count": len(records), "thresholds": thresholds,
            "minimum": {key: "inf" if value == math.inf else (None if not math.isfinite(value) else value) for key, value in minima.items()}, "frames": records}


def measure_quality(candidate: Path, reference: Path, args: argparse.Namespace,
                    recorder: Recorder) -> dict[str, Any]:
    time_base = Fraction(1, 1) / args.fps
    normalize = f"format=pix_fmts={args.metric_pixel_format},settb=expr={time_base},setpts=N"
    graph = (f"[0:v:0]{normalize},split=2[ds][dp];[1:v:0]{normalize},split=2[rs][rp];"
             "[ds][rs]ssim=stats_file=ssim.log:shortest=1:repeatlast=0:eof_action=endall[ss];"
             "[dp][rp]psnr=stats_file=psnr.log:stats_version=2:shortest=1:repeatlast=0:eof_action=endall[ps]")
    # Clear only this run's generated metric logs so failure cannot reuse old results.
    for name in ("ssim.log", "psnr.log"):
        (recorder.directory / name).unlink(missing_ok=True)
    command = [args.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror",
               "-err_detect", "explode", "-i", str(candidate), "-err_detect", "explode", "-i", str(reference),
               "-filter_complex_threads", "1", "-filter_complex", graph,
               "-map", "[ss]", "-map", "[ps]", "-an", "-sn", "-dn", "-fps_mode", "passthrough", "-f", "null", "-"]
    record = recorder.run("quality", command)
    ssim = parse_metric_log(recorder.directory / "ssim.log", args.frames, ("Y",), {"Y": args.ssim_y})
    psnr = parse_metric_log(recorder.directory / "psnr.log", args.frames, ("psnr_y", "psnr_u", "psnr_v"),
                            {"psnr_y": args.psnr_y, "psnr_u": args.psnr_uv, "psnr_v": args.psnr_uv})
    errors = []
    if record["returncode"] != 0 or Path(record["stderr_path"]).read_text(errors="replace").strip():
        errors.append("Metric FFmpeg command failed or reported errors; see retained stderr")
    return {"status": "evaluated", "passed": not errors and ssim["passed"] and psnr["passed"],
            "errors": errors, "ssim": ssim, "psnr": psnr, "filter_graph": graph,
            "metric_precision": "Thresholds apply to FFmpeg per-frame log values: SSIM 6 decimals, PSNR 2 decimals; near-threshold rounding is not independently resolved",
            "normalization": {"both_inputs": normalize, "pairing": "frame ordinal, zero based",
                "common_time_base": str(time_base), "common_pts": "N", "pixel_format": args.metric_pixel_format,
                "resize": "none", "color_conversion": "FFmpeg default pixel-format conversion; no explicit range/matrix/transfer override",
                "caveat": "Conversion may subsample chroma/reduce bit depth. This is per-engine reference fidelity, not cross-engine pixel identity or a colorimetric/source-render correctness test."}}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("candidate", type=Path)
    p.add_argument("--reference", type=Path)
    p.add_argument("--engine", default="unspecified")
    p.add_argument("--reference-engine")
    p.add_argument("--reference-lossless-attested", action="store_true",
                   help="Caller attests reference is lossless; needed for codecs not intrinsically lossless")
    p.add_argument("--scene", default="unspecified")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--frames", type=int, default=300)
    p.add_argument("--fps", type=rational, default=Fraction(30))
    p.add_argument("--ssim-y", type=float, default=0.995)
    p.add_argument("--psnr-y", type=float, default=40.0)
    p.add_argument("--psnr-uv", type=float, default=35.0)
    p.add_argument("--metric-pixel-format", choices=("yuv420p", "yuv422p", "yuv444p"), default="yuv420p")
    p.add_argument("--output", type=Path, help="JSON result; evidence logs go beside it in <stem>.evidence/")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--ffprobe", default="ffprobe")
    p.add_argument("--timeout", type=float, default=600.0, help="Per-command timeout, seconds")
    return p


def validate(args: argparse.Namespace) -> dict[str, Any]:
    candidate = args.candidate.resolve()
    reference = args.reference.resolve() if args.reference else None
    output = (args.output or candidate.with_suffix(".validation.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    recorder = Recorder(output.parent / (output.stem + ".evidence"), args.timeout)
    result: dict[str, Any] = {"schema_version": 1, "started_at": utc_now(), "engine": args.engine,
        "scene": args.scene, "expected": {"width": args.width, "height": args.height,
            "frames": args.frames, "fps": str(args.fps), "pts_seconds": "n/fps, n=0..frames-1"},
        "candidate": {"path": str(candidate)}, "reference": {"path": str(reference)} if reference else None,
        "quality": {"status": "not_evaluated", "passed": None, "reason": "No per-engine lossless reference supplied"},
        "scope": "First video stream only; audio/subtitles and cross-engine pixel identity are not assessed",
        "errors": [], "commands": recorder.commands, "passed": False}
    try:
        for binary, label in ((args.ffmpeg, "ffmpeg_version"), (args.ffprobe, "ffprobe_version")):
            version = recorder.run(label, [binary, "-version"])
            if version["returncode"] != 0:
                result["errors"].append(f"Cannot run {binary}")
        result["candidate"].update(fingerprint(candidate))
        candidate_probe = probe_input(candidate, "candidate", args, recorder)
        candidate_decode = full_decode(candidate, "candidate", args, recorder)
        result["candidate"].update(probe=candidate_probe, decode=candidate_decode)
        structural_pass = candidate_probe["passed"] and candidate_decode["passed"]
        if reference:
            result["quality"] = {"status": "blocked", "passed": False, "reason": "Reference prerequisites must pass"}
            result["reference"].update(fingerprint(reference), engine=args.reference_engine)
            ref_probe = probe_input(reference, "reference", args, recorder, strict_timing=False)
            ref_decode = full_decode(reference, "reference", args, recorder)
            result["reference"].update(probe=ref_probe, decode=ref_decode)
            codec = ref_probe.get("stream", {}).get("codec_name")
            lossless = codec in LOSSLESS_CODECS or args.reference_lossless_attested
            result["reference"]["lossless_provenance"] = {
                "codec": codec, "intrinsically_lossless_codec": codec in LOSSLESS_CODECS,
                "caller_attested": args.reference_lossless_attested,
                "caveat": "Neither codec nor attestation establishes the file was produced from this scene/engine or that its upstream source was lossless"}
            if not lossless:
                result["errors"].append("Reference is not an intrinsically lossless codec; explicit --reference-lossless-attested is required")
            if args.engine == "unspecified" or args.reference_engine != args.engine:
                result["errors"].append("Reference requires explicit matching --engine and --reference-engine; cross-engine references are rejected")
            if structural_pass and ref_probe["passed"] and ref_decode["passed"] and not result["errors"]:
                result["quality"] = measure_quality(candidate, reference, args, recorder)
                result["quality"]["input_color_metadata"] = {
                    "candidate": {key: candidate_probe["stream"].get(key) for key in COLOR_KEYS},
                    "reference": {key: ref_probe["stream"].get(key) for key in COLOR_KEYS}}
        result["structure_decode_passed"] = structural_pass
        result["quality_passed"] = result["quality"]["passed"]
        result["passed"] = structural_pass and not result["errors"] and (not reference or result["quality"]["passed"] is True)
        result["verdict"] = ("structure_and_quality_pass" if reference else "structure_only_pass") if result["passed"] else "fail"
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["verdict"] = "fail"
    result["finished_at"] = utc_now()
    result["output_path"] = str(output)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if min(args.width, args.height, args.frames) < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        p.error("width, height, frames, and timeout must be positive")
    if not all(math.isfinite(value) for value in (args.ssim_y, args.psnr_y, args.psnr_uv)):
        p.error("quality thresholds must be finite")
    if not 0 <= args.ssim_y <= 1 or min(args.psnr_y, args.psnr_uv) < 0:
        p.error("SSIM threshold must be in [0,1] and PSNR thresholds must be nonnegative")
    if args.metric_pixel_format == "yuv420p" and (args.width % 2 or args.height % 2):
        p.error("yuv420p metrics require even width and height")
    if args.metric_pixel_format == "yuv422p" and args.width % 2:
        p.error("yuv422p metrics require even width")
    if args.output and args.output.resolve() in {args.candidate.resolve(), args.reference.resolve() if args.reference else None}:
        p.error("output must not overwrite an input")
    result = validate(args)
    print(json.dumps({"verdict": result["verdict"], "passed": result["passed"],
                      "quality_status": result["quality"]["status"], "result": result["output_path"]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
