# Study index

| Family | Role | Evidence namespace |
| --- | --- | --- |
| M3 Pro CPU baseline | exploratory baseline | `cpu-macos/local-driver`, `three-engine-v1` |
| Decoder thread microstudy | supporting measurement | `cpu-macos/decode-study-v1` |
| Paired decoder export | separately qualified improvement | `cpu-macos/paired-decode-export-v1` |
| H encoder-thread / F worker screens | configuration selection | `cpu-macos/encoder-thread-study-v1`, `fframes-worker-study-v1` |
| R CPU/JPEG screens | eligibility/tuning; JPEG80 excluded | `cpu-macos/remotion-cpu-jpeg-study-v1` |
| All-frame metrics and clock correction | quality-only evidence | `cpu-macos/quality-measurement-v1`, `quality-clock-revision-v1` |
| Final local resource screens | select settings, not holdout statistics | `cpu-macos/final-cpu-studies-v1/results/medium-screen`, `ul-screen` |
| Fresh CPU holdout | 18 timed + 6 warmups | `cpu-macos/final-cpu-studies-v1/results/holdout` |
| Scheduler checks | correctness/merge evidence, no remote speedup claim | `cpu-macos/scheduler-*` |
| Linux Amp Orb | independent host CPU holdout | `cpu-orb`, `cpu-orb-delivery` |
| GPU TextGrid software/hardware | separate four-round comparisons | `gpu-comparison/software-balanced-01tab`, `hardware-balanced` |
| Native delivery histories | functional/source/GPU qualification | `native/*-evidence` |
| 4K original F product screens | failed-quality/excluded | `gpu-comparison/circles-screen-f-*` |
| Common-converter4K | separately labeled serial adapter comparison | `gpu-comparison/circles-common-binary-300-balanced` |
| Original F same-stream handoff | ambiguity diagnostic, still chroma failures | `gpu-comparison/fframes-original-handoff-20261004` |
| Modified F concurrent NV12 | H.264 4K quality qualification, untimed | `gpu-comparison/fframes-concurrent-nv12-20261004` |
| Native centered signaling | separately qualified small-scene conformance | `gpu-comparison/native-conformance-prep-20261005` |
| Serial 4K plan | frozen plan/resource ledger; not execution | `gpu-comparison/serial-4k-qualification-plan-20261005` |
| Streaming/codec/bridge preparation | bounded CPU fixtures; hardware not qualified | `gpu-comparison/*prep-20261005` |
| Independent monitor audits | cross-checks and honest scope | `audits` |

Recent source chats inventoried: **Benchmark fframes rendering optimiz**, **Helios CPU benchmarks on Amp Orbs**, **Compare Helios GPU performance**, **Portable native GPU rendering and benchmarks**, and **Set up helios**. The setup chat supplied background, not an additional qualified rendering benchmark. The original Amp experiment is thread`T-01a0fe75-21f7-744a-9a0b-efb868105967`. Conversation transcripts and unrelated product/promo/credential material are not republished as benchmark receipts.
