# Frozen paired decoder-thread export driver

Preparation only: no exports have run. One authorized TypeScript build wrote only candidate/dist; build-result.json records exit 0, unchanged source hashes, and unchanged repo/dist hashes. The baseline copies all 19 portable dist JS files, the unmodified TextGrid fixture and pinned DM Sans font. `snapshot.json` binds exact copied bytes to original paths/hashes, the original package hash, copied unchanged local worker, and opaque repo/node_modules symlink. Minimal package metadata supplies only `type: module`. No dependencies are installed or copied.

Launch only after selecting a measured decoder thread count and reviewing this driver:

```sh
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/run.py --decode-threads 8 --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/results/full-v1
```

The required decode-threads receipt parameter is 8. The candidate is the actual TypeScript output frozen in candidate/dist. At launch the driver requires the exact compiled policy once and checks that the Node host’s availableParallelism produces the requested budget. The only changed JS file is render.js; its exact import and argv diff is saved as candidate.diff:

```diff
- '-threads', '1', packets ? '-count_packets' : '-count_frames'
+ '-threads', packets ? '1' : String(Math.min(8, availableParallelism())), packets ? '-count_packets' : '-count_frames'
```

The full count_frames verification stays enabled. All 18 other dist JS files and minimal package metadata have identical hashes. Candidate declarations are also retained and bound in snapshot.json. Candidate N=8 matches the lead's new source decoder cap on the 11-CPU host; this experiment uses the frozen baseline and compiled candidate; the build preserved repo/dist.

Defaults: one excluded warmup per variant/profile, then three timed pairs/profile with AB, BA, AB ordering. A=baseline; B=candidate. Profiles run medium then ultrafast. Root-only trial overrides: `--warmups 0 --pairs 1` with a distinct results directory. Existing results directories fail; there are no retries.

Both profiles preserve 300 frames, 3334 labels, 1920×1080 at 30 fps, CRF 11, RGB-to-BT601, GOP 24, qmin 15, qmax 60, qcompress 0.6, maxQdiff 4. Medium uses 4 workers/8 encoder threads/75-frame chunks/3 B-frames/scene cuts. Ultrafast uses 6 workers/4 encoder threads/50-frame chunks/0 B-frames/no scene cuts. FFmpeg and FFprobe are /opt/homebrew/bin tools; Node uses the specified bundled runtime.

Each process receipt retains original exit code, stdout/stderr logs, external perf_counter_ns wall time, source/composition hashes, output SHA-256/size, and existing component-stats.json. Output hashing and retained-byte accounting happen after the external timer stops. Each pair saves both process receipts and its candidate/baseline wall ratio; manifest summary reports the median paired ratio per profile. Ratios below 1 favor candidate. Component stats remain separate from process wall time.

Sources are bound before launch and checked after every export. Missing inputs, unexpected source shape, source changes, launcher/export failures, missing stats/output, and exhausted budget stop the study with existing evidence preserved. All MP4s under this driver count toward the 4 GiB budget, including warmups and failed partial outputs; an output exceeding the budget is retained and further launches stop. A single in-flight export can cross the limit before its receipt is saved. Concurrent independent study launches are outside this sequential driver's scope. No quality suite, tests, migration, review framework, or watcher is included. Build stdout/stderr and original TS/config/compiler hashes are retained outside the repo.
