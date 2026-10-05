# Native GPU implementation and qualification handoff

Durable root: `/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/native-gpu-evidence`.
The original `/private/tmp/helios-gpu-evidence` path is a symlink alias.

Implementation worktree: `/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios`.
Native helper: `packages/portable/native/target/release/helios-gpu`, SHA-256
`87aec3f3d39db8956490942429e6a865741c04515ad6b98753aaf6599c197a90`.
Do not rebuild or relabel frozen measurements without new binary/source bindings.

Implementation commit `5e0cc9c7ba29d6d30dbd2fadfe1e3dfbcc101872` was externally
merged via PR5009 as `5299bf7f9ad69f54c25b26b0b0774fbcc7d5f723`.
Current follow-up branch `gavin/fix-gpu-reference-color` carries the NV12 oracle
fix, independent red/green regression and measured documentation. No merge by
this task. No deployment or provisioning performed.

Read `FINAL-REPORT.json`, `FINAL-BUILD-PINS.json`, `RECEIPT-MANIFEST.json`,
`hardware-reference-direct-binding.json`, and repository
`packages/portable/benchmarks/GPU-RESULTS.md` first.

Four software pairs in AB/BA/BA/AB order qualify; native median26.197s versus
Chromium30.199s, every pair native faster. Hardware100Mbps median6.385s export,
7.955s including mandatory API decode; four separate180Mbps repeats retained
at8.811s median. All timed outputs/quality rows/PTS and original process clocks
retained. Do not pool hardware/software or bitrate sets.

The original `final-reference-hardware/reference.mkv` and its old quality
receipts are invalid. Raw-NV12 missing metadata caused FFmpeg to change pixels.
Corrected `final-reference-hardware-tagged/reference.mkv` exactly matches all
300 directly exported GPU NV12 frames after planar splitting, zero mismatches.
Original candidate exports/clocks are unchanged; corrected quality receipts are
`quality-corrected` for hardware rounds1-3 and `quality` for round4 and100Mbps.
Software rounds1-2 have strict PTS/color checks in `quality-strict`; rounds3-4
have them in `quality`. Every included gate passes. Screens20/40Mbps fail;
100/140Mbps pass. No screen/warmup/profile enters timing summaries.

Full300-frame independent interposer: no hooked pixel/IOSurface locks, texture
getBytes or texture-to-buffer downloads;300 actual conversions/callbacks on
oneIOSurface. Pointer queries/buffer accesses remain unknown-intent and opaque
driver/encoder transfers remain unknown. `zeroCopyProved=false`. Both positive
controls detect intentionally read NV12/RGBA. Actual Metal capture resources and
Chromium Graphite/readback trace are retained separately, excluded from timing.

Skia dependency: official crates0.91.0, milestone143, successful official
prebuilt URL in FINAL-BUILD-PINS; Cargo cache `/private/tmp/helios-gpu-cargo`.
This is not ABI evidence for fframes current upstreamSkia0.153.3 or old custom
fork0.91.0. Do not synchronize dependency versions manually.

Supported macOSarm64 Metal/H264 only. HEVC,Vulkan,Intel,Windows,GPUmedia,broad
Canvas paths/circles/99k public-API scene and remote hosts unsupported. Public
frame-returning API and software/reference paths explicitly read pixels back.
Existing CPU backends remain selectable. Full suite202 passed; final14 focused
GPU/reference tests passed after oracle fix; fault-device/encoder checks pass.

Originating chat01a0ff86-ddbd-7703-92b8-781e18082039 owns the full same-host
Helios/fframes/Remotion comparison and separate4K99k-circle claim. It is actively
building task-owned adapters; original fframes failed build retained, current
upstream supportedSkia release build succeeded. Report back with final follow-up
PR URL and receipt paths. Follow the authorized hourly heartbeat through full
comparison completion; pause it only when its entire saved objective is done.
No claim of beating the separate upstreamM5Max4Ksingle-run benchmark exists yet.
