# Frozen medium encoder-thread study

Preparation only: no exports or tests have run for this study. Python AST parsing and Node syntax checks passed. This small study asks whether 2 or 4 encoder threads per drawing worker reduce complete export delivery time compared with 8. There is no assumed gain or competitor claim.

Run after the active three-engine benchmark finishes, using a new result directory:

```sh
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/encoder-thread-study-v1/run.py --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/encoder-thread-study-v1/results/full-v1
```

Exactly 12 exports run sequentially: one excluded warmup for each thread count, followed by three timed rounds. Each thread count appears once in each timed position:

| Phase | First | Second | Third |
| --- | ---: | ---: | ---: |
| Warmup | 2 | 4 | 8 |
| Timed round 1 | 2 | 4 | 8 |
| Timed round 2 | 4 | 8 | 2 |
| Timed round 3 | 8 | 2 | 4 |

All runs import the same actual compiled candidate from `../paired-decode-export-v1/candidate/dist`, use its unchanged minimal package metadata and existing dependency resolution, and load exactly the same frozen TextGrid module and DM Sans font. Expected candidate/fixture hashes are embedded from the existing snapshot at preparation; the original snapshot, driver, worker, README, candidate diff and build receipt are also bound. No rebuild, installation, package/source edit, or writes to original export receipts occur. Missing or altered sources and a changed candidate file set stop launch.

Fixed settings: 300 frames, 3334 labels, 1920×1080 at 30 fps; 4 drawing workers; 75-frame chunks; medium preset; CRF 11; RGB-to-BT601; GOP 24; 3 B-frames; sceneCut true (existing encoder maps this to sc_threshold 40); qmin 15; qmax 60; qcompress 0.6; maxQdiff 4. Only existing `options.encoder.threads` changes between 2, 4, and 8. Full final count_frames verification uses the same compiled `min(8, availableParallelism())` decoder policy for every run; packet probing remains 1 thread.

Resource disclosure: the originating host has 11 available CPUs. Four simultaneous encoders request 8, 16, or 32 aggregate encoder threads at 2, 4, or 8 per worker respectively, in addition to drawing and other process work. These are configured thread counts, not measurements of actual CPU utilization. The runner records the host's availableParallelism and requires the compiled decoder budget to equal 8. Use the specified bundled Node binary and `/opt/homebrew/bin/ffmpeg` and `ffprobe`. Avoid overlapping benchmark jobs; this sequential driver does not control unrelated processes or concurrent study instances.

The primary timer is unchanged from the paired-export runner: Python `perf_counter_ns()` starts immediately before launching a fresh Node worker and stops when that process returns. It includes process startup, drawing, chunk encoding, assembly, internal full final verification, and component-stat writing. Config/composition preparation and source/output hashing are outside the timer. `component-stats.json` remains separate from external whole-process time. Each receipt preserves the original exit code, stdout/stderr, nanoseconds/milliseconds, composition hash, output size/hash, retained bytes, and source-integrity result. Per-round ratios compare 2 and 4 with 8 in that round; the manifest summarizes median ratios and each variant's median timed wall milliseconds. Warmups are excluded. Ratios below 1 favor the tested thread count; the small study cannot establish general workload gains.

Changing x264 encoder thread counts can change the encoded bitstream. Quality remains pending; differing output hashes are recorded and do not prove a regression or equivalence. No quality suite, competitor comparison, review framework, test harness, memory sampler, concurrency controller, or automatic watcher is included.

All MP4s under this study, including warmups, older study runs and failed partial outputs, count toward the 3 GiB retained-output budget. The runner refuses another launch at the limit and stops if a completed export crosses it; one in-flight export can exceed the limit. Existing result directories fail, there are no retries or cleanup, and failures preserve their current receipts and artifacts. Every export rechecks bound source hashes before launch and after process return. Source changes, launch/export failure, missing output/stats, and budget exhaustion stop the study. Interrupted or disk-full receipt writes may leave a `.tmp` evidence file; the runner does not overwrite that file. Runtime behavior remains unverified; preparation included syntax checks only.
