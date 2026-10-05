# Preserved setup and inspection failures

No qualification or holdout export failed, and no benchmark export was retried or replaced.

1. Exact PR merge ref fetch: `git fetch --quiet origin pull/5006/merge` returned `fatal: couldn't find remote ref pull/5006/merge`. The preceding unshallow fetch had completed, and the required merge object was then verified locally by exact SHA. See `receipts/git-binding-second-attempt.txt`.
2. Initial machine inventory exited 1 because none of the probed Chromium command names existed. All preceding output is preserved in `receipts/machine-toolchain.txt`; exact Chrome for Testing 149 was subsequently installed explicitly.
3. Direct cgroup root reads for `cpu.max`, `memory.max`, and `memory.current` failed because this orb delegates limits below the cgroup root. Discovery is preserved in `receipts/cgroup-discovery.txt`; inherited values are in `receipts/effective-cgroup-values.txt`. A per-command scope path also disappeared after that command ended, while the stable workload-slice values remained readable.
4. Direct `apt-get update` failed with permission denied on `/var/lib/apt/lists/lock`. The value-free `sudo apt-get` retry succeeded.
5. First locked fframes build failed before compilation because standalone Cargo could not find `rustc` by name: `could not execute process rustc -vV`. See `logs/fframes-build.log`. The retry used the explicit fixed path `/home/user/benchmark-work/rust/bin:/usr/local/bin:/usr/bin:/bin`.
6. Second locked fframes build failed in `ffmpeg-sys-next 9.0.0` configuration with `ERROR: x264 not found using pkg-config`. See `logs/fframes-build-second.log`. Installing only `libx264-dev` resolved the missing build prerequisite; the third locked build succeeded (`logs/fframes-build-third.log`).
7. `pstree` was unavailable during build inspection. A scoped `ps` query was used instead; this did not affect source or build state.
8. One analysis-only `jq '.[0]'` invocation was incorrectly applied to a stream of JSON objects and returned “Cannot index object with number.” It was corrected to `jq -s '.[0]'`; benchmark outputs and metrics were not changed.

The only source adaptations are the one-line fframes crate path change (`receipts/fframes-linux-path.diff`) and the focused Linux runner diff (`receipts/linux-runner-adaptation.diff`).
