"""Freeze preparation only. Never launch a renderer, encoder, build or timing job."""
import hashlib, json, pathlib, shutil, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'comparison/serial-4k-qualification-plan-20261005'
CHILD = pathlib.Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94')
GIB = 1024 ** 3

def pin(path):
    path = pathlib.Path(path).resolve()
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

OUT.mkdir(exist_ok=False)
metal = json.loads((CHILD / 'hevc-evidence/BUILD-READY.json').read_text())
vk = json.loads((CHILD / 'vulkan-evidence/BUILD-READY.json').read_text())
mf = ROOT / 'comparison/fframes-concurrent-nv12-20261004'
adapter = pin(ROOT / 'checkpoint/native_chroma_conformance.py')
assert adapter['sha256'] == 'b0a36b7852439a78b27365a2846a1b471207f1285fbb9461aa7fa125a21a5088'
mh = pin(metal['frozenHelper']); vh = pin(vk['helper']['path'])
assert mh['sha256'] == metal['helperSha256'] and vh['sha256'] == vk['helper']['sha256']
fh = pin(ROOT / 'build/fframes-current/release/circles-concurrent-nv12')
fc = pin(ROOT / 'sources/fframes-concurrent-nv12/nv12-converter.dylib')
assert fh['sha256'] == '665ce943531be9a35d61aa7629e12646e280d0568c1ca6a576816f15963210a8'
assert fc['sha256'] == '11522ab92e119b84f9af86b9abf5864263c774a21ac7505b82a6556b6e9e132d'
font = pin(ROOT / 'preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf')
assert font['sha256'] == '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5'
inputs = [adapter, mh, vh, fh, fc, font, pin(ROOT/'checkpoint/circles-scene.mts')]
ffont = pin(ROOT/'comparison/font/DMSans-Regular.ttf')
assert ffont['sha256'] == font['sha256']
inputs.append(ffont)
for name in ['hevc-evidence/BUILD-READY.json', 'vulkan-evidence/BUILD-READY.json',
             'COMPARISON-MONITOR-NATIVE-CONFORMANCE-PREP-20261005.json']:
    inputs.append(pin(CHILD / name))
for name in ['BUILD-READY.json','EXACT-RUNTIME-PINS.json','DEPENDENCY-SOURCE-PINS.json','HARNESS-PINS.json','RECEIPT-MANIFEST.json']:
    inputs.append(pin(mf/name))
for name in ['FINAL-REPORT.json','EXACT-PINS.json','RECEIPT-MANIFEST.json']:
    inputs.append(pin(ROOT/'comparison/native-conformance-prep-20261005'/name))
for name in ['validate-native-conformance-prep.py','test_native_chroma_conformance.py',
             'run-concurrent-nv12.py','audit-concurrent-nv12.py','audit-concurrent-gpu.py',
             'audit-concurrent-4k-profile.py']:
    inputs.append(pin(ROOT/'checkpoint'/name))
inputs.append(pin(ROOT/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'))
for tree in [metal['worktree'], vk['worktree']]:
    portable = pathlib.Path(tree)/'packages/portable'
    for folder in ['src','dist','native']:
        for p in sorted((portable/folder).rglob('*')):
            if p.is_file() and 'target' not in p.parts and p.suffix in ['.ts','.js','.rs','.mm','.hpp','.toml','.lock']:
                inputs.append(pin(p))
for name in ['node','python3','ffmpeg','ffprobe']:
    inputs.append(pin('/opt/homebrew/bin/'+name))
runtime = pathlib.Path('/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS/libMoltenVK.dylib')
inputs.append(pin(runtime))
for n in ['hardware.dylib','nv12-control.dylib','rgba-control.dylib']:
    inputs.append(pin(CHILD/'hevc-evidence/qualification-01'/n))
for n in ['hardware.dylib','nv12-control.dylib','rgba-control.dylib']:
    inputs.append(pin(CHILD/'vulkan-evidence/qualification-02'/n))
inputs.append(pin(mf/'transfer-interposer.dylib'))
inputs.append(pin(pathlib.Path(__file__)))
inputs.append(pin(ROOT/'checkpoint/check-serial-4k-plan-20261005.py'))
inputs = list({p['path']: p for p in inputs}.values())
write('EXACT-INPUT-PINS.json', {'files':inputs, 'scope':'actual readable files; build receipts retain prior full dependency/source provenance; no rebuild'})

def native(lane, codec, backend, helper, worktree, protocol):
    # List arguments explicitly: codec is argv[12], after GOP and pool.
    args = ['encode-binary','3840','2160','30','1','300000000','{OUT}/elementary.'+('h265' if codec=='hevc' else 'h264'),'{OUT}/gpu-transfer.jsonl','','30','3',codec]
    return {'id':lane,'engine':'Helios','codec':codec,'backend':backend,'helper':helper,
            'sourceCommit':metal['commit'] if backend=='metal' else vk['sourceCommit'],
            'binaryProtocol':protocol,'transport':'binary','encoder':'required VideoToolbox',
            'pool':3,'recorderModule':str(pathlib.Path(worktree)/'packages/portable/dist/gpu.js'),
            'nativeCommand':[helper['path'],*args],
            'referenceCommand':[helper['path'],'reference-binary',*args[1:6],'/unused','{OUT}/reference-transfer.jsonl','','30','3',codec],
            'muxCommand':['/opt/homebrew/bin/ffmpeg','-v','error','-xerror','-n','-r','30','-f','hevc' if codec=='hevc' else 'h264','-i',args[6],'-c:v','copy','-an','-video_track_timescale','30','-movflags','+faststart','{OUT}/original.mp4'],
            'referenceSource':'new native reference-binary stdout, explicit excluded GPU NV12 download; separate reference render, not claimed candidate encoder handoff',
            'interop':'Metal IOSurface' if backend=='metal' else 'macOS MoltenVK Metal texture import and VideoToolbox; not Linux Vulkan Video',
            'qualified4K':False}

lanes = [native('H-metal-hevc','hevc','metal',mh,metal['worktree'],7),
         native('H-metal-h264','h264','metal',mh,metal['worktree'],5),
         {'id':'F-modified-concurrent-h264','engine':'fframes','codec':'h264','backend':'metal','helper':fh,'converter':fc,
          'command':[fh['path'],'hardware','{OUT}/original.mp4',str(ROOT/'comparison/font'),'300','300000000'],
          'taskSettings':{'FFRAMES_EXPLICIT_NV12':'1','FFRAMES_HANDOFF_CAPTURE':'{OUT}/capture','FFRAMES_NV12_TRACE':'{OUT}/gpu-transfer.jsonl','COMPARISON_REQUIRE_HARDWARE_FRAMES':'1'},
          'profileSettings':{'FFRAMES_CAPTURE_NO_DOWNLOAD':'1'},
          'contexts':3,'generationWorkers':5,'encoderWorkers':5,'queue':10,'segments':5,'framesPerSegment':60,
          'allocationThresholdPerContext':64,'referenceSource':'new same-stream capture of actual NV12 at encoder handoff, rawSha and source index ledger; pure planar split',
          'originalProduct':False,'qualified4KWithSharedAdapter':False},
         native('H-vulkan-h264','h264','vulkan',vh,vk['worktree'],9),
         native('H-vulkan-hevc','hevc','vulkan',vh,vk['worktree'],9)]
for lane in lanes:
    lane['workingDirectory']=str(ROOT)
    lane['conformanceCommand']=['/opt/homebrew/bin/python3',adapter['path'],'{OUT}/original.mp4','{OUT}/center.mp4','--codec',lane['codec'],'--receipt','{OUT}/CONFORMANCE.json']
    lane['qualityCommand']=['/opt/homebrew/bin/python3',str(ROOT/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'),'{OUT}/center.mp4','--reference','{OUT}/reference.mkv','--engine',lane['id'],'--reference-engine',lane['id'],'--scene','Circles99kText1k','--width','3840','--height','2160','--frames','300','--fps','30/1','--ssim-y','.995','--psnr-y','40','--psnr-uv','35','--ffmpeg','/opt/homebrew/bin/ffmpeg','--ffprobe','/opt/homebrew/bin/ffprobe','--output','{OUT}/quality.json']

referenceCommand=['/opt/homebrew/bin/ffmpeg','-v','error','-xerror','-n','-f','rawvideo','-pix_fmt','yuv420p','-s','3840x2160','-r','30','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-chroma_sample_location','center','-i','pipe:0','-c:v','ffv1','-level','3','-threads','2','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-chroma_sample_location','center','-frames:v','300','{OUT}/reference.mkv']
plan={'status':'frozen configuration and resource plan only; launch disabled','firstLane':'H-metal-hevc','serialOrder':[x['id'] for x in lanes],
      'scene':{'name':'Circles99kText1k','width':3840,'height':2160,'frames':300,'fpsNum':30,'fpsDen':1,'sourceIndicesInclusive':[3,302],'circleCount':99000,'textCount':1000,'scale':[3.84,2.16],'painterOrder':'all circles before all digits','audio':False,'font':font},
      'commonEncoding':{'bitrate':300000000,'gop':30,'qualityFloorsEveryFrame':{'ssimY':.995,'psnrY':40,'psnrU':35,'psnrV':35},'range':'limited','primaries':'bt709','transfer':'bt709','matrix':'bt709','physicalChroma':'equal four-sample 2x2 averaging','signaledChroma':'center'},
      'lanes':lanes,'sharedConformanceAdapter':adapter,'referenceCommand':referenceCommand,
      'feedContract':{'header':'one bounded JSON line {fonts:{dm:base64(font)}}','frames':'recordGpuCanvasBinary(createCircles(font), index, previousPacketLength), indices 3..302; write each binary Buffer with no separators; await drain before reuse; close stdin after frame302','retain':'index,sourceIndex,packetBytes,SHA256 for every packet, combined feed SHA256; font/module/scene exact pins','bounds':'native reader existing 120k commands /32MiB frame /64 stack /20k texts; exactly300 packets; no persistent duplicate 1.68GB packet stream'},
      'acceptanceOrder':['verify pins, source/build bindings, live runtime dependency hashes and resource gate; unique output root, no overwrite','bounded 3-frame codec/protocol/cadence/mux/conformance integration and full SPS/PPS/VPS/nonSPS/decoded invariance guards','predetermined sRGB-to-BT709-limited NV12 controls tolerance1: solids red/green/blue/white and fine colored edges; compare every control byte, never fit controls/floors','new all300 reference: raw NV12 SHA256 and pure indexing planar MD5 per index/source index; FFV1 decode all300 hashes exact; explicit source and output center/color tags','fresh encoded300: native required-hardware/rasterizer/protocol/bitrate/GOP/pool receipts, then identical b0 conformance adapter','independent SPS bits/full semantic fields except chroma location/alignment invariant; all other configuration/PPS/VPS bytes and every nonSPS NAL exact; original/conformed decoded YUV420p bytes all300 exact','all300 indexed quality floors, exact candidate 1/30 PTS/durations frame0..299, 3840x2160, noaudio, noBframes, GOP<=30, every decoded frame limited709 center; disclose reference Matroska timestamp quantization','separate full300 4K uncaptured interposer + raster/conversion/encoder callback/fence/owner release/reuse ledger and 3-frame 4K NV12/RGBA positive controls; capture overhead excluded','final manifest, helpers/source/runtime/harness archive pins and independent audit before any timed lane'],
      'profilingContract':{'candidateRawDownloadRequired':0,'referenceDownloadsExcluded':True,'actualGpuStagesRequired':True,'nativePool':3,'FAllocationThresholdPerContext':64,'FPolicyPreserved':'3 contexts /5+5 workers /queue10; source completion, conversion fence, ordered5segments, AVBuffer owner release before reuse; opaque VT retains unknown','vulkan':'actual VkQueueSubmit/fence/imported texture identity and GPU conversion+VT callback ownership; macOS only','zeroCopyProved':False,'unknown':'unhooked/driver/encoder copies and pointer/buffer access intent; never infer from feature flags'},
      'clocks':{'export':'start before startup/feed; include raster/conversion/encode/drain/elementary write/mux and complete conform() probes, copy/rewrite/hash/fsync/verification; stop only after conformed output published','delivered':'export plus mandatory API decode/cadence validation, separate receipt','excluded':'references, controls, warmups, profiles/captures, extra independent quality/requalification/invariance audit; never reconstruct original clocks'},
      'launchPrerequisitesStillPending':['9GiB live free disk for retained-raw one-lane route','new orchestration integration for explicit codec argument/protocol7 or9; old protocol5 exporter is not reused unmodified','full-workload profile launch paths/log redirection verified against frozen interposers; profile receipts cannot reuse small-scene scope','fresh live runtime dependency readSet pinned before launch; authoritative prior build/runtime receipts retained'],
      'performancePolicy':{'timingWindowOpen':False,'balancedRunsAuthorizedOnlyAfterAllGates':True,'possibleMatchedPair':'new centered H-metal-h264 versus separately labeled F modified concurrent h264,300Mbps; differing pool/concurrency contracts disclosed','HEVC':'separate native qualification until fframes HEVC lane exists; H264/HEVC not codec-matched timings','balancedOrder':['H,F','F,H','F,H','H,F'],'warmupsExcluded':True,'noConcurrentEngines':True,'announceWindowBeforeTiming':True,'publishedM5ClaimBeaten':False},
      'preserve':['all historical helpers, clocks, originals, references, raw receipts and excluded failures','native final-v3 accepted preparation; oldleft/default references remain oldscope','original F failures and serial adapter lane; modifiedF is not original product'],
      'Library':{'sourcePreparationId':'libfile_19c903c1d7508191ac4881f0e96e4229','historicalCheckpointId':'libfile_cd84375e4648819195364136245484c6','newIds':[],'publication':'blocked; no substitute route'},
      'nativeVulkanPublication':'destination approval pending; no push retry','broaderObjectiveComplete':False}
write('CONFIG.json',plan)
rows=[('directNV12 retained raw or compressed capture cap',3732480000,'retain; exactly300 frames; F capture is same-stream; compressed representation overhead counts toward cap and can refuse run'),('FFV1 centered lossless reference cap',GIB,'retain; budget cap not promised compression ratio'),('elementary stream cap',GIB//2,'retain native stream; F reservation conservative'),('original MP4 cap',GIB//2,'retain'),('conformed MP4 cap',GIB//2,'retain'),('atomic conformance temporary cap',GIB//2,'scratch; failed artifact retained within cap'),('excluded full300 profile candidate cap',GIB//2,'retain separate uncaptured hardware profile video'),('uncaptured profiler/control receipts cap',GIB//2,'retain; bounded logs; no large gputrace in this budget'),('three-frame RGBA/NV12 positive-control outputs cap',GIB//4,'retain; raw RGBA99532800 plus NV1237324800 bytes and small encoded/control artifacts'),('indexed probe/hash/quality/log cap',GIB//8,'retain; streaming decoded hashes, no persisted decoded raw'),('free disk reserve',GIB,'not output allocation')]
peak=sum(x[1] for x in rows)
ledger={'observedFreeBytes':shutil.disk_usage(ROOT).free,'calculation':'3840*2160*3/2*300','directFrameBytes':12441600,'direct300Bytes':3732480000,'entries':[{'item':n,'budgetBytes':b,'retention':r} for n,b,r in rows],
        'retainedRawPeakBudgetBytes':peak,'retainedRawGateBytes':9*GIB,'rawGateMarginBytes':9*GIB-peak,
        'streamingProposedPeakBytes':peak-3732480000,'streamingProposedGateBytes':6*GIB,'streamingEnabled':False,
        'balancedEightOutputBudgetBytes':8*(3*GIB//2)+GIB//2+GIB+GIB,'balancedGateBytes':15*GIB,'balancedScope':'8 native/F elementary+original+conformed outputs at0.5GiB each,0.5GiB conformance temporary,1GiB logs,1GiB reserve; refs must already exist. Extra profiling/reference/capture space added separately. Earlier12GiB estimate superseded for this retention plan.',
        'failurePolicy':'predict remaining budget before each stage; monitor own output tree size and free disk; stop before1GiB reserve/cap exhaustion; retain partial/error files; no evidence deletion; next attempt needs newly sufficient headroom. Caps are ceilings that can refuse a run, not estimates of codec byte maxima.',
        'serialPolicy':'check current free space anew before every lane, including outputs retained by prior lanes;9GiB is incremental per active lane, not permission to run all5 on one9GiB disk.',
        'capturePolicy':'actual 3-frame GPU capture needs a separate measured allocation gate; prior4K capture ENOSPC retained; no successful4K capture inferred; large capture not required to count uncaptured transfer proof but actual scene GPU proof still mandatory',
        'cachePurge':'9 unrelated ignored-cache approvals pending; nominal4.31GiB gain is not assumed and does not guarantee9GiB'}
write('RESOURCE-LEDGER.json',ledger)
stream={'status':'design evaluated from native stdout contract only; unimplemented and unqualified; cannot lower resource gate',
        'savingBytesPerNative300Reference':3732480000,'appliesTo':'native reference-binary stdout; not automatically F concurrent captured files',
        'dataPath':'producer stdout -> bounded exact-frame reader -> rawNV12 SHA256 then pure planar Y + evenUV(U) + oddUV(V), planar SHA256+MD5 -> FFV1 stdin; no color arithmetic',
        'memory':'one12,441,600-byte raw frame and one12,441,600-byte planar frame plus bounded pipe buffers; asynchronous writer must await backpressure; no accumulating raw frames',
        'endToEndBinding':'predeclare300frames source3..302; producer success + exact3,732,480,000bytes + no trailing/partial frames +300 raw/planar hashes + FFV1 success + all300 independently decoded planarMD5 equality; bind actual producer argv/helper/feed/scene/font/protocol/stderr/raw-readback count,reference SHA and encoder argv/runtime. Publish final binding only if all gates pass.',
        'recoverability':'lossless centered reference reconstructs planar samples exactly; reconstruct interleaved NV12 and rehash every raw SHA256 independently; raw stream not persisted, this limitation and producer provenance remain explicit',
        'referenceTags':'pure planar input carries centered limitedBT709 metadata BEFORE input and AFTER output; use CONFIG referenceCommand; no implicit NV12 sampling conversion',
        'requiredBoundedTests':['copied retained small raw only, noGPU: irregular chunk boundaries including1byte','truncated input atframe boundary and midframe rejected','extra complete frame/trailing byte rejected','nonzero producer exit after completebytes rejected','FFV1 failure/broken pipe early exit kills feed withoutdeadlock','corrupted reference/hashes rejects atomic binding','source/hash mismatch,duplicateindex,sourceorder faults rejected','backpressure slowconsumer fixed memory and everyframe preserved','inverse planar-to-NV12 hash reconstruction equals every direct SHA'],
        'retention':'never delete existing direct raw/reference evidence; new streaming lane retains source/feed/hash manifest, lossless file, exact commands+stdout/stderr+process results+all failure receipts. No substitution for prior all300 raw reference gates.',
        'qualification':'after bounded tests, resource-specific storage pilot separately frozen; fresh actual4K GPU reference and encode/profile still required; no benchmarking this reader as GPU performance',
        'F':'production contexts must not be serialized or capture buffers reused early. Current frozenF writes ordered compressed capture files; retain that route until an independently frozen streaming handoff reader exists.'}
write('STREAMING-STORAGE-PROPOSAL.json',stream)
for src,dest in [(ROOT/'checkpoint/circles-scene.mts','circles-scene.mts'),(pathlib.Path(font['path']),'DM-Sans.ttf'),(ROOT/'checkpoint/check-serial-4k-plan-20261005.py','check-plan.py')]:
    shutil.copy2(src,OUT/dest)
print(json.dumps({'status':'plan frozen; no jobs launched','directory':str(OUT),'pins':len(inputs),'rawPeakBudgetBytes':peak,'rawGateBytes':9*GIB,'observedFreeBytes':ledger['observedFreeBytes']}))
