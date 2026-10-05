# CPU TextGrid reproduction bundle

This bundle reproduces the **qualified final settings** for the 300-frame, 1920×1080, 30fps, 3,334-label TextGrid CPU study. `holdout-receipts.json` preserves all24 original warmup/timed rows, original nanosecond clocks and component timers, output hashes, x264 SEI, sanitized CPU DOM-stage evidence, all300 per-frame PSNR/SSIM rows for each of6 unique output/reference pairs, exact actual PTS, reference hashes, and original source/runtime/manifest hashes. It is compact evidence extracted from independently verified original artifacts; **creating this bundle did not perform another full decode or rerun**.

Original host: Apple M3 Pro,11 available logical CPUs, macOS arm64. MEDIUM delivered medians H11.990895250s, F15.203560167s, R24.039981583s; UL H4.210728167s, F7.357826791s, R18.165699834s. The JSON preserves individual rows and distinguishes ratios of medians from within-round ratios. These observations apply to this workload, host, native rasterizers, versions and tested configurations. New local runs are separate studies. Fidelity is against each engine's own lossless rasterizer, without asserting pixel equivalence between native Skia, FFRAMES CPU SVG, and Chrome DOM rendering.

```text
explicit built inputs → fresh warmups + HFR/FRH/RHF rounds → delivered timers
                                                        → fresh own references → actual PTS → integer-clock PSNR/SSIM
```

## Requirements and preparation

Preparation of this bundle ran syntax checks and read-only preflight only. It contains source, locks, notices and compact JSON; no binaries, videos, original lossless references, logs, credentials, or font binary. Original evidence paths are replaced with stable `study/`, `helios-repo/` and `tools/` labels; numeric and hash values are unchanged.

This focused driver requires Python3.9+, Node24.19.0, FFmpeg/probe9.0 linked to shared x264 core165, Google Chrome for Testing149.0.7790.0 headless shell, macOS arm64 compositor, and at least11 available logical CPUs. Supply executables explicitly. Native Rust build prerequisites include a Rust toolchain supporting edition2024 and `usize::is_multiple_of`, plus the pinned FFRAMES crate's FFmpeg/native build prerequisites. The bundled Cargo.lock controls crates; Node projects retain their original locks. Tool acquisition/build is deliberately separate from study timing. Do not upgrade versions or manually synchronize internal package versions.

Use a workspace with sibling `fframes/`, `helios/`, and this bundle directory. Commands below are setup instructions for another engineer; they were **not executed** while preparing the bundle.

```sh
git clone https://github.com/dmtrKovalenko/fframes fframes
git -C fframes checkout bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b
git clone https://github.com/BintzGavin/helios helios
git -C helios checkout ebf8e145538d454479d80f97f8f76893b2fdf96f
npm --prefix helios ci --ignore-scripts
npm --prefix helios run build --workspace packages/portable
cargo build --release --locked --manifest-path public-reproduction-v1/fframes-cpu/Cargo.toml
npm --prefix public-reproduction-v1/remotion-project ci --ignore-scripts
mkdir -p public-reproduction-v1/remotion-project/public
cp fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf public-reproduction-v1/remotion-project/public/DMSans-Regular.ttf
```

Helios tested source commit is `0566d1108f922ea88294d4bbe1f11cdb49849834`, merged by [PR5006](https://github.com/BintzGavin/helios/pull/5006) as `ebf8e145538d454479d80f97f8f76893b2fdf96f`. All115 portable package files in that merge are Git-tree identical to the tested head. Its19 compiled JS files were verified byte-identical to the frozen candidate. `merge-receipts.json` records both renderer and scheduler merges; scheduler wall-time gains remain unmeasured. The driver checks the nine rendering modules it binds against the original receipt hashes. Use `--helios-package` to supply an already built package instead of `--helios-repo`. `@napi-rs/canvas` must resolve its original macOS arm64 native module.

The public Rust source changes only the original hardcoded media folder into required CLI argument6. Its Cargo.toml changes only the original absolute FFRAMES path into `../../fframes/fframes`; preserve the sibling layout or update that path explicitly in your new local crate. Build the adapted source before launching. `--fframes-binary` supports a build stored outside the crate's default target directory. Read-only preflight can inspect the historical crate, but export launch rejects Rust sources that differ from the bundled adapted main.rs. This protects the explicit media argument; it is not a claim that binary/source correspondence was independently rebuilt here.

Retrieve the font from the exact pinned FFRAMES checkout. Required SHA256:
`9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5`.
Preflight verifies upstream, project and bundle copies. No font-specific redistribution license was verified in that checkout, so this bundle omits the binary. FFRAMES's MIT notice applies to copied benchmark code; installed Helios, Remotion, FFmpeg/x264 and other dependencies retain their own notices/licenses. See `licenses/` and `provenance.json`.

Use your exact Node24.19 executable to bundle the copied Remotion project after installing its lock. The browser is acquired separately at the pinned version; the driver never downloads it. Remotion renderer and bundler4.0.529 are in the locked CLI dependency graph.

```sh
node24=/absolute/path/to/node24.19.0
"$node24" public-reproduction-v1/bundle.mjs public-reproduction-v1/remotion-project public-reproduction-v1/remotion-bundle
```

## Study command

Replace explicit path placeholders. `--preflight` is read-only: source/font/runtime bindings and version/resource queries only. It does not build, render, generate references or measure quality.

```sh
python3 -B public-reproduction-v1/run.py --preflight \
  --node /absolute/path/to/node24.19.0 \
  --ffmpeg /absolute/path/to/ffmpeg9 --ffprobe /absolute/path/to/ffprobe9 \
  --browser /absolute/path/to/chrome149-headless-shell \
  --x264-library /absolute/path/to/libx264.165.dylib \
  --helios-repo ./helios --fframes-repo ./fframes \
  --fframes-crate ./public-reproduction-v1/fframes-cpu \
  --remotion-project ./public-reproduction-v1/remotion-project \
  --remotion-bundle ./public-reproduction-v1/remotion-bundle
```

To launch a **new** local study, use the same inputs, replace `--preflight` with `--run --results ./my-new-cpu-holdout`. The output directory must not exist. Every engine export gets a fresh process. There are24 exports: one warmup per engine/preset and three timed rounds per preset with HFR, FRH, RHF order; engines execute sequentially. No retries, cooldowns, polling or historical reruns.

Fixed final settings: H MEDIUM4workers/4encoder threads, UL8/2; F11/2 both presets; R JPEG10011renderer workers/8threads per active encoder both presets. H/F threads are per worker/segment; R renderer concurrency does not establish simultaneous encoder count. Codec: software libx264 CRF11, GOP24, qmin15/qmax60/qcomp.6/qdiff4, BT.601 TV YUV420P. MEDIUM B3/scenecut40; UL B0/scenecut0. Actual x264 parameters and encoder thread scope are saved.

The external `perf_counter_ns` clock includes fresh process lifetime through successful full final decode. H counts its internal final full decode once; F/R count one external8-thread final full decode. F UL retains its original export, then includes stream-copy edit-list repair and final verification in delivery time. Setup, source hashes, output hashes, SEI, quality and exact cadence are outside delivery clocks. No component clock is rewritten.

After all timed rows finish, the runner generates **new own-source** lossless H/F/strict-CPU R references using the copied original helpers. No original private NUT path is read. Reference creation is untimed and retains per-frame source hashes where the original helper provides them. R uses PNG only for its own lossless reference; timed R uses JPEG100. Actual300-frame PTS must equal0…299/30 with exact cadence and format before integer metric normalization. The corrected metric graph uses `settb=expr=1/30,setpts=N` on both inputs. Each frame must meet SSIM Y≥.995 and PSNR Y≥40/U≥35/V≥35. Identical new output hashes are measured once per own reference and bound to every original repeat.

Chrome receives `--disable-gpu --disable-gpu-compositing --disable-gpu-rasterization`; CDP must admit software/disabled compositor and rasterization stages for the DOM workload. Sanitized feature status and GL renderer/vendor are saved. Other browser capabilities can report enabled; these receipts attest the required workload stages and software video encoder rather than every browser subsystem.

## Scope, history and storage

Resource tuning was bounded: H MEDIUM4/4,6/2,8/2,11/1; UL H6/4,8/2,11/1, F6/2,11/2, R JPEG1006/1,11/1,6/8,11/8. Earlier F MEDIUM tested4/6/11workers with2threads, and R MEDIUM JPEG1006/11workers with8threads. Final selections used new screen medians among settings passing every frame's quality/cadence checks, then an independent holdout. No claim of a broader optimum.

Original JPEG80 failed the fixed fidelity floor (SSIM Y minimum.952, PSNR Y34.91); JPEG100 was admitted. Initial PNG timing evidence lacked the later CPU DOM-stage admission and is excluded from CPU comparison claims. Original Remotion metric comparisons had a floating timestamp normalization bug; the exact shared integer clock corrected those quality comparisons. Original actual cadence and original performance timers were preserved.

Study MP4 logical cap6 GiB includes all original F UL exports/repairs. Only new study-owned files are SHA-verified and atomically hardlinked after delivery clocks, preserving every original path and receipt. Failed attempts and historical evidence are never deleted. Expect≈4.1 GiB logical MP4s,≈1.2 GiB physical if repeats match; physical sharing is reported, not promised. New lossless references have their own6 GiB cap, with≈.75 GiB retained and≈1.25 GiB transient R PNG scratch anticipated. Only that newly generated PNG scratch is removed by the original reference helper after hashes/receipts are saved. Allow at least12 GiB free for conservative caps and scratch. Failures stop without retry; fidelity failure excludes a setting from claims.

Preparation limitations: Rust adaptation and source-path substitutions were inspected as focused diffs; Python, JS and shell syntax passed; read-only preflight passed against the existing known built inputs. Adapted Rust was **not rebuilt**, and public reproduction exports/reference generation were **not exercised**. Native package/tool linkage and a fresh engineer's installed prerequisites must be verified locally. Installing or running this bundle produces a new study, not the historical proof.

`original-decoder-candidate.diff` preserves the original frozen baseline→candidate change. An optional baseline reconstruction may use the same source with only final full-decode threading reverted to1. Label that as a new reconstruction, keep its files separate, and derive no new baseline numbers from this bundle's holdout clocks.

