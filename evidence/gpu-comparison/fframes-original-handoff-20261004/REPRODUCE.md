This is an excluded diagnostic package, not a benchmark timing result. All clocks produced with handoff capture enabled must remain excluded.

Frozen sources are in source.zip; BUILD-PINS.json identifies 164 source files and both release executables. The archive overlays the task's fframes base f89cbd572524b70a709ba3569fa23b0bbc8a0d9c. It retains the pre-existing matched scene and hardware fail-closed harness changes. It does not claim to recover the public benchmark author's uncommitted original scene. The review patch is relative to the retained circles/high-quality harness, not unmodified upstream.

For a new checkout, obtain the full fframes repository at that pinned base and overlay source.zip. Workspace components represented by symlinks in this executor come from that full checkout. Obtain svgr at 1c2a088217eb3365e965fd8dbd62acf265a07d33, preserving its matching usvgr and macro workspace. The archived Cargo.toml records this executor's absolute path overrides; substitute the new executor's svgr/crates/svgr and svgr/crates/usvgr paths and record that source change. Do not silently claim the original source hashes after substituting paths. Cargo.lock is unchanged and must remain locked. Official skia-safe/skia-bindings 0.153.3 and ffmpeg-sys-fframes 9.0.0 remain in use, with the existing codec/features. This is not a custom Skia ABI build.

On macOS arm64 with the required Metal/VideoToolbox capabilities:

```sh
cargo build --release --locked -p vs-remotion-bench \
  --bin circles-handoff-capture --bin handoff-color-controls
cargo test --release --locked -p fframes \
  --features h264,libav-agree-gpl,videotoolbox diagnostic_capture::tests
```

Use fresh absolute capture directories. Refusing an existing log is intentional:

```sh
FFRAMES_HANDOFF_CAPTURE=/absolute/new-controls/capture \
  target/release/handoff-color-controls \
  /absolute/new-controls/video.mp4 /absolute/new-controls/capture
FFRAMES_HANDOFF_CAPTURE=/absolute/new-circles/capture \
  target/release/circles-handoff-capture hardware \
  /absolute/new-circles/video.mp4 /absolute/pinned-font-directory 300 500000000
```

The font is DM Sans, SHA-256 9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5, with system fonts disabled. The scene remains 99,000 circles and 1,000 digits, nonuniform 1000×1000→3840×2160 scaling, source frames 3–302, 300 frames at 30/1, no audio. GOP30 and original MaxPerformance hardware frame negotiation are mandatory. A changed codec, conversion, concurrency or workload is a new lane.

Included Python scripts record process/resource receipts, independently audit all indexed events and compressed source frames, apply the fixed BT601 FFV1 proxy protocol and run the original prep validator. Their root directory is the task workspace; relocate them with the declared folder structure or explicitly record path substitutions. The validation source is included under preparation/ in the review bundle. No quality floor or conversion variant may be selected based on the candidate.

Compressed raw BGRA frames, complete candidate/reference videos and frozen executables are retained locally and SHA-bound in RECEIPT-MANIFEST.json. Large media/raw files are not duplicated in the review ZIP. No application-level or end-to-end zero-copy claim applies to this diagnostic capture. Its observed AVBuffer final-reference release is not an opaque encoder ownership trace.

Library source preparation ID libfile_19c903c1d7508191ac4881f0e96e4229 and historical checkpoint ID libfile_cd84375e4648819195364136245484c6 have distinct roles. Neither is a new publication of this result. Publication remains blocked; no new Library ID exists.
