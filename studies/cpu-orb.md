# Linux CPU benchmark on an Amp Orb

One private a1.small Orb ran the Linux counterpart. This is a CPU-only study, not Orb GPU acceleration. Intel Xeon 2.60GHz, one physical core / two logical CPUs, 3 GiB workload memory cap, Debian 12, x86_64. H/F use up to two single-thread encoders; Remotion uses one single-thread final encoder. Each preset has one excluded warmup and three balanced timed rounds per engine.

| Preset | H median ns | F median ns | R median ns | F/H | R/H |
| --- | ---: | ---: | ---: | ---: | ---: |
| Medium | 69156139448 | 92045448392 | 152316073808 | 1.330980 | 2.202495 |
| Ultrafast | 20704839205 | 39251199575 | 60012809861 | 1.895750 | 2.898492 |

[Independent receipt audit](../evidence/cpu-orb-delivery/linux-evidence-verification.md) verified 488 indexed included files, 18 timed exports, six excluded warmups, all 1,800 saved per-frame metric rows, exact 300-frame n/30 cadence, encoder SEI settings, repair/full-decode costs and software-stage admission. [Machine-readable audit](../evidence/cpu-orb-delivery/linux-evidence-verification.json).

The compact archive is **2,578,213 bytes**, SHA-256 `a524078edfebea024d4a5524b507ba1336af13ba0d6cb1ef321130d3576e618f`; primary holdout manifest `e2a3af7c3c9ec342d40ba4e19aa24b4ecd0aef7a36e9833f009fa0e79084b62f`. All transferred receipts are preserved under `evidence/cpu-orb/`, including scripts, settings, setup failures, metrics and the original full-tree index.

Helios merge `ebf8e145538d454479d80f97f8f76893b2fdf96f` and tested head `0566d1108f922ea88294d4bbe1f11cdb49849834` share portable tree `bba6de4d9bfde1df81c37f4c1a9199978dc1047c` (115 files). fframes `bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b`, Remotion 4.0.529, Chrome 149.0.7790.0, Node 24.19.0, Rust/Cargo 1.90.0. H/R use FFmpeg 5.1.9/x264 core164; fframes uses vendored FFmpeg9 and the same x264 core164. These versions differ from the M3 Pro study.

Medium encoding dominated; under ultrafast native/browser rasterization dominated. No paired Linux decoder-optimization study was run and no new Linux speedup from that change is proven.

## Transfer limits

Original raw videos/references remain at `/home/user/evidence/helios-cpu-linux-2026-10-02` on the original Orb. Full-tree final INDEX SHA-256 `e41dae21878996104f9f167da3c37ccda9d3899bf11eafcb397ccaf8beca8631`; the compact archive uses an earlier index. Absolute monotonic start/end counters were not serialized. The compact package omits raw media, so the local audit did not independently re-decode or rehash those files. Amp transformed an output review attachment from 142,217,777 to 50,985,101 bytes; it is excluded from exact-byte evidence. Expiring private attachment URLs are not a durable receipt route. These omissions are explicitly retained in this publication.
