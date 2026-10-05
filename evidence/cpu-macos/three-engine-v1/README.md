# Prepared three-engine CPU TextGrid timer

Preparation only. No browser, export, build, benchmark, test, quality check, or watcher has run for this harness. No repository files changed. Existing assemblies are reused; assembly and binding are outside all delivered timers.

After the lead approves execution and confirms competing exports have finished:

```sh
/usr/bin/python3 /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/three-engine-v1/run.py --run --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/three-engine-v1/results/full-v1
```

The result directory must be new. A failed run is preserved and never resumed or overwritten. Choose a new suffix for a later authorized study. There is no automatic launch or watcher.

```text
run.py (fresh sequential subprocesses; perf_counter_ns)
  H -> worker.mjs -> frozen canvas-pool -> internal full decode
  F -> existing CPU binary -> UL edit-list repair -> full decode
  R -> worker.mjs -> existing bundle/browser -> full decode
stop delivered timer
  output SHA/size + x264 user SEI + source/runtime hash checks
```

One warmup per engine/preset precedes three timed rounds. Orders are H/F/R, F/R/H, R/H/F for each preset. Warmups and timed outputs are retained. Delivered wall time includes process startup/exit, complete export, actual repair when needed, and the required full decode. Raw components are separately measured: subprocess walls; H API statistics; R browser open/select/render/close; F upstream renderSeconds. H component statistics overlap and must not be summed. Nothing is subtracted from delivered time. If any phase fails, its actual attempt duration and logs are recorded without a valid performance result.

| Preset | Helios workers/encoder threads | fframes workers/encoder threads | Remotion workers/encoder threads |
| --- | --- | --- | --- |
| medium | 4 / 8 | 11 / 2 | 4 / 8 |
| ultrafast | 6 / 4 | 6 / 2 | 4 / 1 |

These are provisional tuned profiles provided by the lead. They do not establish historical tuning or a global optimum. All exports run sequentially on the same whole-host CPU allocation; differing concurrency/encoder-thread counts are disclosed and are not equal per-engine thread caps. The harness does not enforce CPU affinity or prevent unrelated host work.

Workload: upstream revision bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b; original 3,334 labels, 1920x1080, 300 frames, 30fps, 10s. Pinned DM Sans SHA256: 9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5. H uses the actual compiled paired-decode candidate; F uses the existing release CPU binary. F's codec_params specify crf/preset/threads; its pinned renderer/encoder.rs defaults and renderer/stream.rs color behavior supply GOP24, qmin15/qmax60/qcomp0.6/qdiff4, BT.601 limited yuv420p. Medium B3/sc40 and ultrafast B0/sc0 are checked from x264 SEI rather than assumed from CLI labels.

R directly imports the installed 4.0.529 renderer via createRequire, uses selectComposition/renderMedia and closes the browser in finally. Existing Chrome Headless Shell runs with gl swangle (ANGLE SwiftShader software GL), hardwareAcceleration disable, PNG screenshots, no audio, frames 0..299. The installed source supports binariesDirectory: compositor/get-executable-path.js chooses exact filenames remotion/ffmpeg/ffprobe. At launch the driver stages symlinks to the existing Remotion compositor/libraries and the same Homebrew ffmpeg/ffprobe paths used by H. ffmpegOverride records every original type's final argv, sets actual encoder threads/BF/sc/quantizer bounds and explicit BT.601 limited conversion only for encoding steps; a later copy stitch retains the pre-encode.

H already verifies its final output with min(8, availableParallelism()) decoder threads. F/R use an external ffprobe count_frames full decode with the same eight threads inside delivered timing; require 300 decoded frames, dimensions, H.264, yuv420p, 30fps and 10s. F ultrafast retains original.mp4 and uses the exact ignore_editlist 1 / video copy / use_editlist 0 workaround inside delivered timing. H's API checks completeness internally; its stats expose finalVerifyMs rather than returning the decoded probe JSON. H color/pixel format are configured explicitly but are not redundantly decoded. x264 SEI is read from at most the first 2MiB after timing; actual quantizer, GOP, B-frame, scenecut, thread and distinguishing preset parameters are checked. A missing or mismatched SEI fails the study. No memory sampling or extra full decode occurs.

The driver binds source/harness/runtime binaries, H dist/src/native canvas, R renderer dist/bundle/project/lock, browser executable, F harness/defaults and upstream source metadata. It records host CPU counts/model, tool versions, outputs' SHA/size, exact commands, stdout/stderr/exit code and nanosecond wall times. Installed transitive libraries beyond the specified bindings are not exhaustively frozen; the lock file records package resolution, not an immutable machine image. F's libav build differs from CLI FFmpeg even though the lead established FFmpeg 9.0.2 / shared x264165 linkage; files/versions are recorded, not proof of identical implementations.

Retained MP4 budget is 6GiB across this owned directory, with a conservative 512MiB reservation before each export. There is no per-file write limit. If retained output exceeds the total budget, the driver stops and preserves artifacts. Small logs/configs and transient renderer scratch files are outside the retained MP4 budget. No deletion, retry, subprocess polling, memory sampler, or background process is added.

Failure modes in scope: invalid/mutated fixture or source, unsupported runtime shape, wrong geometry/codec/frame count/color, nonzero subprocess exit, repair failure, missing encoder metadata, source drift, reused result paths and output-size limits. No retry/resume policy, concurrent study coordination, host affinity, quality metric, full frame cadence/PTS audit, rasterization parity, or old-client compatibility work is included. Rendering differs (Skia Canvas, tiny-skia SVG, Chromium DOM), and chroma/rasterization are not pixel-identical. PNG CRF11 is this controlled CPU/codec comparison; the published JPEG CRF18 reproduction is separate and not planned here. Quality and complete cadence must be assessed only after the performance phase, before making claims.
