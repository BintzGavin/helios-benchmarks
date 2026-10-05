"""Pure unit tests plus tiny CPU FFmpeg smoke tests; no GPU/1080p render needed."""
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import validate_video as gate


class ProbeTests(unittest.TestCase):
    def fixture(self, time_base="1/15360", step=512, count=4):
        return {"streams": [{"width": 64, "height": 48, "time_base": time_base,
                              "r_frame_rate": "30/1", "avg_frame_rate": "30/1"}],
                "frames": [{"pts": n * step, "width": 64, "height": 48} for n in range(count)]}

    def inspect(self, data):
        return gate.inspect_probe(data, 64, 48, 4, Fraction(30))

    def test_invalid_rationals_are_argument_errors(self):
        for value in ("1/0", "0/0", "0", "-1", "nan", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.rational(value)

    def test_exact_common_time_bases(self):
        for base, step in [("1/30", 1), ("1/15360", 512), ("1/90000", 3000), ("1001/30000", 0)]:
            with self.subTest(base=base):
                self.assertEqual(self.inspect(self.fixture(base, step))["passed"], step != 0)

    def test_rounded_decimal_timestamps_do_not_substitute_for_pts(self):
        data = self.fixture()
        del data["frames"][1]["pts"]
        data["frames"][1].update(pts_time="0.033333", best_effort_timestamp=512)
        self.assertFalse(self.inspect(data)["passed"])

    def test_pts_noninteger_and_offset_and_duplicate_and_gap(self):
        for pts in ("512.0", 513, 0, 1024, None):
            with self.subTest(pts=pts):
                data = self.fixture()
                data["frames"][1]["pts"] = pts
                self.assertFalse(self.inspect(data)["passed"])
        data = self.fixture()
        for frame in data["frames"]:
            frame["pts"] += 512
        self.assertFalse(self.inspect(data)["passed"])

    def test_dimensions_count_and_rates(self):
        for path, value in (("width", 65), ("height", 49), ("r_frame_rate", "30000/1001"),
                            ("avg_frame_rate", "0/0"), ("time_base", None)):
            with self.subTest(path=path):
                data = self.fixture()
                data["streams"][0][path] = value
                self.assertFalse(self.inspect(data)["passed"])
        data = self.fixture(count=3)
        self.assertFalse(self.inspect(data)["passed"])
        data = self.fixture()
        data["frames"][2]["width"] = 32
        self.assertFalse(self.inspect(data)["passed"])

    def test_rational_fractional_rate(self):
        data = self.fixture("1/30000", 1001)
        data["streams"][0].update(r_frame_rate="30000/1001", avg_frame_rate="30000/1001")
        self.assertTrue(gate.inspect_probe(data, 64, 48, 4, Fraction(30000, 1001))["passed"])

    def test_reference_ordinal_pairing_not_reference_timestamps(self):
        data = self.fixture("1/1000", 33)
        data["streams"][0]["avg_frame_rate"] = "0/0"
        self.assertFalse(self.inspect(data)["passed"])
        self.assertTrue(gate.inspect_probe(data, 64, 48, 4, Fraction(30), False)["passed"])


class MetricTests(unittest.TestCase):
    def parse(self, content, count=2, psnr=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.log"
            path.write_text(content)
            if psnr:
                return gate.parse_metric_log(path, count, ("psnr_y", "psnr_u", "psnr_v"),
                    {"psnr_y": 40.0, "psnr_u": 35.0, "psnr_v": 35.0})
            return gate.parse_metric_log(path, count, ("Y",), {"Y": 0.995})

    def test_every_frame_ssim_not_average(self):
        self.assertTrue(self.parse("n:1 Y:1.000000\nn:2 Y:0.995000\n")["passed"])
        self.assertFalse(self.parse("n:1 Y:1.000000\nn:2 Y:0.994999\n")["passed"])

    def test_all_psnr_channels_and_infinity(self):
        good = "n:1 psnr_y:inf psnr_u:inf psnr_v:inf\nn:2 psnr_y:40.00 psnr_u:35.00 psnr_v:35.00\n"
        self.assertTrue(self.parse(good, psnr=True)["passed"])
        for key, below in (("psnr_y:40.00", "psnr_y:39.99"), ("psnr_u:35.00", "psnr_u:34.99"),
                           ("psnr_v:35.00", "psnr_v:34.99")):
            self.assertFalse(self.parse(good.replace(key, below), psnr=True)["passed"])

    def test_missing_duplicate_out_of_order_or_extra_frames_fail(self):
        for content in ("n:1 Y:1\n", "n:1 Y:1\nn:1 Y:1\n", "n:2 Y:1\nn:1 Y:1\n",
                        "n:1 Y:1\nn:2 Y:1\nn:3 Y:1\n"):
            self.assertFalse(self.parse(content)["passed"])

    def test_invalid_metric_values_fail_and_serialize(self):
        for value in ("nan", "-inf", "inf", "garbage", "1.1"):
            result = self.parse(f"n:1 Y:{value}\nn:2 Y:1.000000\n")
            self.assertFalse(result["passed"])
            json.dumps(result, allow_nan=False)
        self.assertFalse(self.parse("n:1 U:1\nn:2 Y:1\n")["passed"])

    def test_psnr_header_allowed_other_garbage_rejected(self):
        good = "psnr_log_version:2 fields:n,mse_avg,psnr_y,psnr_u,psnr_v\nn:1 psnr_y:inf psnr_u:inf psnr_v:inf\n"
        self.assertTrue(self.parse(good, count=1, psnr=True)["passed"])
        self.assertFalse(self.parse(good + "broken log\n", count=1, psnr=True)["passed"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and ffprobe required")
class FFmpegSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="video-gate-tests-")
        cls.root = Path(cls.tmp.name)
        cls.ref = cls.root / "reference.nut"
        cls.black = cls.root / "black.nut"
        cls.short = cls.root / "short.nut"
        cls.rounded = cls.root / "rounded.mkv"
        cls.mp4 = cls.root / "candidate.mp4"
        for path, source, frames in ((cls.ref, "testsrc2=size=64x48:rate=30", 6),
                                     (cls.black, "color=black:size=64x48:rate=30", 6),
                                     (cls.short, "testsrc2=size=64x48:rate=30", 5),
                                     (cls.rounded, "testsrc2=size=64x48:rate=30", 6)):
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", source,
                            "-frames:v", str(frames), "-c:v", "ffv1", str(path)], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(cls.ref),
                        "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(cls.mp4)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_gate(self, candidate=None, reference=None, extra=()):
        name = self.id().rsplit(".", 1)[-1]
        output = self.root / (name + ".json")
        argv = [str(candidate or self.ref), "--width", "64", "--height", "48", "--frames", "6",
                "--engine", "fixture", "--scene", "testsrc2", "--output", str(output)]
        if reference:
            argv.extend(["--reference", str(reference), "--reference-engine", "fixture"])
        args = gate.parser().parse_args(argv + list(extra))
        result = gate.validate(args)
        self.assertEqual(result, json.loads(output.read_text()))
        for record in result["commands"]:
            self.assertTrue(Path(record["stdout_path"]).exists())
            self.assertTrue(Path(record["stderr_path"]).exists())
        return result

    def test_structure_only_is_not_quality_pass(self):
        result = self.run_gate()
        self.assertTrue(result["passed"])
        self.assertEqual(result["verdict"], "structure_only_pass")
        self.assertIsNone(result["quality_passed"])
        self.assertEqual(result["quality"]["status"], "not_evaluated")

    def test_lossless_mp4_against_own_reference(self):
        result = self.run_gate(self.mp4, self.ref)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["quality"]["ssim"]["minimum"]["Y"], 1.0)
        self.assertEqual(result["quality"]["psnr"]["minimum"]["psnr_y"], "inf")
        self.assertIn("settb=expr=1/30,setpts=N", result["quality"]["filter_graph"])
        self.assertEqual(result["quality"]["ssim"]["frame_count"], 6)
        self.assertEqual(result["quality"]["psnr"]["frame_count"], 6)

    def test_quality_degradation_fails(self):
        result = self.run_gate(self.black, self.ref)
        self.assertTrue(result["structure_decode_passed"])
        self.assertFalse(result["passed"])
        self.assertFalse(result["quality_passed"])

    def test_reference_wrong_count_blocks_metrics(self):
        result = self.run_gate(reference=self.short)
        self.assertFalse(result["passed"])
        self.assertEqual(result["quality"]["status"], "blocked")
        self.assertFalse(any(command["label"] == "quality" for command in result["commands"]))

    def test_cross_engine_references_rejected(self):
        result = self.run_gate(reference=self.ref, extra=("--reference-engine", "other_engine"))
        self.assertFalse(result["passed"])
        self.assertIn("cross-engine", " ".join(result["errors"]))

    def test_unknown_lossless_provenance_requires_attestation(self):
        result = self.run_gate(reference=self.mp4)
        self.assertFalse(result["passed"])
        self.assertIn("attested", " ".join(result["errors"]))
        result = self.run_gate(reference=self.mp4, extra=("--reference-lossless-attested",))
        self.assertTrue(result["passed"])
        self.assertTrue(result["reference"]["lossless_provenance"]["caller_attested"])

    def test_millisecond_rounded_timestamps_fail(self):
        result = self.run_gate(self.rounded)
        self.assertFalse(result["passed"])
        self.assertTrue(any("PTS*time_base" in error for error in result["candidate"]["probe"]["errors"]))

    def test_corrupt_input_fails_and_retains_errors(self):
        bad = self.root / "broken.mp4"
        bad.write_bytes(b"not a video")
        result = self.run_gate(bad)
        self.assertFalse(result["passed"])
        self.assertFalse(result["candidate"]["decode"]["passed"])
        self.assertTrue(result["candidate"]["probe"]["errors"])

    def test_missing_binary_fails_and_retains_json(self):
        result = self.run_gate(extra=("--ffmpeg", str(self.root / "nonexistent-ffmpeg")))
        self.assertFalse(result["passed"])
        self.assertTrue(result["errors"])
        self.assertTrue(any("error" in command for command in result["commands"]))

    def test_cli_exit_codes_and_output_protection(self):
        self.assertEqual(gate.main([str(self.ref), "--width", "64", "--height", "48", "--frames", "6",
                                   "--output", str(self.root / "cli.json")]), 0)
        self.assertEqual(gate.main([str(self.ref), "--width", "64", "--height", "48", "--frames", "7",
                                   "--output", str(self.root / "cli-fail.json")]), 1)
        with self.assertRaises(SystemExit) as context:
            gate.main([str(self.ref), "--output", str(self.ref)])
        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
