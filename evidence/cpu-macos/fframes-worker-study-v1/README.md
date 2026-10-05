# Prepared FFRAMES CPU medium worker-count study

Preparation only: no exports, CPU jobs, tests, or reviews have run. Python syntax parsing passed. This small study asks whether 4 or 6 drawing workers reduce delivered export time compared with 11, at medium/CRF11 and 2 encoder threads per segment. No winner, global optimum, or public superiority claim is assumed; previous worker-selection evidence is not established.

The lead will preflight and launch after the current three-engine benchmark and Helios encoder-thread study finish:

```sh
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-study-v1/run.py --run --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-study-v1/results/full-v1
```

Exactly 12 fresh, sequential, full 300-frame FFRAMES exports run. One excluded warmup per worker count precedes three timed rounds; each count occupies each timed position once:

| Phase | First | Second | Third |
| --- | ---: | ---: | ---: |
| Warmup | 4 | 6 | 11 |
| Timed round 1 | 4 | 6 | 11 |
| Timed round 2 | 6 | 11 | 4 |
| Timed round 3 | 11 | 4 | 6 |

The runner invokes the existing `../fframes-setup/cargo-target/release/helios-fframes-cpu-comparison` binary as `OUTPUT medium 11 WORKERS 2`. Its CPU backend and TextGrid remain unchanged: 3334 labels, 1920×1080, 300 frames, 30fps, 10 seconds, silent video, pinned DM Sans font, no system fonts. The pinned encoder defaults supply GOP24/B3/sc40/qmin15/qmax60/qcomp0.6/qdiff4. The existing three-engine helper validates actual x264 SEI after timing, including these defaults, 2 encoder threads, and medium's distinguishing parameters. No rebuild, install, source modification, extra Helios/Remotion export, historical rerun, or writes to existing receipts occur.

Resource disclosure: the originating host has 11 available CPUs. Pinned cpu.rs and segment_writer.rs open an encoder for each segment. FrameScheduler starts `min(workers, totalFrames/minSegmentFrames)` initial segments; this 300-frame/GOP24 workload starts 4, 6, or 11 for the tested counts. Two threads per encoder therefore request 8, 12, or 22 initial aggregate encoder threads alongside drawing and other work; this is not a global two-thread cap or measured utilization. Actual host metadata is recorded through the specified bundled Node. The Homebrew FFprobe full decode uses `min(8, availableParallelism())`, required to be 8. Avoid overlapping benchmarks; the runner does not impose CPU affinity or coordinate unrelated processes.

```text
perf_counter_ns start
  fresh FFRAMES process -> complete CPU export -> process receipt
  Homebrew FFprobe: 8-thread full count_frames -> process receipt
  validate raw probe completeness and format
perf_counter_ns stop
  header-only x264 SEI + output SHA/size + source/runtime hashes
```

This is the original three-engine delivered timer boundary: immediately before the engine-process helper through full probe completion and metadata validation. It includes process startup/exit and the same small helper receipt overhead. Nothing is subtracted. Engine process wall nanoseconds and full-decode process wall nanoseconds remain separate fields and original process receipts. The runner directly reuses `process`, `validate_probe`, and `encoder_info` from `../three-engine-v1/run.py`; importing that module does not execute its main. No medium edit-list repair, additional decode, quality suite, new benchmark framework, concurrency controller, sampler, or watcher is added.

Every attempt preserves engine/verify commands, original exit codes, stdout/stderr, raw FFprobe JSON, and process receipt nanoseconds. Validation requires exactly one silent video stream, H.264, yuv420p, 300 decoded frames, 1920×1080, avg/r fps30, duration10 seconds within 1/30 second, TV range and SMPTE170M color space. Timed round ratios compare 4 and 6 against 11 within that round; the manifest reports median round ratios and median delivered wall milliseconds per worker count. Warmups are excluded. Failed attempts do not become valid performance results.

Expected bindings are embedded in run.py from the existing binary, source defaults/backend/scheduler, main.rs, Cargo manifest/lock, setup receipt, font, shared x264165, Node, FFprobe, and reused helper. Own runner/README hashes join those bindings at launch. Hashing occurs outside delivered timers; pre/post-export drift stops the study. The setup receipt identifies upstream revision bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b. Installed transitive libraries beyond the named bindings are not exhaustively frozen; these hashes do not prove an immutable machine image or reproduce the original build.

All MP4s under this owned study directory, including warmups, older runs and failed partial outputs, count toward a 3 GiB retained-output budget. The runner reserves 256 MiB before each export. This is a launch reservation, not a write cap: one in-flight export can exceed the budget, after which the driver stops and preserves it. Logs and transient renderer scratch files are outside the retained-MP4 budget. Result directories must be new; there are no retries, resume, deletion, cleanup, or overwritten original receipts.

Failure modes addressed: missing/changed bindings, wrong upstream metadata/font, insufficient decoder budget, reused result paths, nonzero subprocess exit, missing/wrong full probe metadata, absent/mismatched SEI, source drift, and output-budget exhaustion. Launch/runtime remain unverified; preparation included Python syntax parsing only. Concurrent instances, disk-full recovery, exhaustive library pinning, all-frame quality, cadence/PTS audit and rasterization parity remain outside scope. Changing worker count changes segmentation and can change bitstreams; all-frame quality remains pending before any public best/superiority claim.
