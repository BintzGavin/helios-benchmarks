# Linux Orb evidence verification

Package SHA256: `a524078edfebea024d4a5524b507ba1336af13ba0d6cb1ef321130d3576e618f`. Package bytes: 2,578,213. Primary holdout manifest SHA256: `e2a3af7c3c9ec342d40ba4e19aa24b4ecd0aef7a36e9833f009fa0e79084b62f`.

Independent receipt audit passed: 488 indexed included files; 18 timed exports, 6 excluded warmups; six unique delivered output hashes; 1,800 raw per-frame metric rows recomputed; exact 300-frame n/30 cadence; eight holdout Remotion software-stage receipts. Frozen settings precede holdout creation and qualification manifest hash matches. All encoder SEI settings match the requested presets, CRF11 and thread counts. Repair/full-decode costs are inside delivery.

| Preset | Engine | Round 1 ns | Round 2 ns | Round 3 ns | Median seconds |
|---|---|---:|---:|---:|---:|
| medium | H | 69156139448 | 69059951412 | 69426166154 | 69.156139448 |
| medium | F | 92045448392 | 91910993266 | 92201298828 | 92.045448392 |
| medium | R | 151413629799 | 152851689415 | 152316073808 | 152.316073808 |
| ultrafast | H | 21163641221 | 20704839205 | 20679705204 | 20.704839205 |
| ultrafast | F | 39733311374 | 39229473920 | 39251199575 | 39.251199575 |
| ultrafast | R | 60125442549 | 60012809861 | 59564471586 | 60.012809861 |

## Scope and limits

- Audit independently recomputes timers summaries, encoder receipt settings, frame cadence and quality minima from saved receipts; raw videos/references omitted from compact package, so no independent local re-decode or media hash recomputation.
- Original nanosecond duration counters preserved; absolute start/end monotonic counters not serialized.
- One a1.small machine, no timing tuning screen, H/F up to two one-thread encoders and Remotion one one-thread final encoder.
- Own lossless references establish per-engine fidelity, not cross-engine identical pixels.
- Compact archive precedes final full-tree index; 488 included indexed files match, embedded INDEX and SYMLINKS exclude later receipts.
- No paired Linux optimization study; no new Helios change speedup proven.

## Interpretation

Ratios of eligible medians: medium F/H 1.330980, R/H 2.202495; ultrafast F/H 1.895750, R/H 2.898492. These describe the frozen configuration on this two-logical-CPU Linux machine, not universally optimized engine throughput. The original M3 Pro study remains separate.

Original full remote evidence: `/home/user/evidence/helios-cpu-linux-2026-10-02`. Original full-tree final INDEX SHA256: `e41dae21878996104f9f167da3c37ccda9d3899bf11eafcb397ccaf8beca8631`. The compact package uses an earlier index snapshot.

Amp video review attachment was transformed from 142,217,777 to 50,985,101 bytes; it was excluded from hash/fidelity verification. No benchmarks, builds, exports or quality analysis were rerun remotely. No repository changes or publication occurred.

Nine compiled-module hashes in the fresh Linux manifest match the historical candidate receipt: canvas, canvas-pool, canvas-worker, render, process, skia-binding, text, plan, media. These are receipt bindings; the compact package does not include the full frozen native runtime.
