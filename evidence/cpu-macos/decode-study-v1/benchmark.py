"""Count decoded frames in fresh ffprobe processes; run only after exports finish."""
import argparse
import hashlib, json, shlex, statistics, subprocess, time
from decimal import Decimal
from pathlib import Path
STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parent
FFPROBE = "/opt/homebrew/bin/ffprobe"
PROFILES = ("medium", "ultrafast")
def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def metadata(data):
    videos = [s for s in data["streams"] if s.get("codec_type") == "video"]
    if len(videos) != 1:
        raise ValueError("expected exactly one video stream")
    video = videos[0]
    result = {key: video[key] for key in
              ("codec_name", "width", "height", "r_frame_rate", "nb_read_frames")}
    result["duration"] = format(Decimal(data["format"]["duration"]).normalize(), "f")
    expected = dict(codec_name="h264", width=1920, height=1080, r_frame_rate="30/1",
                    nb_read_frames="300", duration="10")
    if result != expected:
        raise ValueError("decoded metadata differs from expected: " + repr(result))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threads", type=int, choices=(1, 2, 4, 8))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, default=STUDY / "results" / "all-threads")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    if not Path(FFPROBE).is_file():
        parser.error("ffprobe is missing: " + FFPROBE)
    output = args.output.resolve()
    if not output.is_relative_to(STUDY) or output == STUDY:
        parser.error("--output must be a new directory inside decode-study-v1")
    inputs = {p: ROOT / "local-driver" / "results" / "baseline-v1" /
              (p + "-timed-1") / "output.mp4" for p in PROFILES}
    fingerprints = {}
    for profile, path in inputs.items():
        if not path.is_file() or path.stat().st_size == 0:
            parser.error("input is missing or empty: " + str(path))
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        fingerprints[profile] = dict(path=str(path), bytes=path.stat().st_size,
                                     sha256=digest.hexdigest())
    output.mkdir(parents=True, exist_ok=False)
    threads = [args.threads] if args.threads is not None else [1, 2, 4, 8]
    template = [FFPROBE, "-v", "error", "-threads", "{threads}", "-count_frames",
                "-show_streams", "-show_format", "-of", "json", "{input}"]
    save(output / "manifest.json", dict(inputs=fingerprints, rounds=args.rounds, threads=threads,
         command_template=template, timer="perf_counter_ns"))
    rows, stable, error = [], None, None
    for round_index in range(args.rounds):
        order = threads[round_index % len(threads):] + threads[:round_index % len(threads)]
        profiles = PROFILES if round_index % 2 == 0 else PROFILES[::-1]
        for count in order:
            for profile in profiles:
                name = "round-%d-%s-threads-%d" % (round_index + 1, profile, count)
                command = [str(count) if x == "{threads}" else
                           str(inputs[profile]) if x == "{input}" else x for x in template]
                start = time.perf_counter_ns()
                process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                elapsed = time.perf_counter_ns() - start
                (output / (name + ".stdout.json")).write_bytes(process.stdout)
                (output / (name + ".stderr.log")).write_bytes(process.stderr)
                row = dict(round=round_index + 1, profile=profile, threads=count,
                           command=command, command_shell=shlex.join(command),
                           elapsed_ns=elapsed, exit_code=process.returncode)
                try:
                    if process.returncode:
                        raise ValueError("ffprobe returned " + str(process.returncode))
                    row["metadata"] = metadata(json.loads(process.stdout))
                    if stable is not None and row["metadata"] != stable:
                        raise ValueError("decoded metadata changed between runs")
                    stable = row["metadata"]
                except (ValueError, KeyError, TypeError) as problem:
                    row["error"] = error = str(problem)
                save(output / (name + ".receipt.json"), row)
                rows.append(row)
                if error:
                    break
            if error:
                break
        if error:
            break
    medians = [dict(profile=p, threads=n, samples=len(values), median_seconds=
               statistics.median(values) / 1e9) for p in PROFILES for n in threads
               if (values := [r["elapsed_ns"] for r in rows if r["profile"] == p
                              and r["threads"] == n and "error" not in r])]
    save(output / "summary.json", dict(completed=error is None, error=error, medians=medians))
    print(output / "summary.json")
    return 1 if error else 0
if __name__ == "__main__":
    raise SystemExit(main())
