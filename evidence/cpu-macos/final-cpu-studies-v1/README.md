# Focused CPU studies and matched holdout

Prepared only: no builds, dependency changes, exports, tests, or historical reruns were performed during preparation. Frozen actual cap8 compiled candidate and pinned existing F/R runtimes are reused.

```text
MEDIUM resource screen ─┐
                       ├─ all-frame eligible median selection → fresh MEDIUM + UL holdout
UL resource screen ────┘
```

MEDIUM: H workers/encoder threads 4/4 (control A), 6/2 (B), 8/2 (C), 11/1 (D). One warmup each; timed orders ABCD, DCBA, BDAC.
UL: A H6/4 control, B H8/2, C H11/1, D F6/2 control, E F11/2, F R JPEG100 6/1, G R JPEG100 11/1, H R JPEG100 6/8, I R JPEG100 11/8. One warmup each; timed orders ABCDEFGHI, DEFGHIABC, GHIABCDEF.
Holdout: H fastest fully eligible screen setting per preset; F MEDIUM11/2 and fastest fully eligible UL; R MEDIUM JPEG10011/8 and fastest fully eligible UL. One new warmup per engine/preset, then HFR / FRH / RHF. Selection uses only new screen medians, with exact median ties resolved by fewest workers×encoder threads, then workers, then threads. No broad optimality claim.

Each row uses a fresh process. The external clock ends after successful full final decode: H internal decode once; F/R external 8-thread count once; F UL includes original export + stream-copy edit-list repair + final full decode. Subprocess component receipts retain separate wall times. Existing source checks, assembly, hashes, SEI, actual frame cadence, and PSNR/SSIM are outside delivery clocks. Exact actual PTS/cadence is checked before metrics use shared `settb=expr=1/30,setpts=N`. Existing own-source lossless references are reused, never regenerated. All 300 frames must satisfy SSIM Y≥.995, PSNR Y≥40/U≥35/V≥35. Identical output hashes are measured once per reference, then bound to every original repeat. Failed quality excludes its profile; process, cadence, drift, or budget errors stop with no retry.

CPU R uses the original admitted Chrome wrapper and original worker source; the 13-line local wrapper changes only preset-dependent x264 fields. Codec CRF11, GOP24, q15..60, qcomp.6, qdiff4, BT.601 TV; MEDIUM B3/sc40, UL B0/sc0. SEI is recorded per encoder; H/F initial aggregate is workers×threads, while R encoder concurrency is disclosed separately from DOM worker count.

Logical new MP4 caps: MEDIUM3 GiB, UL10 GiB (lead adjustment), holdout6 GiB, including original F UL files. UL additionally caps unique-inode MP4 sizes at4 GiB; reported allocated bytes are saved. SHA-verified atomic hardlinks deduplicate only this invocation's new files after delivery clocks. Every original path/byte/hash and process receipt remains. Logs/metrics are small and excluded from MP4 caps. Expected logical totals ≈2.2/8.6/4.1 GiB, physical unique outputs ≈.55/2.3/1.2 GiB if repeats are byte-identical. Parent checks free space before launch.

Estimated sequential elapsed time, including untimed checks/metrics: MEDIUM5–8min, UL12–20min, holdout10–15min. These are estimates from prior output sizes/times, not new results. Screening quality failures may leave no eligible engine; holdout then refuses selection. Syntax and read-only preflight cannot establish actual runtime success, fidelity, or physical dedup rate.

Run sequentially, stopping if any command fails:
```sh
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/run.py --preflight
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/run.py --run --mode medium-screen --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/medium-screen/full-v1
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/run.py --run --mode ul-screen --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/ul-screen/full-v1
/usr/bin/python3 -B /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/run.py --run --mode holdout --medium-screen /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/medium-screen/full-v1/manifest.json --ul-screen /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/ul-screen/full-v1/manifest.json --results /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/holdout/full-v1
```

All result directories must be new. A repeat with the same path fails; there is no resume, automatic retry, cooldown, polling, or concurrent engine launch.

