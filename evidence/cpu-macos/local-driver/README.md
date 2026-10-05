# Fresh CPU baseline driver

No exports have been executed during preparation. Run only after the fframes build finishes.

`run.py --font /absolute/path/to/DM-Sans.ttf` defaults to one warmup and three timed fresh Node processes for medium, then ultrafast. `--timed 2` shortens the initial batch. Outputs and logs stay under a unique `local-driver/results/` directory; `--results` can choose a new directory inside `local-driver/`. Existing directories are rejected.

Each export retains `output.mp4`, `config.json`, `composition.mjs`, `component-stats.json`, `stdout.log`, `stderr.log`, and `process-result.json`. The batch `manifest.json` captures Python, OS, CPU count, Node, FFmpeg and FFprobe versions, and SHA-256 hashes of all portable dist JS, fixture, font, portable package metadata, driver files, and executables. Sources are checked before and after every export. This is a live-source baseline; freeze exact source copies before an A/B comparison.

```text
Python perf_counter_ns starts
  fresh Node worker
    import portable dist/canvas-pool.js
    renderCanvasModule -> existing chunk and final output checks
    write returned component stats
  Node exits -> Python records exit code and wall time
```

External wall time includes process startup, imports, rendering, output verification, and stats serialization. Returned renderer component stats are recorded separately and may overlap across workers; do not sum them into wall time. Warmups are labeled and retained, never mixed into timed samples automatically.

Both profiles use the existing 300-frame, 1920×1080, 30 fps, 3334-label fframes TextGrid fixture, CRF 11, RGB-to-BT601 conversion, GOP 24, qmin 15, qmax 60, qcompress 0.6, and maxQdiff 4. Medium uses four workers, eight encoder threads per worker, 75-frame chunks, three B-frames and scene cuts. Ultrafast uses six workers, four threads per worker, 50-frame chunks, zero B-frames and no scene cuts.

The default retained MP4 budget is 3 GiB. If a completed export exceeds the budget, retain it and stop further launches. Failed exports stop the batch with logs and process results preserved. No automatic retries, memory sampling, quality suite, source snapshots, historical reconstruction, or background watcher is included.
