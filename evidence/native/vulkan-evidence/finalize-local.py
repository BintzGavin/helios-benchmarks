from pathlib import Path
import json, hashlib, zipfile, datetime, subprocess

root = Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94')
r = root / 'vulkan-evidence'
b = json.loads((r / 'BUILD-READY.json').read_text())
w = Path(b['worktree'])
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda: f.read(1048576), b''): h.update(x)
    return h.hexdigest()
def save(p, d): p.write_text(json.dumps(d, indent=2) + '\n')
for group in ['sourceFiles', 'builtFiles']:
    base = w if group == 'sourceFiles' else w / 'packages/portable/dist'
    for f in b[group]:
        p = base / f['path']
        assert p.stat().st_size == f['bytes'] and sha(p) == f['sha256'], str(p)
for f in b['oldHelpers'] + [b['helper'], b['sourceArchive']]:
    assert sha(Path(f['path'])) == f['sha256'], f['path']
with zipfile.ZipFile(b['sourceArchive']['path']) as z: assert z.testzip() is None
assert subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=w, text=True).strip() == b['sourceCommit']
assert not subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'], cwd=w, text=True).strip()
b['helper']['uncommittedSource'] = False
b['helper']['sourceCommit'] = b['sourceCommit']
b['helper']['qualification'] = 'Passed: final helper03, both codecs all300 independent reference/quality/cadence/color and actual Vulkan/GPU/fault controls.'
b['publication'] = {'status': 'blocked-by-automatic-approval-review', 'remote': 'git@github.com:BintzGavin/helios.git', 'pushExecuted': False, 'pullRequest': None, 'approvalNeeded': 'Human explicit approval to push gavin/feat-gpu-vulkan-interop to BintzGavin/helios and open prepared draft PR.'}
save(r / 'BUILD-READY.json', b)
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
c = {'status': 'bounded native Vulkan H264/HEVC qualification complete locally; push awaiting explicit destination approval', 'updatedUtc': now, 'sourceCommit': b['sourceCommit'], 'branch': b['branch'], 'worktree': b['worktree'], 'qualifiedVulkanHelper': b['helper'], 'ownerCursor': b['ownerCursor'], 'timingWindow': 'closed', 'activeJobs': [], 'diskBlockResolved': True, 'resourceQuestionPending': False, 'skiaQualificationPending': False, 'broaderObjectiveComplete': False, 'heartbeatStatus': 'ACTIVE', 'zeroCopyProved': False, 'portableChecks': b['proofs']['portableTests'], 'nativeApiChecks': b['proofs']['nativeApiTests'], 'runtimeLoadRequirement': b['runtimeLoadRequirement'], 'publication': b['publication'], 'pending': ['Explicit human authorization for blocked push and prepared draft PR.', 'Owner retains full4K Vulkan/HEVC and quality-qualified fully enabled production comparison; no ownership handoff.', 'Library preparation route and exact measured M5 source/hardware remain unavailable; no substitutes.'], 'excludedCandidates': ['helper-candidate-01', 'helper-candidate-02'], 'receipts': ['BUILD-READY.json', 'INDEPENDENT-AUDIT.json', 'qualification-02/REPORT.json', 'qualification-02/H264-REPORT.json', 'RECEIPT-MANIFEST.json']}
save(r / 'CHECKPOINT.json', c)
f = {'status': 'qualified local bounded native Vulkan delivery; publication blocked', 'sourceCommit': b['sourceCommit'], 'helperSha256': b['helper']['sha256'], 'buildReady': 'BUILD-READY.json', 'independentAudit': 'INDEPENDENT-AUDIT.json', 'qualificationScope': {'device': 'Apple M3 Pro', 'backend': 'Skia Vulkan via pinned MoltenVK1.4.2 -> shared Metal texture -> GPU BT709 NV12 -> required VT', 'codecs': ['H264', 'HEVC Main8bit'], 'framesPerCodec': 300, 'width': 256, 'height': 128, 'fps': '30000/1001', 'requestedConfiguredBitrate': 20000000, 'gop': 30, 'pool': 3, 'jsonProtocol': 8, 'binaryProtocol': 9}, 'verified': ['Exact source/runtime/helper pins and six unchanged historical helpers.', 'All300 direct NV12/lossless reference frames and indexed decoded quality/cadence/color for each codec.', 'Actual Vulkan submission/fence and ordered conversion/callback/owner release for all300 per codec.', '219 portable checks,9 native Vulkan API checks,5 packet/boundary checks.', 'Both positive transfer controls detected;4 Vulkan and5 retained device/encoder/format fault controls refuse atomically.', 'Five focused receipt mutations killed after baseline and source restoration.'], 'confidence': {'percent': 95, 'scope': 'Bounded functional native qualification on this host; subjective confidence, not a statistical interval.', 'strongestUnmetRequirement': 'Full4K quality-qualified fully enabled production comparison remains incomplete.', 'largestResidualRisk': 'Unqualified scenes/hardware and opaque driver/encoder transfer behavior.', 'inference': 'No extrapolation from bounded scenes to4K performance or exact published M5 source reproduction.'}, 'limitations': ['20 explicit native/default-helper path skips; no newly rebuilt default Metal helper qualification.', 'Frozen helper requires retained canonical runtime path or exact pinned bytes restored there.', 'No full4K/performance/published M5/production win; Linux Vulkan Video,Intel/Windows,GPUmedia unsupported.', 'No zero-copy proof: mapped pointer intent and opaque transfers unknown.'], 'publication': b['publication'], 'broaderObjectiveComplete': False, 'zeroCopyProved': False, 'reviewImage': 'qualification-02/review.png', 'reviewVideo': 'qualification-02/video.mp4', 'sourceArchive': b['sourceArchive'], 'excludedAttempts': b['excludedAttempts']}
save(r / 'FINAL-REPORT.json', f)
files = []
for p in sorted(r.rglob('*')):
    if p.is_file() and p.name != 'RECEIPT-MANIFEST.json': files.append({'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)})
m = {'status': 'qualified bounded final-helper03 local delivery; historical failures retained and excluded', 'sourceCommit': b['sourceCommit'], 'qualifiedHelperSha256': b['helper']['sha256'], 'excludedHelperCandidates': ['helper-candidate-01', 'helper-candidate-02'], 'zeroCopyProved': False, 'full4KOrPerformanceQualified': False, 'files': files}
save(r / 'RECEIPT-MANIFEST.json', m)
for f in files: assert sha(Path(f['path'])) == f['sha256'] and Path(f['path']).stat().st_size == f['bytes']
a = {'status': 'passed', 'updatedUtc': now, 'manifestSha256': sha(r / 'RECEIPT-MANIFEST.json'), 'manifestMembersVerified': len(files), 'sourcePinsVerified': len(b['sourceFiles']), 'builtPinsVerified': len(b['builtFiles']), 'historicalHelpersUnchanged': len(b['oldHelpers']), 'archiveCrcPassed': True, 'sourceCommit': b['sourceCommit'], 'publicationBlockedByApprovalReview': True, 'broaderObjectiveComplete': False}
save(root / 'COMPARISON-MONITOR-VULKAN-FINAL.json', a)
with (root / 'GPU-COMPARISON-RESUME.md').open('a') as out:
    out.write('''

VULKAN LOCAL QUALIFIED DELIVERY (2026-10-04; supersedes preceding disk-block/unqualified statements): source63869ba529c89fc1a27f7f55057e4d876c42d26e on gavin/feat-gpu-vulkan-interop, external HEVC base079356491449178e66ab8bbaac700684668c8951. Corrected immutable helper03 SHA6679452901c6535cc80b4b762cd6c7c13d222e91fb8212a837ca85e60f4af22b passes actual Skia Vulkan using pinned MoltenVK1.4.2 on M3Pro. Read vulkan-evidence/BUILD-READY.json, FINAL-REPORT.json, INDEPENDENT-AUDIT.json, RECEIPT-MANIFEST.json and qualification-02/{REPORT,H264-REPORT}.json. Both codecs independently qualify all300256x128 frames at30000/1001,20Mbps,GOP30,pool3: exact directNV12/lossless binding, full decoded cadence/color/GOP and unchanged every-frame floors. Worst HEVC .999978/69.22/67.40/69.34; H264 .999984/67.10/71.95/71.70. Actual300 Vulkan submissions/fences and ordered same-IOSurface GPU conversion/submission/callback/release per codec; no early reuse. Expanded uncaptured profiler sees0hooked raw downloads, NV12control6locks and RGBAcontrol3VkCopyImageToBuffer detected. Pointer access and opaque transfers unknown, zeroCopyProved=false. Separate actual3frame whole-device capture excluded. Four Vulkan refusal controls and five retained device/encoder/format controls pass atomic refusal.219portable checks pass/20explicit default-native/path skips;9native API and5packet checks pass;5receipt mutations killed after baseline/source restored. Historical six helpers unchanged; candidates01/02 and failed profiler/diagnostic/ENOSPC/PATH attempts retained/excluded. Final source archive79255be24f4e86d18d4f5cb2f6afd611a07a50185d299c1dd1ea8b8a3ab22001,156source/42dist pins, CRC and allmanifest SHA/size bindings verified in COMPARISON-MONITOR-VULKAN-FINAL.json. Runtime58files frozen durably; retain canonical tmp runtime path or restore identical bytes there before frozen-helper reuse.

Publication blocked by automatic approval review of git push to git@github.com:BintzGavin/helios.git: exporting repository source and creating remote ref requires explicit destination authorization. Do not bypass/retry push without human explicit approval. No Vulkan PR exists yet; prepared PR-BODY.md includes reviewer Mermaid. Clean committed worktree; no jobs. Disk block resolved. Owner remains idle, cursor16, timing window closed and retains full4KHEVC/Vulkan/full-production comparison and Library identities. No full4K/performance/production/M5 claim; broader objective incomplete. Library preparation and exact measured M5 source/hardware blockers unchanged. Heartbeat ACTIVE.
''')
print(json.dumps(a))
