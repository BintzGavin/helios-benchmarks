# Prepared Remotion CPU JPEG study

Preparation only. Syntax, browser launch, runtime GPU evidence, exports, and quality
are unverified. The lead runs preflight and launches after the existing studies
finish sequentially. This study is separate from `three-engine-v1`'s PNG/swangle
measurements and does not change or replace their receipts.

The pinned TextGrid workload is 3,334 DOM text labels, 1920×1080, 300 frames at
30 fps (10 seconds), using the existing source, font, bundle, Remotion 4.0.529,
and Chrome executable identified in `../remotion-setup/ready.json` and its source
manifest. Runtime/library hashes reuse the existing study's bindings, with
fresh bindings for this study's four files. No rebuilds or downloads are needed.
The existing `../three-engine-v1/results/full-v1/binaries` symlinks are required;
missing or mismatched links fail preparation at launch rather than being created.

| Key | Configuration | JPEG quality | Renderer workers |
| --- | --- | ---: | ---: |
| A | jpeg80-c6 | 80 | 6 |
| B | jpeg100-c6 | 100 | 6 |
| C | jpeg100-c11 | 100 | 11 |

JPEG quality 80 is the installed upstream video default; JPEG quality 100 is a
quality candidate. Neither establishes final encoded quality equivalence.
Every configuration uses shared pinned Homebrew software libx264, medium, CRF
11, eight encoder threads, GOP 24, B-frames 3, scene cut 40, qmin 15, qmax 60,
qcomp 0.6, qdiff 4, yuv420p, and BT.601 TV-range conversion/signaling. The
FFmpeg override preserves supplied arguments and inserts encoder controls before
the final filename; a stitch-copy command remains a remux without re-encoding.

The schedule is one excluded warmup for A, B, C, followed by three balanced
timed rounds: **ABC → BCA → CAB**. This is 12 exports total, with three timed
samples per configuration. Each export starts a fresh Node process, with no
browser or rendering preamble outside its delivery timer.

`chrome-cpu.sh` execs the absolute pinned browser, preserves every original
argument, and appends `--disable-gpu --disable-gpu-compositing
--disable-gpu-rasterization` last. The worker retains the existing swangle GL
selection. Browser-level CDP queries occur after browser opening and before any
export. Admission requires all three exact flags plus nonempty
`gpu_compositing` and `rasterization` statuses containing `software`, `disabled`,
or `unavailable` (case insensitive). Missing evidence or an enabled/unknown
required-stage status fails before rendering. Other selected feature statuses
and `glRenderer`/`glVendor` are recorded as evidence only. Unused capabilities
and GPU enumeration/context names do not establish GPU work for this DOM scene.
This bounded CPU qualification covers explicit GPU/raster/compositor flags and
runtime DOM-stage evidence; it does not assert every Chromium capability is
disabled. Software libx264 encoding is separately enforced.

Flag source: [Chromium content switches](https://chromium.googlesource.com/chromium/chromium/%2B/HEAD/content/public/common/content_switches.cc).
Hardware-stage status is unverified until the actual run. Receipts omit raw
browser argv, profile details, GPU device lists, and unfiltered auxiliary data;
only expected GPU flags, the static selected feature keys, and the two selected
GL attributes are persisted. GPU evidence is retained even on admission failure.

The primary `perf_counter_ns` delivery interval encloses the fresh worker process
(including browser opening, queries, selection, rendering, encoding, and cleanup)
and one external full `ffprobe -threads 8 -count_frames` decode. It also checks
300 frames, H264, silent video, dimensions, both frame rates, duration, yuv420p,
and BT.601 TV signaling. There is no duplicate internal full probe. Separate
`processNs` and `decodeNs` remain in each record; JSON receipts, output/source
hashes, and the bounded x264 SEI check are saved/read after delivery timing.
Stdout/stderr are streamed to per-attempt files. Worker details are written in
its `finally`, including failure and cleanup details. Progress samples are
limited to rendered-frame milestones 1/50/100/150/200/250/300, when emitted;
Remotion's timing fields overlap encoding and do not establish pure capture cost.

The retained MP4 budget is **3 GiB across this study**, with a 256 MiB reservation
before each export and a budget check after it. Reservation is not a per-file
write limit. A failed or oversized attempt is retained, stops the schedule, and
is never retried or overwritten. Each results directory must be fresh.

After lead preflight and completion of the existing studies, the launch command is:

```sh
/usr/bin/python3 '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/remotion-cpu-jpeg-study-v1/run.py' --run --results '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/remotion-cpu-jpeg-study-v1/results/full-v1'
```

Final encoded quality must be compared against a **lossless PNG source reference
captured with the same strict CPU browser**, not a JPEG master. Reference capture
and qualification are subsequent work, outside these 12 exports. Do not claim
quality equivalence, throughput superiority, or complete cadence until every
frame and cadence qualifies.
